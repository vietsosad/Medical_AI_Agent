"""Nút Phân Tích & Tiêm Ký ức Lâm Sàng (Intake Analyzer & Profile Memory Injection Node).

Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md & TRIAGE_AGENT_SOLUTION_DESIGN.md:
- Immutability trong clinical state (luôn trả partial update mới cho Dict).
- Tiêm đúng tiền sử lâm sàng từ EHRProfile tương ứng với hồ sơ thân nhân (Multi-Profile).
- Thực thi Chỉ thị Lâm sàng đặc thù: Kích hoạt Khiên Nhi khoa (<16 tuổi) hoặc Lão khoa (>=65 tuổi).
"""

import re
from typing import Any

from src.agents.guardrails import (
    extract_patient_reported_vital_context,
    extract_patient_reported_vitals,
)
from src.agents.nodes.answer_validator import (
    EHR_CONFIRMATION_OPTION_IDS,
    RECENT_PROCEDURE_PATTERNS,
    VITAL_UNAVAILABLE_PATTERNS,
)
from src.agents.nodes.intent_classifier import normalize_vietnamese_text
from src.agents.blueprint_projection import ingest_blueprint, project_blueprint
from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.adaptive_questions import canonical_key_for_field
from src.agents.nodes.fact_extraction import (
    ExtractedFact,
    apply_message_to_state,
    extract_facts,
)
from src.agents.nodes.problem_attribute_extraction import extract_answer_for_target
from src.agents.nodes.severity_extraction import extract_severity_score
from src.agents.state import AgentState


SYMPTOM_TERMS = (
    "đau đầu",
    "đau ngực",
    "đau bụng",
    "đau lưng",
    "đau họng",
    "khó thở",
    "buồn nôn",
    "chóng mặt",
    "tiêu chảy",
    "phát ban",
    "chảy máu",
    "sốt",
    "ho",
    "nôn",
    "mệt",
)
ASSOCIATED_TERMS = (
    "sốt",
    "rét run",
    "buồn nôn",
    "nôn",
    "chóng mặt",
    "choáng",
    "khó thở",
    "vã mồ hôi",
)
GENERIC_SYMPTOM_DESCRIPTORS = {
    "dau",
    "te",
    "ngua",
    "sung",
    "moi",
    "tuc",
    "rat",
    "yeu",
}
SYMPTOM_PHRASE_STOP_WORDS = {
    "ban",
    "oi",
    "nhe",
    "a",
    "voi",
    "va",
    "nhung",
    "tu",
    "luc",
    "khi",
    "duoc",
    "roi",
    "qua",
    "lam",
    "hom",
    "sang",
    "trua",
    "toi",
}
EHR_CONTEXT_PATTERNS = (
    "benh nen",
    "di ung",
    "thuoc dang dung",
    "thuoc hang ngay",
    "doi thuoc",
    "ngung thuoc",
)
def resolve_ehr_confirmation_choice(
    option_id: str,
    *,
    clinical_memory_updated_at: str | None,
) -> tuple[str, bool, str | None]:
    """Map a server-issued EHR option ID to its deterministic workflow state."""
    if option_id == "ehr_confirmed":
        return "CONFIRMED", False, clinical_memory_updated_at
    if option_id == "ehr_changed":
        return "NOT_REVIEWED", True, None
    if option_id == "ehr_unsure":
        return "UNCERTAIN", False, clinical_memory_updated_at
    raise ValueError(f"Unsupported EHR confirmation option: {option_id}")


def _merge_unique(original: list[str], additions: list[str]) -> list[str]:
    return list(dict.fromkeys([*original, *additions]))


def _drop_subsumed_terms(terms: list[str]) -> list[str]:
    """Drop a matched term that is contained in another matched term.

    The lexicon overlaps by design -- "nôn" is a word inside "buồn nôn" -- so
    one complaint can match twice. Keeping both is not wrong, but showing the
    patient "buồn nôn, nôn" to confirm reads as two findings where they
    reported one.
    """
    kept: list[str] = []
    for term in terms:
        if any(
            other != term and term in other
            for other in terms
        ):
            continue
        kept.append(term)
    return kept


