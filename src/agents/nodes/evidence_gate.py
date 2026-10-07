"""Fail-closed authority and applicability gate for retrieved protocols."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.agents.nodes.resource_estimator import estimate_resource_count_esi
from src.agents.problem_state import build_problem_state_from_agent_state
from src.agents.state import AgentState
from src.config import get_settings
from src.services.db import async_engine
from src.services.rag.clinical_query_planner import (
    ClinicalQuerySet,
    plan_clinical_queries,
)
from src.services.rag.hybrid_retrieval import (
    FusedCandidate,
    apply_relevance_floor,
    deterministic_relevance,
    llm_rerank,
)
from src.services.rag.knowledge_retriever import get_knowledge_retriever
from src.services.rag.outcomes import RetrievalOutcome, RetrievalStatus
from src.services.rag.query_translation import translate_query


logger = logging.getLogger(__name__)


_RESOURCE_LEVEL_SQL = text(
    """
    SELECT document_id, retrieval_text, atom_type, pass5_version,
           retrieval_text_sha256, payload
    FROM esi_knowledge_documents
    WHERE retrieval_scope = 'CLINICAL_AUTHORITY'
      AND (payload::jsonb)->'retrieval_facets' ? 'RESOURCE'
      AND (
        (
          (payload::jsonb)->>'esi_level' ~ '^[0-9]+$'
          AND ((payload::jsonb)->>'esi_level')::int = :esi_level
        )
        OR retrieval_text ILIKE :level_text
      )
    ORDER BY
      CASE
        WHEN (payload::jsonb)->>'title' ILIKE 'Decision Point C%%' THEN 0
        WHEN retrieval_text ILIKE '%%Decision Point C%%' THEN 1
        ELSE 2
      END,
      LENGTH(retrieval_text)
    LIMIT 1
    """
)


def _authority_queries(
    planned: ClinicalQuerySet,
    combined: str,
    refinement: str,
) -> list[tuple[str, str]]:
    """Query set for the ESI authority corpus.

    The narrow primary-symptom query is kept here: finding the rule that
    governs "severe chest pain" is exactly what a short, specific query is good
    at. A bounded refinement from the reasoner is added as its own channel so
    it competes on rank rather than being concatenated into everything else.
    The legacy combined string remains a fallback for the case where canonical
    state produced no usable English at all.
    """
    queries = list(planned.queries())
    # Decision Point C is the governing branch for non-ESI-1/2 cases.  Symptom
    # queries alone often retrieve high-risk examples but miss the resource
    # count rules that distinguish ESI 3, 4 and 5; include those authority
    # questions as first-class retrieval channels so the reasoner can cite the
    # algorithm instead of similar cases.
    queries.extend(
        [
            (
                "decision_point_c_resources",
                "Emergency Severity Index Decision Point C how many different resources ESI level 3 ESI level 4 ESI level 5",
            ),
            (
                "resource_count_levels",
                "ESI resource count two or more resources one resource no resources level 3 level 4 level 5",
            ),
        ]
    )
    if refinement:
        queries.append(("refinement", refinement))
    if not queries and combined:
        queries.append(("combined", combined))
    return queries


def _case_support_queries(planned: ClinicalQuerySet) -> list[tuple[str, str]]:
    """Query set for similar real cases.

    Deliberately narrower than the authority set. A bare "moderate headache"
    matches every headache in 5,590 cases, so including it dilutes fusion and
    measurably lowers precision (see eval/results/retrieval_report.md); the
    overall presentation and the symptom combination are what make one case
    more like this patient than another.
    """
    return [
        (name, text)
        for name, text in planned.queries()
        if name in {"overall", "associated"}
    ]


async def _rank_case_support(
    case_support: RetrievalOutcome,
    planned: ClinicalQuerySet,
    *,
    settings: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rerank similar cases, then withhold the ones not worth showing.

    Returning fewer cases -- or none -- is the intended behaviour. A retriever
    asked for five returns five whatever it found, and five cases that are not
    actually similar cost a nurse the time to rule each one out while implying
    a support the evidence does not provide.

    The relevance produced here is a retrieval score. It is not a probability,
    not a confidence, and it never touches the ESI decision: MIETIC labels are
    carried for display only and the reasoner is not shown them.
    """
    if case_support.status is not RetrievalStatus.SUCCESS or not case_support.items:
        return [], {"status": case_support.status.value, "shown": 0}

    candidates = [
        FusedCandidate(
            doc_id=item.doc_id,
            text=item.text,
            metadata=dict(item.metadata),
        )
        for item in case_support.items
    ]
    # Channel provenance survives the round trip so "both channels agreed" is
    # still available to the reranker.
    for candidate, item in zip(candidates, case_support.items, strict=True):
        audit = item.metadata.get("channel_audit") or {}
        candidate.fusion_score = float(item.metadata.get("fusion_score") or 0.0)
        candidate.metadata["dense_score"] = audit.get("dense")
        candidate.metadata["lexical_score"] = audit.get("lexical")
        candidate.metadata["channels"] = audit.get("channels") or []

    for candidate in candidates:
        score, reason = deterministic_relevance(
            candidate,
            grounded_concepts=planned.grounded_concepts,
            lexical_terms=planned.lexical_terms,
        )
        candidate.relevance = score
        candidate.relevance_reason = reason

    reranked_by_llm = False
    if settings.retrieval_rerank_enabled and planned.overall:
        reranked_by_llm = await llm_rerank(planned.overall, candidates)

    kept = apply_relevance_floor(
        candidates,
        minimum=float(settings.case_support_min_relevance),
        max_shown=int(settings.case_support_max_shown),
    )
    shown = [
        {
            "case_id": candidate.doc_id,
            "presentation_excerpt": candidate.text[:240],
            # Retained under its old name for stored-state compatibility; it is
            # the dense cosine similarity and is not what ordering used.
            "similarity_score": candidate.metadata.get("dense_score"),
            "retrieval_relevance": candidate.relevance,
            "relevance_band": _relevance_band(candidate.relevance),
            "relevance_reason": candidate.relevance_reason,
            "retrieval_channels": candidate.metadata.get("channels") or [],
            # Case metadata, grounded in the corpus row. UNKNOWN stays UNKNOWN:
            # a case with no validated level is never rendered as though it had
            # one, and none of this may set the patient's ESI.
            "validated_esi_level": candidate.metadata.get("validated_esi_level"),
            "candidate_esi_levels": list(
                candidate.metadata.get("candidate_esi_levels") or []
            ),
            "label_status": candidate.metadata.get("label_status") or "UNKNOWN",
            "age_band": candidate.metadata.get("age_band"),
            "sex": candidate.metadata.get("sex"),
            "symptom_concepts": list(
                candidate.metadata.get("symptom_concepts") or []
            ),
            "retrieval_scope": "CASE_SUPPORT",
            "authority_status": "NOT_PROTOCOL",
        }
        for candidate in kept
    ]
    audit = {
        "status": case_support.status.value,
        "pool": len(candidates),
        "shown": len(shown),
        "suppressed": len(candidates) - len(shown),
        "min_relevance": float(settings.case_support_min_relevance),
        "llm_reranked": reranked_by_llm,
        "scores": [
            {"case_id": item.doc_id, "relevance": item.relevance}
            for item in candidates[:10]
        ],
    }
    return shown, audit