def _raw_span(query: str, value: Any) -> str:
    """Return the smallest available verbatim span for a patient-reported fact."""
    candidate = str(value).strip()
    if candidate:
        start = query.lower().find(candidate.lower())
        if start >= 0:
            return query[start : start + len(candidate)]
    return query.strip()[:300]


def _build_fact_updates(
    query: str,
    current: dict[str, Any],
    proposed: dict[str, Any],
    provenance: dict[str, list[dict[str, Any]]],
    source_turn_id: str,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
]:
    """Commit non-conflicting facts and stage scalar conflicts for clarification."""
    committed = {
        **proposed,
        "chief_complaint": list(proposed.get("chief_complaint", [])),
        "associated_symptoms": list(proposed.get("associated_symptoms", [])),
        "vital_signs": dict(proposed.get("vital_signs", {})),
    }
    updated_provenance = {
        field: [dict(item) for item in records]
        for field, records in provenance.items()
    }
    pending_updates: list[dict[str, Any]] = []

    scalar_fields = (
        "onset_time",
        "severity_score",
        "radiation",
        "recent_procedure",
        "clinical_context_note",
    )
    for field in scalar_fields:
        previous = current.get(field)
        value = proposed.get(field)
        if value is None or value == previous:
            continue
        previous_records = updated_provenance.get(field, [])
        previous_record = previous_records[-1] if previous_records else {}
        is_conflict = field == "onset_time" and previous not in (None, "")
        record = {
            "field": field,
            "value": value,
            "source_turn_id": source_turn_id,
            "raw_span": _raw_span(query, value),
            "status": "DISPUTED" if is_conflict else "CONFIRMED",
            "previous_value": previous,
            "previous_turn_id": str(
                previous_record.get("source_turn_id") or "legacy-checkpoint"
            ),
            "previous_raw_span": str(
                previous_record.get("raw_span") or previous or ""
            ),
        }
        pending_updates.append(record)
        updated_provenance.setdefault(field, []).append(record)
        if is_conflict:
            # Never silently overwrite the earlier onset. The dedicated
            # contradiction node decides whether clarification is required.
            committed[field] = previous

    for field in ("chief_complaint", "associated_symptoms"):
        previous_items = list(current.get(field, []))
        for value in proposed.get(field, []):
            if value in previous_items:
                continue
            record = {
                "field": field,
                "value": value,
                "source_turn_id": source_turn_id,
                "raw_span": _raw_span(query, value),
                "status": "CONFIRMED",
            }
            pending_updates.append(record)
            updated_provenance.setdefault(field, []).append(record)

    previous_vitals = dict(current.get("vital_signs", {}))
    for key, value in proposed.get("vital_signs", {}).items():
        if previous_vitals.get(key) == value:
            continue
        field = f"vital_signs.{key}"
        record = {
            "field": field,
            "value": value,
            "source_turn_id": source_turn_id,
            "raw_span": _raw_span(query, value),
            "status": "CONFIRMED",
        }
        pending_updates.append(record)
        updated_provenance.setdefault(field, []).append(record)

    return committed, updated_provenance, pending_updates


def _projected_fact_records(
    before: dict[str, Any],
    after: dict[str, Any],
    already_recorded: list[dict[str, Any]],
    source_turn_id: str,
) -> list[dict[str, Any]]:
    """Provenance for values the canonical projection added to the blueprint."""
    seen = {str(item.get("field")) for item in already_recorded}
    previous_vitals = dict(before.get("vital_signs") or {})
    records: list[dict[str, Any]] = []
    for key, value in (after.get("vital_signs") or {}).items():
        field = f"vital_signs.{key}"
        if field in seen or previous_vitals.get(key) == value:
            continue
        records.append(
            {
                "field": field,
                "value": value,
                "source_turn_id": source_turn_id,
                "raw_span": str(value)[:120],
                "status": "CONFIRMED",
            }
        )
    return records


# Canonical wording for the two ways a patient can settle the associated-symptom
# question without naming one. Fixed strings, so they map to stable canonical
# keys instead of to whatever sentence the patient happened to type.
NO_ASSOCIATED_SYMPTOM_PHRASE = "không có triệu chứng đi kèm"

NO_CURRENT_SYMPTOM_PATTERNS = (
    r"\b(?:toi\s+)?khong\s+(?:bi|co|thay|cam thay)?\s*(?:kho chiu|dau|dau don|trieu chung)(?:\s+gi|\s+gi het|\s+nao)?\b",
    r"\bkhong\s+co\s+trieu\s+chung(?:\s+cap|\s+gi|\s+nao)?\b",
    r"\b(?:hien tai\s+)?(?:toi\s+)?binh thuong\b",
    r"\bkhong\s+bi\s+kho\s+chiu\s+gi\s+het\b",
)
UNSURE_ASSOCIATED_SYMPTOM_PHRASE = "không rõ triệu chứng đi kèm"


def _extract_generic_symptom_phrases(text: str) -> list[str]:
    """Extract symptom phrases by grammar so body locations are not hard-coded."""
    original_tokens = re.findall(r"[^\W\d_]+|\d+", text.lower(), flags=re.UNICODE)
    normalized_tokens = [normalize_vietnamese_text(token) for token in original_tokens]
    phrases: list[str] = []

    for index, token in enumerate(normalized_tokens):
        if token not in GENERIC_SYMPTOM_DESCRIPTORS:
            continue
        if index > 0 and normalized_tokens[index - 1] in {"khong", "chua", "ko"}:
            continue
        if (
            index > 1
            and normalized_tokens[index - 2] in {"khong", "chua", "ko"}
            and normalized_tokens[index - 1] == "con"
        ):
            continue
        if token == "dau" and original_tokens[index] not in {"đau", "dau"}:
            # Vietnamese words “đau”, “dấu” and “đâu” fold to the same
            # ASCII token. Only the actual symptom spelling (or unaccented
            # patient input) is allowed to create a pain fact.
            continue
        if token == "moi" and original_tokens[index] != "mỏi":
            continue
        phrase_tokens = [original_tokens[index]]
        for offset in range(index + 1, min(index + 6, len(original_tokens))):
            next_token = normalized_tokens[offset]
            if next_token in SYMPTOM_PHRASE_STOP_WORDS:
                break
            phrase_tokens.append(original_tokens[offset])
        phrase = " ".join(phrase_tokens).strip()
        if phrase:
            phrases.append(phrase[:120])

    return list(dict.fromkeys(phrases))


def _contains_non_negated_term(text: str, term: str) -> bool:
    """Do not convert explicit denials into positive clinical facts."""
    for match in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", text):
        prefix = normalize_vietnamese_text(text[max(0, match.start() - 24):match.start()])
        if not re.search(r"(?:khong|chua|ko)(?:\s+con)?\s*$", prefix):
            return True
    return False


def _is_no_current_symptom_statement(text: str) -> bool:
    folded = normalize_vietnamese_text(text.strip().lower())
    if not folded:
        return False
    return any(re.search(pattern, folded) for pattern in NO_CURRENT_SYMPTOM_PATTERNS)