async def _resource_authority_fallback(
    state: AgentState,
    *,
    channel_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Fetch a Decision Point C authority atom when hybrid retrieval misses it.

    This is not a case-example shortcut and it does not relax provenance: it
    reads the same validated authority table as the retriever, requires
    pass5/hash metadata, and exposes the same citation/evidence contract.  It
    only runs for a deterministic resource-count estimate after ESI 1/2 gates
    have stayed negative.
    """

    estimate = estimate_resource_count_esi(state)
    if estimate is None:
        return [], [], []

    level_text = f"%ESI Level {estimate.esi_level}%"
    try:
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                _RESOURCE_LEVEL_SQL,
                {"esi_level": estimate.esi_level, "level_text": level_text},
            )
            row = result.mappings().first()
    except Exception:  # noqa: BLE001 - fallback must fail closed
        logger.exception("Resource-count authority fallback failed")
        return [], [], []

    if not row:
        return [], [], []

    doc_id = str(row["document_id"])
    retrieval_text = str(row["retrieval_text"] or "")
    pass5_version = str(row["pass5_version"] or "")
    content_hash = str(row["retrieval_text_sha256"] or "")
    payload = row["payload"] if isinstance(row["payload"], dict) else {}
    if not doc_id or not retrieval_text.strip() or not pass5_version or not content_hash:
        return [], [], []

    section = str(
        payload.get("heading_path")
        or payload.get("section")
        or payload.get("source_heading")
        or ""
    )
    criteria = _protocol_criteria(doc_id, payload)
    if not criteria:
        return [], [], []

    citation = {
        "id": doc_id,
        "title": str(payload.get("title") or payload.get("heading") or section or doc_id),
        "protocolId": doc_id,
        "excerpt": retrieval_text[:240] + ("..." if len(retrieval_text) > 240 else ""),
        "relevanceScore": 1.0,
        "sourceType": "validated_protocol",
        "version": pass5_version,
        "section": section or None,
        "contentHash": content_hash,
        "retrievalChannels": [
            # Keep the patient-facing DTO inside the public retrieval-channel
            # contract. The fallback remains auditable through provenance and
            # retrieval_degraded_modes; leaking an internal suffix here breaks
            # frontend replay validation for the entire chat transcript.
            {"channel": channel_name, "rank": 1, "score": 1.0}
        ],
    }
    source_uri = _source_uri(payload)
    if source_uri:
        citation["sourceUri"] = source_uri
    issuing_body = str(payload.get("issuing_body") or "").strip()
    if issuing_body:
        citation["issuingBody"] = issuing_body

    evidence = {
        "citation_id": doc_id,
        "protocol_code": doc_id,
        "section": section,
        "protocol_content": retrieval_text,
        "retrieval_scope": "CLINICAL_AUTHORITY",
        "authority_status": "AUTHORITATIVE",
        "similarity_score": 1.0,
        "protocol_criteria": criteria,
        "decision_points": _strings(payload.get("decision_points")),
        "retrieval_facets": _strings(payload.get("retrieval_facets")),
        "provenance": {
            "pass5_version": pass5_version,
            "retrieval_text_sha256": content_hash,
            "atom_type": row["atom_type"],
            "source_occurrences": _source_occurrences(payload),
            "fallback": "DETERMINISTIC_RESOURCE_COUNT_AUTHORITY",
        },
    }
    return [evidence], [citation], criteria


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _source_occurrences(payload: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = payload.get("source_occurrences")
    if not isinstance(occurrences, list):
        return []
    return [dict(item) for item in occurrences if isinstance(item, dict)]


def _source_uri(payload: dict[str, Any]) -> str | None:
    candidate = str(payload.get("source_uri") or "").strip()
    if candidate.startswith(("https://", "http://")):
        return candidate
    for occurrence in _source_occurrences(payload):
        candidate = str(occurrence.get("source_uri") or "").strip()
        if candidate.startswith(("https://", "http://")):
            return candidate
    return None


def _protocol_criteria(doc_id: str, payload: dict[str, Any]) -> list[str]:
    criteria: list[str] = []
    for key in ("criterion_ids", "decision_criteria", "matched_protocol_criteria"):
        criteria.extend(_strings(payload.get(key)))
    criteria.extend(
        f"{doc_id}:decision_point:{value}"
        for value in _strings(payload.get("decision_points"))
    )
    criteria.extend(
        f"{doc_id}:facet:{value}"
        for value in _strings(payload.get("retrieval_facets"))
    )
    return list(dict.fromkeys(criteria))


def _relevance_band(score: float | None) -> str:
    """A label a reader can act on, instead of a number that looks like odds.

    A cosine similarity rendered as "58%" invites the reading "58% confident",
    which it is not: it is a distance in an embedding space with no calibrated
    relationship to anything clinical. Bands say what the number can support --
    how close this case is to the patient's presentation -- and nothing more.
    """
    if score is None:
        return "UNKNOWN"
    if score >= 0.75:
        return "HIGH"
    if score >= 0.5:
        return "MODERATE"
    return "LOW"

INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE = (
    "Hiện chưa đủ thông tin và bằng chứng đã được kiểm định để AI phân loại "
    "mức độ ưu tiên an toàn. Hồ sơ của bạn đã được chuyển tới hàng đợi thẩm "
    "định; vui lòng chờ điều dưỡng xác nhận và hướng dẫn bước tiếp theo. Nếu "
    "triệu chứng nặng lên hoặc xuất hiện dấu hiệu khẩn cấp, hãy gọi 115 hoặc "
    "đến cơ sở y tế gần nhất."
)

RETRIEVAL_FAILURE_MESSAGE = (
    "Hệ thống tra cứu phác đồ đang tạm thời gián đoạn do lỗi kỹ thuật nên AI "
    "chưa thể đưa ra phân loại ESI. Bạn vui lòng thử gửi lại sau ít phút; nếu "
    "cần được đánh giá ngay, hãy chủ động liên hệ nhân viên y tế. Nếu triệu "
    "chứng nặng lên hoặc xuất hiện dấu hiệu khẩn cấp, hãy gọi 115 hoặc đến cơ "
    "sở y tế gần nhất."
)


def build_insufficient_evidence_handoff(
    reason: str,
    *,
    step: int = 3,
    handoff_reason: str = "UNSPECIFIED",
) -> dict[str, Any]:
    """Build the single patient-safe terminal state for evidence abstention.

    ``handoff_reason`` is a short structured code recording *why* the turn had
    to stop. The patient-facing wording is deliberately the same in every case,
    but "we ran out of authority evidence", "the patient stopped answering" and
    "the reasoner abstained" are different operational events, and folding them
    into one indistinguishable outcome is what made every conversation look
    like it ended the same way.
    """
    message = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE,
        "step": step,
        "ragCitations": [],
    }
    return {
        "response": INSUFFICIENT_EVIDENCE_HANDOFF_MESSAGE,
        "messages": [message],
        "current_esi_level": None,
        "preliminary_esi_reasoning": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "response_type": "TEXT",
        "workflow_phase": "HANDOFF",
        "decision_status": "INSUFFICIENT_EVIDENCE",
        "evidence_sufficiency_outcome": "ABSTAIN",
        "handoff_reason": handoff_reason,
        "uncertainty_reasons": [reason],
        "next_step": "complete",
    }


def build_retrieval_failure_response(
    reason: str,
    *,
    step: int = 3,
) -> dict[str, Any]:
    """Keep an operational outage distinct from a clinical evidence finding."""
    message = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": RETRIEVAL_FAILURE_MESSAGE,
        "step": step,
        "ragCitations": [],
    }
    return {
        "response": RETRIEVAL_FAILURE_MESSAGE,
        "messages": [message],
        "current_esi_level": None,
        "preliminary_esi_reasoning": None,
        "sbar_report": None,
        "retrieved_evidence": [],
        "case_support_evidence": [],
        "turn_rag_citations": [],
        "retrieval_channels": [],
        "response_type": "TEXT",
        "workflow_phase": "RETRIEVAL",
        "decision_status": "RETRIEVAL_FAILURE",
        "evidence_status": "RETRIEVAL_FAILURE",
        "evidence_document_type": None,
        "evidence_authority_status": "NOT_EVALUATED",
        "evidence_sufficiency_outcome": "RETRIEVAL_FAILURE",
        "available_protocol_criteria": [],
        "matched_protocol_criteria": [],
        "uncertainty_reasons": [
            "Không thể đánh giá bằng chứng vì dịch vụ tra cứu gặp lỗi kỹ thuật"
        ],
        # Kept in internal state/audit only; the patient response above never
        # exposes provider, database, or credential details.
        "retrieval_error": reason,
        "next_step": "complete",
    }


@dataclass(frozen=True)
class EvidenceEvaluation:
    status: str
    citations: list[dict[str, Any]]
    eligible_for_esi: bool
    reasons: list[str]
    document_type: str | None
    authority_status: str
    matched_protocol_criteria: list[str]


def _required_metadata_present(result: dict[str, Any]) -> bool:
    required = (
        "protocol_code",
        "title",
        "issuing_body",
        "source",
        "source_uri",
        "license_reference",
        "version",
        "effective_date",
        "section",
        "reviewed_by",
        "reviewed_at",
        "parser_version",
        "content_hash",
    )
    return all(str(result.get(field) or "").strip() for field in required)


def evaluate_evidence(
    results: list[dict[str, Any]],
    *,
    missing_critical_fields: list[str] | None = None,
    unresolved_contradictions: list[dict[str, Any]] | None = None,
) -> EvidenceEvaluation:
    """Accept only traceable, calibrated and applicable approved protocols."""
    if unresolved_contradictions:
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=["Còn thông tin mâu thuẫn chưa được xác nhận"],
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )
    if missing_critical_fields:
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=["Còn thiếu trường lâm sàng bắt buộc"],
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )

    citations: list[dict[str, Any]] = []
    criteria: list[str] = []
    rejection_reasons: list[str] = []
    for result in results:
        source = str(result.get("source") or "").strip()
        if source == "MIETIC_v1" or result.get("document_type") == "case_example":
            rejection_reasons.append("Case example không phải bằng chứng phác đồ")
            continue
        if result.get("document_type") != "validated_protocol":
            rejection_reasons.append("Tài liệu không có loại validated_protocol")
            continue
        if result.get("validation_status") != "approved":
            rejection_reasons.append("Tài liệu chưa được clinician phê duyệt")
            continue
        if result.get("authority_status") != "AUTHORIZED":
            rejection_reasons.append("Nguồn tài liệu không thuộc whitelist")
            continue
        if not _required_metadata_present(result):
            rejection_reasons.append("Tài liệu thiếu metadata truy vết bắt buộc")
            continue
        if result.get("scope_match") is not True:
            rejection_reasons.append("Phạm vi phác đồ không khớp nhóm triệu chứng")
            continue
        matched_criteria = [
            str(item).strip()
            for item in result.get("matched_protocol_criteria", [])
            if str(item).strip()
        ]
        if not matched_criteria:
            rejection_reasons.append("Không có decision criterion khớp fact đã xác nhận")
            continue

        calibration_id = str(result.get("calibration_id") or "").strip()
        calibration = result.get("calibration_profile")
        score = float(result.get("similarity_score") or 0.0)
        if not calibration_id or not isinstance(calibration, dict):
            rejection_reasons.append("Retrieval score chưa có calibration profile được duyệt")
            continue
        if (
            calibration.get("symptom_cluster") != result.get("symptom_cluster")
            or calibration.get("population") not in {
                result.get("population"),
                "all_populations",
            }
            or not calibration.get("approved_by")
            or not calibration.get("approved_at")
        ):
            rejection_reasons.append("Calibration profile không khớp cluster/population")
            continue
        thresholds = calibration.get("thresholds")
        if not isinstance(thresholds, dict) or not thresholds:
            rejection_reasons.append("Calibration profile thiếu threshold theo channel")
            continue
        passing_channels = 0
        for channel_result in result.get("retrieval_channels", []):
            if not isinstance(channel_result, dict):
                continue
            channel = str(channel_result.get("channel") or "")
            channel_threshold = thresholds.get(channel)
            channel_score = channel_result.get("score")
            if channel_threshold is None or channel_score is None:
                continue
            if float(channel_score) >= float(channel_threshold):
                passing_channels += 1
        required_channels = int(calibration.get("min_passing_dense_channels") or 1)
        if passing_channels < required_channels:
            rejection_reasons.append(
                "Không đủ retrieval channel vượt ngưỡng đã calibrate"
            )
            continue

        content = str(result.get("protocol_content") or "").strip()
        protocol_code = str(result.get("protocol_code") or "").strip()
        if not content or not protocol_code:
            rejection_reasons.append("Protocol section không có nội dung hoặc mã nguồn")
            continue
        citation_id = str(result.get("citation_id") or "").strip()
        if not citation_id:
            rejection_reasons.append("Protocol section không có citation ID ổn định")
            continue
        citations.append(
            {
                "id": citation_id,
                "title": str(result["title"]),
                "protocolId": protocol_code,
                "excerpt": f"{content[:200]}..." if len(content) > 200 else content,
                "relevanceScore": round(score, 4),
                "issuingBody": str(result["issuing_body"]),
                "sourceUri": str(result["source_uri"]),
                "version": str(result["version"]),
                "section": str(result["section"]),
                "effectiveDate": str(result["effective_date"]),
                "validationStatus": "approved",
                "contentHash": str(result["content_hash"]),
                "reviewedBy": str(result["reviewed_by"]),
                "reviewedAt": str(result["reviewed_at"]),
                "calibrationId": calibration_id,
                "sourceType": "validated_protocol",
                "retrievalChannels": list(result.get("retrieval_channels", [])),
            }
        )
        criteria.extend(matched_criteria)

    if not citations:
        reasons = list(dict.fromkeys(rejection_reasons)) or [
            "Không tìm thấy phác đồ đã duyệt, đúng phạm vi và đạt calibration gate"
        ]
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=reasons,
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )
    return EvidenceEvaluation(
        status="SUFFICIENT",
        citations=citations,
        eligible_for_esi=True,
        reasons=[],
        document_type="validated_protocol",
        authority_status="AUTHORIZED",
        matched_protocol_criteria=list(dict.fromkeys(criteria)),
    )


def evaluate_demo_case_support(
    results: list[dict[str, Any]],
    *,
    missing_critical_fields: list[str] | None = None,
    unresolved_contradictions: list[dict[str, Any]] | None = None,
) -> EvidenceEvaluation:
    """Label usable MIETIC neighbors as demo context, never as a protocol."""
    if unresolved_contradictions:
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=["Còn thông tin mâu thuẫn chưa được xác nhận"],
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )
    if missing_critical_fields:
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=["Còn thiếu trường lâm sàng bắt buộc"],
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )

    citations: list[dict[str, Any]] = []
    for result in results:
        if (
            result.get("source") != "MIETIC_v1"
            or result.get("document_type") != "case_example"
            or result.get("authority_status") != "DEMO_ONLY"
        ):
            continue
        case_id = str(result.get("case_id") or "").strip()
        content = str(result.get("case_content") or "").strip()
        citation_id = str(result.get("citation_id") or "").strip()
        if not case_id or not content or not citation_id:
            continue
        excerpt = " ".join(content.split())
        citations.append(
            {
                "id": citation_id,
                "title": str(result.get("title") or f"Ca MIETIC {case_id}"),
                "protocolId": case_id,
                "excerpt": (
                    f"{excerpt[:240]}..." if len(excerpt) > 240 else excerpt
                ),
                "relevanceScore": round(
                    float(result.get("similarity_score") or 0.0),
                    4,
                ),
                "sourceType": "case_example",
                "retrievalChannels": list(
                    result.get("retrieval_channels", [])
                ),
            }
        )

    if not citations:
        return EvidenceEvaluation(
            status="INSUFFICIENT_EVIDENCE",
            citations=[],
            eligible_for_esi=False,
            reasons=["Không có đủ ca MIETIC tương tự vượt ngưỡng demo"],
            document_type=None,
            authority_status="REJECTED",
            matched_protocol_criteria=[],
        )
    return EvidenceEvaluation(
        status="CASE_EXAMPLE_SUPPORT",
        citations=citations,
        eligible_for_esi=True,
        reasons=[],
        document_type="case_example",
        authority_status="DEMO_ONLY",
        matched_protocol_criteria=[],
    )


async def retrieve_evidence_node(state: AgentState) -> dict[str, Any]:
    """Retrieve traceable ESI authority plus optional, quarantined case support.

    A successful vector search yields *candidates*, not a sufficiency verdict.
    The structured clinical reasoner decides whether those candidates and the
    canonical patient facts support a proposal, a targeted question, or one
    bounded retrieval refinement. Technical faults take a separate fail-safe
    response and can never become ``INSUFFICIENT_EVIDENCE``.
    """

    def _strings(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _source_occurrences(payload: dict[str, Any]) -> list[dict[str, Any]]:
        occurrences = payload.get("source_occurrences")
        if not isinstance(occurrences, list):
            return []
        return [dict(item) for item in occurrences if isinstance(item, dict)]

    def _source_uri(payload: dict[str, Any]) -> str | None:
        candidate = str(payload.get("source_uri") or "").strip()
        if candidate.startswith(("https://", "http://")):
            return candidate
        for occurrence in _source_occurrences(payload):
            candidate = str(occurrence.get("source_uri") or "").strip()
            if candidate.startswith(("https://", "http://")):
                return candidate
        return None

    def _criteria(doc_id: str, payload: dict[str, Any]) -> list[str]:
        criteria: list[str] = []
        for key in ("criterion_ids", "decision_criteria", "matched_protocol_criteria"):
            criteria.extend(_strings(payload.get(key)))
        criteria.extend(
            f"{doc_id}:decision_point:{value}"
            for value in _strings(payload.get("decision_points"))
        )
        criteria.extend(
            f"{doc_id}:facet:{value}"
            for value in _strings(payload.get("retrieval_facets"))
        )
        return list(dict.fromkeys(criteria))

    query_vi = str(state.get("retrieval_query_vi") or "").strip()
    query_en = str(state.get("retrieval_query_en") or "").strip()
    degraded = list(state.get("retrieval_degraded_modes", []))
    translated = translate_query(query_vi) if query_vi else None
    if translated:
        if translated.query_en and translated.query_en not in query_en:
            query_en = "; ".join(
                part for part in (query_en, translated.query_en) if part
            )
        degraded.extend(translated.degraded_modes)

    sparse_terms = [
        str(item).strip()
        for item in state.get("retrieval_sparse_terms", [])
        if str(item).strip()
    ]
    refinement = str(state.get("retrieval_refined_query") or "").strip()[:500]
    query_parts = [query_vi, query_en, " ".join(sparse_terms[:20]), refinement]
    combined = ". ".join(dict.fromkeys(part for part in query_parts if part))
    if not combined:
        return {
            "retrieved_evidence": [],
            "case_support_evidence": [],
            "turn_rag_citations": [],
            "retrieval_channels": [],
            "retrieval_degraded_modes": list(dict.fromkeys(degraded)),
            "evidence_status": "INSUFFICIENT_EVIDENCE",
            "evidence_sufficiency_outcome": "NEED_MORE_PATIENT_INFO",
            "evidence_document_type": None,
            "evidence_authority_status": "REJECTED",
            "available_protocol_criteria": [],
            "matched_protocol_criteria": [],
            "uncertainty_reasons": ["Không có patient facts để tạo truy vấn bằng chứng"],
            "decision_status": "INSUFFICIENT_EVIDENCE",
            "workflow_phase": "RETRIEVAL",
            "next_step": "insufficient_evidence",
        }

    # The English clinical queries this presentation supports. Grounded in
    # canonical state by construction: the vocabulary is derived from canonical
    # fact keys, so a query cannot mention a symptom nobody reported.
    settings = get_settings()
    planned = await plan_clinical_queries(
        build_problem_state_from_agent_state(state)
    )
    degraded.extend(planned.degraded_modes)
    authority_queries = _authority_queries(planned, combined, refinement)
    case_queries = _case_support_queries(planned)
    use_lexical = bool(settings.retrieval_hybrid_enabled)

    retriever = get_knowledge_retriever()
    decision_point = str(state.get("retrieval_decision_point") or "").strip() or None
    facets = [
        str(item).strip()
        for item in state.get("retrieval_facets", [])
        if str(item).strip()
    ][:8]
    try:
        authority, authority_audit = await retriever.search_esi_authority_hybrid(
            authority_queries,
            decision_point=decision_point,
            facets=facets or None,
            use_lexical=use_lexical,
            query_vi=query_vi,
            query_en=query_en,
        )
    except Exception as exc:  # noqa: BLE001 - provider boundary
        logger.exception("Unexpected ESI authority retrieval failure")
        update = build_retrieval_failure_response(
            f"{type(exc).__name__}: {exc}",
            step=int(state.get("step") or 3),
        )
        update["retrieval_degraded_modes"] = list(
            dict.fromkeys([*degraded, "RETRIEVAL_FAILURE:UNEXPECTED_AUTHORITY_ERROR"])
        )
        return update
    if authority.status.is_technical_failure:
        logger.error(
            "Evidence retrieval failed (%s): %s",
            authority.status.value,
            authority.error,
        )
        update = build_retrieval_failure_response(
            authority.error or authority.status.value,
            step=int(state.get("step") or 3),
        )
        update["retrieval_degraded_modes"] = list(
            dict.fromkeys(
                [*degraded, f"RETRIEVAL_FAILURE:{authority.status.value}"]
            )
        )
        update["retrieval_audit"] = {"authority": authority.audit()}
        return update

    # Case support runs its own, narrower query set: the bare primary-symptom
    # query that helps find the governing *rule* matches every case with that
    # symptom, so it is excluded here. No label or case text is sent to the ESI
    # reasoner; the two pipelines only share the patient's canonical facts.
    try:
        case_support, case_support_audit = await retriever.search_mietic_cases_hybrid(
            case_queries,
            use_lexical=use_lexical,
            query_vi=query_vi,
            query_en=query_en,
            top_k=int(settings.retrieval_candidate_pool_size),
        )
    except Exception as exc:  # noqa: BLE001 - optional support boundary
        # MIETIC is optional CASE_SUPPORT. An adapter fault must be visible in
        # audit/degraded mode, but it cannot erase usable ESI authority or turn
        # a support outage into a clinical conclusion.
        logger.exception("Unexpected MIETIC case-support retrieval failure")
        case_support = RetrievalOutcome(
            status=RetrievalStatus.RETRIEVAL_FAILURE,
            query_vi=query_vi,
            query_en=query_en,
            channels=("dense",),
            filters={"retrieval_scope": "CASE_SUPPORT"},
            error=f"{type(exc).__name__}: {exc}",
        )
        case_support_audit = {}
    if case_support.status.is_technical_failure:
        degraded.append(f"CASE_SUPPORT_UNAVAILABLE:{case_support.status.value}")

    channel_name = "hybrid" if use_lexical else "en_dense"
    evidence: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    matched_criteria: list[str] = []
    rejected_untraceable = 0
    for rank, item in enumerate(authority.authority_items, start=1):
        payload = item.metadata.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        content_hash = str(item.metadata.get("retrieval_text_sha256") or "").strip()
        pass5_version = str(item.metadata.get("pass5_version") or "").strip()
        if not item.text.strip() or not content_hash or not pass5_version:
            rejected_untraceable += 1
            continue
        criteria = _criteria(item.doc_id, payload)
        if not criteria:
            rejected_untraceable += 1
            continue
        matched_criteria.extend(criteria)
        section = str(
            payload.get("heading_path")
            or payload.get("section")
            or payload.get("source_heading")
            or ""
        )
        channel = {"channel": channel_name, "rank": rank, "score": item.score}
        citation: dict[str, Any] = {
            "id": item.doc_id,
            "title": str(
                payload.get("title")
                or payload.get("heading")
                or section
                or item.doc_id
            ),
            "protocolId": item.doc_id,
            "excerpt": item.text[:240] + ("..." if len(item.text) > 240 else ""),
            "relevanceScore": round(item.score, 4),
            "sourceType": "validated_protocol",
            "version": pass5_version,
            "section": section or None,
            "contentHash": content_hash,
            "retrievalChannels": [channel],
        }
        source_uri = _source_uri(payload)
        if source_uri:
            citation["sourceUri"] = source_uri
        issuing_body = str(payload.get("issuing_body") or "").strip()
        if issuing_body:
            citation["issuingBody"] = issuing_body
        citations.append(citation)
        evidence.append(
            {
                "citation_id": item.doc_id,
                "protocol_code": item.doc_id,
                "section": section,
                "protocol_content": item.text,
                "retrieval_scope": item.retrieval_scope,
                "authority_status": item.authority_status,
                "similarity_score": item.score,
                "protocol_criteria": criteria,
                "decision_points": _strings(payload.get("decision_points")),
                "retrieval_facets": _strings(payload.get("retrieval_facets")),
                "provenance": {
                    "pass5_version": pass5_version,
                    "retrieval_text_sha256": content_hash,
                    "atom_type": item.metadata.get("atom_type"),
                    "source_occurrences": _source_occurrences(payload),
                },
            }
        )

    fallback_evidence, fallback_citations, fallback_criteria = (
        await _resource_authority_fallback(state, channel_name=channel_name)
    )
    if fallback_evidence and fallback_citations:
        existing_ids = {
            str(item.get("citation_id"))
            for item in evidence
            if isinstance(item, dict) and item.get("citation_id")
        }
        new_evidence = [
            item
            for item in fallback_evidence
            if str(item.get("citation_id")) not in existing_ids
        ]
        new_ids = {
            str(item.get("citation_id"))
            for item in new_evidence
            if isinstance(item, dict) and item.get("citation_id")
        }
        new_citations = [
            item
            for item in fallback_citations
            if isinstance(item, dict) and str(item.get("id")) in new_ids
        ]
        if new_evidence and new_citations:
            evidence.extend(new_evidence)
            citations.extend(new_citations)
            matched_criteria.extend(fallback_criteria)
            degraded.append("RESOURCE_AUTHORITY_FALLBACK")

    candidates_retrieved = bool(evidence) and bool(citations)
    case_items, case_rank_audit = await _rank_case_support(
        case_support,
        planned,
        settings=settings,
    )
    top_score = max((item["similarity_score"] for item in evidence), default=None)
    audit = {
        "authority": authority.audit(),
        "case_support": case_support.audit(),
        "query_plan": planned.to_dict(),
        "authority_channels": authority_audit.get("channels", {}),
        "case_support_channels": case_support_audit.get("channels", {}),
        "case_support_ranking": case_rank_audit,
        "rejected_untraceable_authority_count": rejected_untraceable,
        "refinement_count": int(state.get("retrieval_refinement_count") or 0),
    }
    return {
        "retrieved_evidence": evidence,
        "turn_rag_citations": citations,
        "case_support_evidence": case_items,
        "retrieval_channels": [
            {
                "channel": channel_name,
                "result_count": len(evidence),
                "top_score": top_score,
                "degraded": False,
            }
        ],
        "retrieval_degraded_modes": list(dict.fromkeys(degraded)),
        # RETRIEVED means candidates passed the corpus/provenance boundary. It
        # is intentionally not SUFFICIENT until the structured reasoner proves
        # a decision against patient facts and citations.
        "evidence_status": (
            "RETRIEVED" if candidates_retrieved else "INSUFFICIENT_EVIDENCE"
        ),
        "evidence_sufficiency_outcome": (
            "PENDING_EVALUATION" if candidates_retrieved else "NEED_MORE_EVIDENCE"
        ),
        "evidence_document_type": "validated_protocol" if candidates_retrieved else None,
        "evidence_authority_status": "AUTHORIZED" if candidates_retrieved else "REJECTED",
        # These are candidates exposed by traceable authority atoms. They are
        # not "matched" until the structured reasoner cites the owning document
        # and returns a criterion from that same document.
        "available_protocol_criteria": list(dict.fromkeys(matched_criteria)),
        "matched_protocol_criteria": [],
        "uncertainty_reasons": (
            []
            if candidates_retrieved
            else ["Không tìm thấy phác đồ ESI có provenance đủ để đánh giá"]
        ),
        "decision_status": (
            "READY_FOR_REASONING" if candidates_retrieved else "INSUFFICIENT_EVIDENCE"
        ),
        "retrieval_error": None,
        "retrieval_audit": audit,
        "workflow_phase": "RETRIEVAL",
        "next_step": "triage_reasoner" if candidates_retrieved else "insufficient_evidence",
    }


async def respond_to_insufficient_evidence_node(
    state: AgentState,
) -> dict[str, Any]:
    reasons = state.get("uncertainty_reasons", [])
    reason = "; ".join(str(item) for item in reasons if str(item).strip())
    return build_insufficient_evidence_handoff(
        reason or "Evidence gate không tìm thấy nguồn đã kiểm định đủ thẩm quyền",
        step=int(state.get("step") or 3),
        handoff_reason="NO_AUTHORITY_EVIDENCE_RETRIEVED",
    )