def extract_blueprint_deterministically(
    query: str,
    current: dict[str, Any],
    active_question: dict[str, Any] | None,
    answer_alignment: str = "NOT_APPLICABLE",
) -> dict[str, Any]:
    """Extract common answers locally so safety does not depend on LLM availability."""
    updated: dict[str, Any] = {
        "chief_complaint": list(current.get("chief_complaint", [])),
        "clinical_keywords_en": list(current.get("clinical_keywords_en", [])),
        "onset_time": current.get("onset_time"),
        "severity_score": current.get("severity_score"),
        "radiation": current.get("radiation"),
        "associated_symptoms": list(current.get("associated_symptoms", [])),
        "current_medication": list(current.get("current_medication", [])),
        "recent_procedure": current.get("recent_procedure"),
        "clinical_context_note": current.get("clinical_context_note"),
        "vital_signs": dict(current.get("vital_signs", {})),
        "vital_signs_source": current.get("vital_signs_source"),
        "vital_signs_measured_at": current.get("vital_signs_measured_at"),
        "confidence_score": float(current.get("confidence_score", 0.0)),
    }
    text = query.strip().lower()
    folded = normalize_vietnamese_text(text)
    field = (
        (active_question or {}).get("field")
        if answer_alignment in {"NOT_APPLICABLE", "DIRECT_ANSWER"}
        else None
    )
    no_current_symptom_statement = _is_no_current_symptom_statement(text)

    found_symptoms = (
        []
        if no_current_symptom_statement
        else [
            term
            for term in SYMPTOM_TERMS
            if _contains_non_negated_term(text, term)
        ]
    )
    # A reply that answers a question *about a problem we already know about*
    # is a description of that problem, not a new complaint. Without this,
    # "Đau tăng dần lên, giờ nặng hơn lúc sáng" -- an answer about the course
    # of a headache already on the record -- became three more chief
    # complaints ("đau", "đau nặng hơn", "đau tăng dần lên giờ nặng") and the
    # patient was shown all of them to confirm.
    #
    # Scoped to adaptive targets only. The legacy slots keep their behaviour,
    # so a free-text complaint or an associated-symptom answer is still read
    # the way it always was.
    answering_known_problem = (
        canonical_key_for_field(str((active_question or {}).get("field") or ""))
        is not None
        and answer_alignment == "DIRECT_ANSWER"
    )
    if not answering_known_problem and not no_current_symptom_statement:
        found_symptoms = _merge_unique(
            found_symptoms,
            _extract_generic_symptom_phrases(text),
        )
    if (
        field == "chief_complaint"
        and text
        and not found_symptoms
        and not no_current_symptom_statement
    ):
        found_symptoms = [query.strip()[:120]]
    if found_symptoms and field != "associated_symptoms":
        updated["chief_complaint"] = _merge_unique(updated["chief_complaint"], found_symptoms)

    onset_patterns = (
        r"(?:từ|khoảng|được)\s+(hôm qua|hôm nay|sáng nay|trưa nay|tối qua)",
        r"(?:mới|khoảng|từ)\s+(\d+\s*(?:phút|giờ|tiếng|ngày|tuần))",
        r"(vài\s+(?:phút|giờ|tiếng|ngày|tuần))",
    )
    onset_found = False
    for pattern in onset_patterns:
        match = re.search(pattern, text)
        if match:
            updated["onset_time"] = match.group(0)
            onset_found = True
            break
    if field == "onset_time" and text and not onset_found:
        updated["onset_time"] = query.strip()[:120]

    # A bare digit is not a pain score. Severity is only recorded from an
    # explicit score construction, or as the answer to the 0-10 scale question.
    severity = extract_severity_score(
        query,
        severity_question_active=field == "severity_score",
    )
    if severity.score is not None:
        updated["severity_score"] = severity.score

    associated = [
        term
        for term in ASSOCIATED_TERMS
        if _contains_non_negated_term(text, term)
        and (len(found_symptoms) > 1 or term not in found_symptoms)
    ]
    if field == "associated_symptoms":
        current_chief_complaints = {
            normalize_vietnamese_text(str(item).strip())
            for item in current.get("chief_complaint", [])
            if str(item).strip()
        }
        associated = _merge_unique(
            associated,
            [
                symptom
                for symptom in found_symptoms
                if normalize_vietnamese_text(symptom)
                not in current_chief_complaints
            ],
        )
    if field == "associated_symptoms" and (
        "không có" in text or "không rõ" in text or "không chắc" in text
    ):
        # The slot has been answered and must stop being asked, but the answer
        # is a denial -- not a symptom. Filing the patient's whole sentence
        # here made "Không có dấu hiệu nào đi kèm" a canonical associated
        # symptom (``associated.khong_co_dau_hieu_nao_di_kem``) and had the
        # agent read it back as one: "Mình đã ghi nhận thêm - các triệu chứng
        # đi kèm: Không có dấu hiệu nào đi kèm." One fixed phrase per answer
        # keeps the slot settled without inventing an entity from a sentence.
        associated.append(
            NO_ASSOCIATED_SYMPTOM_PHRASE
            if "không có" in text
            else UNSURE_ASSOCIATED_SYMPTOM_PHRASE
        )
    if associated:
        updated["associated_symptoms"] = _merge_unique(
            updated["associated_symptoms"], associated
        )

    if any(pattern in folded for pattern in RECENT_PROCEDURE_PATTERNS):
        updated["recent_procedure"] = query.strip()[:300]
    elif field == "recent_procedure" and text:
        updated["recent_procedure"] = query.strip()[:300]

    if field == "clinical_memory_update_detail" and text:
        updated["clinical_context_note"] = query.strip()[:500]

    reported_vitals = extract_patient_reported_vitals(query)
    if reported_vitals:
        updated["vital_signs"] = {
            **updated["vital_signs"],
            **reported_vitals,
        }
        vital_context = extract_patient_reported_vital_context(query)
        if vital_context.get("source"):
            updated["vital_signs_source"] = vital_context["source"]
        if vital_context.get("measured_at"):
            updated["vital_signs_measured_at"] = vital_context["measured_at"]

    # "nôn" also matches inside "buồn nôn": one complaint, matched twice by an
    # overlapping lexicon. Both are true, but showing the patient "buồn nôn,
    # nôn" to confirm reads as two findings where they reported one. Applied
    # last so the extraction branches above still see what they matched.
    updated["chief_complaint"] = _drop_subsumed_terms(updated["chief_complaint"])
    updated["associated_symptoms"] = _drop_subsumed_terms(
        updated["associated_symptoms"]
    )

    chief_specific = bool(updated["chief_complaint"])
    has_detail = updated["severity_score"] is not None or bool(updated["associated_symptoms"])
    updated["confidence_score"] = round(
        (0.4 if chief_specific else 0.0)
        + (0.3 if updated["onset_time"] else 0.0)
        + (0.3 if has_detail else 0.0),
        2,
    )
    return updated


async def analyze_patient_intake(state: AgentState) -> dict:
    """Nút thu nhận và trích xuất thông tin người bệnh thành JSON Blueprint (Slot-Filling)."""
    special_instructions = list(state.get("special_instructions", []))
    age = state.get("patient_age")
    relationship = state.get("relationship_type", "SELF").upper()
    current_blueprint = state.get("clinical_blueprint", {})
    alignment = state.get("answer_alignment", "NOT_APPLICABLE")
    query = state.get("query", "")
    # The open question is kept whatever the router decided this turn was.
    #
    # Discarding it when the intent came back TRIAGE_NEW_SYMPTOM was the single
    # largest source of repeated questions in the live audit: the classifier
    # returns "new symptom during unrelated follow-up" for any reply carrying a
    # symptom word, so "Không, tôi từng đau hơn hồi năm ngoái" -- a clear *no*
    # to "is this the worst headache you have ever had?" -- threw the question
    # away, bound nothing, and had the agent ask the same question again. To
    # the patient that is the agent forgetting what it just asked.
    #
    # Nothing is filed blindly in exchange. Alignment still has to say the
    # reply answers this question, the target must still be UNKNOWN, and
    # ``extract_answer_for_target`` still declines a message that raises a new
    # symptom. Those are the fine-grained guards; dropping the question was a
    # blunt one that also removed the correct cases.
    active_question = state.get("active_question")
    raw_active_field = str((active_question or {}).get("field") or "")
    resolving_field = (
        raw_active_field.removeprefix("contradiction_")
        if raw_active_field.startswith("contradiction_")
        and alignment == "DIRECT_ANSWER"
        else None
    )
    # A contradiction question is intentionally free text. Alignment alone is
    # not enough to settle it: the generic validator accepts any substantive
    # reply so the patient can phrase the correction naturally. Only an
    # explicitly extracted value for the disputed canonical key is a
    # structured resolution; "tôi không biết" must leave the conflict open.
    resolution_fact = None
    if resolving_field:
        resolution_fact = next(
            (
                fact
                for fact in extract_facts(
                    query,
                    severity_question_active=resolving_field == "severity_score",
                )
                if fact.key == resolving_field
            ),
            None,
        )
    extraction_question = (
        {**(active_question or {}), "field": resolving_field}
        if resolution_fact is not None
        else active_question
    )
    deterministic_blueprint = extract_blueprint_deterministically(
        query,
        current_blueprint,
        extraction_question,
        alignment,
    )
    source_turn_id = state.get("current_turn_id") or (
        f"{state.get('session_id', 'session')}:turn:{len(state.get('messages', []))}"
    )
    provenance_before_update = state.get("clinical_fact_provenance", {})
    current_for_update = current_blueprint
    remaining_contradictions = list(state.get("unresolved_contradictions", []))
    if resolving_field and resolution_fact is not None:
        current_for_update = {**current_blueprint, resolving_field: None}
        provenance_before_update = {
            field: [dict(item) for item in records]
            for field, records in provenance_before_update.items()
        }
        if provenance_before_update.get(resolving_field):
            provenance_before_update[resolving_field][-1]["status"] = "SUPERSEDED"
        remaining_contradictions = [
            item
            for item in remaining_contradictions
            if str(item.get("field") or item.get("key") or "")
            != resolving_field
        ]
    (
        deterministic_blueprint,
        fact_provenance,
        pending_fact_updates,
    ) = _build_fact_updates(
        query,
        current_for_update,
        deterministic_blueprint,
        provenance_before_update,
        source_turn_id,
    )

    folded_query = normalize_vietnamese_text(query)
    active_field = str((active_question or {}).get("field") or "")
    procedure_mentioned = any(
        pattern in folded_query for pattern in RECENT_PROCEDURE_PATTERNS
    )
    procedure_pending = state.get("clinical_context_update_pending", False)
    if procedure_mentioned and active_field != "recent_procedure":
        procedure_pending = True
    elif active_field == "recent_procedure" and alignment == "DIRECT_ANSWER":
        procedure_pending = False

    memory_status = state.get(
        "clinical_memory_confirmation_status",
        "NOT_REVIEWED",
    )
    memory_update_pending = state.get("clinical_memory_update_pending", False)
    confirmed_memory_updated_at = state.get("confirmed_clinical_memory_updated_at")
    selected_option_id = state.get("selected_option_id")
    if selected_option_id in EHR_CONFIRMATION_OPTION_IDS:
        (
            memory_status,
            memory_update_pending,
            confirmed_memory_updated_at,
        ) = resolve_ehr_confirmation_choice(
            selected_option_id,
            clinical_memory_updated_at=state.get("clinical_memory_updated_at"),
        )
    elif active_field == "clinical_memory_confirmation" and alignment == "DIRECT_ANSWER":
        if selected_option_id is None and any(
            marker in folded_query
            for marker in ("van dung", "khong thay doi", "chinh xac", "dung")
        ):
            memory_status = "CONFIRMED"
            memory_update_pending = False
            confirmed_memory_updated_at = state.get("clinical_memory_updated_at")
        elif selected_option_id is None and any(
            marker in folded_query
            for marker in ("thay doi", "can sua", "khong dung")
        ):
            memory_status = "NOT_REVIEWED"
            memory_update_pending = True
            confirmed_memory_updated_at = None
        else:
            memory_status = "UNCERTAIN"
            memory_update_pending = False
            confirmed_memory_updated_at = state.get("clinical_memory_updated_at")
    elif active_field == "clinical_memory_update_detail" and alignment == "DIRECT_ANSWER":
        memory_status = "UPDATED_BY_PATIENT"
        memory_update_pending = False
        confirmed_memory_updated_at = state.get("clinical_memory_updated_at")
    elif memory_update_pending and len(query.strip()) >= 3:
        # We asked what changed in their record, and they wrote something. That
        # is the answer, whether or not ``active_question`` survived the trip
        # through the checkpoint and the transcript.
        #
        # This gate used to close only when the open question could still be
        # identified. The persisted AI message stores a short title rather than
        # the question text, so recovering it depends on a structured payload
        # that a free-text question does not have -- and when that failed the
        # patient was asked the identical question again, immediately after
        # answering it. Being re-asked something you just answered is the single
        # clearest way for software to say it was not listening.
        memory_status = "UPDATED_BY_PATIENT"
        memory_update_pending = False
        confirmed_memory_updated_at = state.get("clinical_memory_updated_at")
    elif (
        state.get("intake_confirmation_status") == "AWAITING_CONFIRMATION"
        and any(marker in folded_query for marker in EHR_CONTEXT_PATTERNS)
    ):
        deterministic_blueprint["clinical_context_note"] = query.strip()[:500]
        memory_status = "UPDATED_BY_PATIENT"
        memory_update_pending = False
        confirmed_memory_updated_at = state.get("clinical_memory_updated_at")

    vital_status = state.get("vital_signs_status", "NOT_REVIEWED")
    if active_field == "vital_signs" and alignment == "DIRECT_ANSWER" and any(
        marker in folded_query for marker in VITAL_UNAVAILABLE_PATTERNS
    ):
        vital_status = "UNAVAILABLE_CONFIRMED"
    elif active_field == "vital_signs" and alignment == "DIRECT_ANSWER":
        vital_status = "UNCERTAIN"

    # 1. Các kiểm tra Guardrail như Nhi Khoa, Lão Khoa... (giữ nguyên logic gốc)
    if relationship == "CHILD" or (age is not None and age < 16):
        special_instructions.append("🍼 [KHIÊN NHI KHOA]...")
    elif relationship == "PARENT" or (age is not None and age >= 65):
        special_instructions.append("👵 [KHIÊN LÃO KHOA]...")

    # Translation/query expansion happens only after patient confirmation in
    # bilingual_query_builder. Intake remains deterministic and cannot stall
    # or silently add a clinical fact through an external model provider.
    updated_blueprint = deterministic_blueprint

    # Canonical Patient State runs from the same message, independently of the
    # question we happened to ask. It carries the semantics the flat blueprint
    # cannot hold: UNKNOWN vs NEGATED, temporal context, and provenance.
    canonical = CanonicalPatientState.from_dict(state.get("canonical_state"))
    severity_question_active = active_field == "severity_score" or active_field.endswith(
        ".severity_score"
    )
    apply_message_to_state(
        canonical,
        query,
        turn_id=source_turn_id,
        severity_question_active=severity_question_active,
    )
    if resolving_field and resolution_fact is not None:
        # Generic extraction preserves every observation and can therefore add
        # another disputed value. The explicit contradiction workflow must
        # then settle the conflict in the canonical source of truth, not just
        # remove the legacy flat-list marker. Preserve the extractor's status
        # and timing (especially NEGATED symptom answers) on the resolver's
        # auditable observation.
        resolved = canonical.resolve_contradiction(
            resolving_field,
            resolution_fact.value,
            turn_id=source_turn_id,
            raw_span=resolution_fact.raw_span or query.strip()[:300],
        )
        resolved.status = resolution_fact.status
        resolved.source = resolution_fact.source
        resolved.temporal = resolution_fact.temporal
        resolved.temporal_label = resolution_fact.temporal_label
        resolved.confidence = resolution_fact.confidence
    # An answer to an adaptive question belongs to the attribute that was
    # actually asked about. The generic extractors write shared keys ("course",
    # "frequency"), which the problem projection attributes to the *primary*
    # problem -- so without this, "3 lần" answering a question about the nausea
    # would be filed against the headache and the nausea question would be
    # asked again next turn.
    # The planner target, not the slot the question was rendered through. A
    # symptom probe ("Bạn có thấy đau ngực kèm theo không?") is rendered on the
    # legacy ``associated_symptoms`` slot so it keeps its structured payload,
    # which meant "Không có." settled the slot and left ``symptom.chest_pain``
    # UNKNOWN -- so the same probe was asked again on the next turn. The
    # question's semantic identity is carried explicitly and is what the answer
    # binds to.
    adaptive_key = canonical_key_for_field(active_field) or canonical_key_for_field(
        str((active_question or {}).get("semantic_target") or "")
    )
    if (
        adaptive_key
        and alignment == "DIRECT_ANSWER"
        and canonical.status_of(adaptive_key) == "UNKNOWN"
    ):
        # A message that names a new symptom is the patient raising something
        # else, not an answer to what we asked. The question stays open; the
        # repeat limit stops it becoming a loop.
        turn_facts = extract_facts(
            query,
            severity_question_active=severity_question_active,
        )
        introduced_new_topic = any(
            fact.key.startswith("symptom.")
            and fact.key != adaptive_key
            for fact in turn_facts
        )
        # When a dedicated extractor already read this attribute, use its
        # normalised value rather than the whole sentence. "Bắt đầu từ sáng
        # nay, khoảng 6/10" answers an onset question with "sáng nay"; storing
        # the sentence would put the severity into the onset field and make the
        # confirmation summary read back something the patient never said.
        attribute = adaptive_key.split(".", 1)[-1]
        extracted = next(
            (
                fact
                for fact in turn_facts
                if fact.key in {adaptive_key, attribute}
            ),
            None,
        )
        if extracted is not None:
            answer = ExtractedFact(
                key=adaptive_key,
                value=extracted.value,
                status=extracted.status,
                source=extracted.source,
                temporal=extracted.temporal,
                temporal_label=extracted.temporal_label,
                raw_span=extracted.raw_span,
                confidence=extracted.confidence,
            )
        else:
            answer = extract_answer_for_target(
                query,
                adaptive_key,
                introduced_new_topic=introduced_new_topic,
            )
        if answer is not None:
            canonical.record(
                answer.key,
                answer.value,
                status=answer.status,
                source=answer.source,
                temporal=answer.temporal,
                temporal_label=answer.temporal_label,
                raw_span=answer.raw_span,
                turn_id=source_turn_id,
                note=answer.note or "answer_to_adaptive_question",
            )

    # Anything the legacy slot-filling extractor found that canonical did not
    # (structured-form answers, free-text complaints) is folded in, so canonical
    # is complete...
    ingest_blueprint(canonical, updated_blueprint, turn_id=source_turn_id)
    # ...and only then is the blueprint rebuilt *from* canonical. It is a
    # read-model, not a second source of truth: denied and historical-only
    # symptoms cannot survive the projection as positive complaints.
    updated_blueprint = project_blueprint(canonical, updated_blueprint)

    # Facts that only exist once canonical state has been projected -- free-text
    # vitals are the common case -- are recorded here too. ``pending_fact_updates``
    # is what the rest of the turn reads to answer "what did we just learn?", and
    # a record that says "nothing new" while the summary visibly gained a
    # temperature is worse than saying nothing at all.
    pending_fact_updates.extend(
        _projected_fact_records(
            current_blueprint,
            updated_blueprint,
            pending_fact_updates,
            source_turn_id,
        )
    )

    # Decided from the projected read-model, not from the legacy extractor
    # alone. Free-text vitals ("38.5 độ") are only canonical facts until the
    # projection runs, and reading the pre-projection dict here is what left
    # ``vital_signs_status`` at NOT_REVIEWED for a patient who had just told us
    # their temperature.
    if updated_blueprint.get("vital_signs"):
        vital_status = "PATIENT_REPORTED"

    summary_log = f"[Intake Analyzer] Đã cập nhật Blueprint. Confidence: {updated_blueprint.get('confidence_score', 0)}"

    # A clinically relevant mutation invalidates any conclusion already drawn.
    # Trivial changes (a name, a passing remark) do not appear here, so a turn
    # that changes nothing decisive does not force reassessment.
    requires_reassessment = bool(canonical.pending_reassessment_keys) and bool(
        state.get("current_esi_level") or state.get("sbar_report")
    )

    # Did this turn actually learn anything? The canonical version only moves
    # when an observation was recorded, so this distinguishes "the patient told
    # us something new" from "the patient replied but nothing was extractable".
    # The question planner uses it to stop asking instead of looping.
    information_gained = canonical.version > int(
        state.get("canonical_state_version") or 0
    )

    return {
        "canonical_state": canonical.to_dict(),
        "canonical_state_version": canonical.version,
        "information_gained_last_turn": information_gained,
        "pending_reassessment_keys": list(canonical.pending_reassessment_keys),
        "requires_triage_reassessment": requires_reassessment,
        # Parser divergence, surfaced rather than discarded. Never a patient
        # contradiction, so it does not trigger a clarification question.
        "extraction_disagreements": [
            item.to_dict() for item in canonical.extraction_disagreements
        ],
        "special_instructions": special_instructions,
        "clinical_blueprint": updated_blueprint,
        "clinical_fact_provenance": fact_provenance,
        "pending_fact_updates": pending_fact_updates,
        "unresolved_contradictions": remaining_contradictions,
        "clinical_context_update_pending": procedure_pending,
        "clinical_memory_confirmation_status": memory_status,
        "clinical_memory_update_pending": memory_update_pending,
        "confirmed_clinical_memory_updated_at": confirmed_memory_updated_at,
        "vital_signs_status": vital_status,
        "active_question": None,
        "structured_question": None,
        "workflow_phase": "INTAKE_EXTRACTION",
        "decision_status": "COLLECTING",
        "current_esi_level": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "analysis": state.get("analysis", "") + "\n" + summary_log
    }
