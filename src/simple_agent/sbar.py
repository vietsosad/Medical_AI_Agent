"""Pure-Python SBAR-shaped summary for a simple_agent session, for nurse review.

Mirrors ``src/agents/nodes/summary_creator.py``'s own design choice for the
production engine: SBAR here is deterministic string assembly over
already-computed state, never an LLM call, and never touches
``decision.py``/``agent.py`` -- it only re-presents facts those modules already
decided. Same 5-key shape as the production ``SbarReportDTO``
(``situation``/``background``/``assessment``/``recommendation``/``citations``)
so a nurse-facing UI can render it the same way, even though the two engines'
underlying clinical models are unrelated.

``citations`` here is every protocol atom *retrieved* during the
conversation (``session.seen_atom_ids``), not only the ones that ended up
fully supported -- callers must still label this "phác đồ đã tham chiếu
trong phiên", not "đã khớp", to avoid overclaiming (an atom can appear here
while ``status`` says it was never actually satisfied). What changed
(2026-08-28): each entry is no longer a bare atom-id string -- it now also
carries ``status`` (SATISFIED | CONTRADICTED | MISSING_INFO, the same
3-way read `tools.py`'s ``search_protocol_atoms`` tool already uses) and,
when SATISFIED, ``satisfied_requirements`` describing exactly which
patient-reported value met which condition (see ``decision.py``'s
``describe_satisfied_branch`` -- a read-only re-derivation, ``agent.py``'s
own RETURN_MATCH/RETURN_INCOMPLETE decision is completely untouched by this).

What changed again (2026-08-29): once the session actually has a match
(``matched_esi_levels`` non-empty), the full transparent list above turned
out to be more confusing than helpful to a patient/nurse reading it --
real feedback, a benign ESI 3/4 atom satisfied *alongside* a genuine ESI 2
finding read as if the case were simultaneously 3 levels at once, and a
still-unmatched/missing-info atom sitting right next to the real reason
for the outcome looked like part of the answer. So a MATCHED session's
citations are now narrowed to only the atom(s) whose own
``decision_effect.candidate_esi`` equals the single most severe (lowest
numbered) level in ``matched_esi_levels`` -- exactly the criteria that
actually produced the result shown to the patient, nothing else. This
narrowing only applies once there IS a match: an INCOMPLETE session
(``matched_esi_levels`` empty) still gets the full list, unchanged --
there is no "the criteria that produced the result" to narrow to, and a
reviewer looking at an incomplete case still needs to see what was tried
and what's missing.
"""

from __future__ import annotations

from typing import Any

from .corpus import Corpus
from .decision import atom_status, describe_satisfied_branch
from .session import Session

__all__ = ["build_simple_agent_sbar"]

_CITATION_STATUS_ORDER = {"SATISFIED": 0, "MISSING_INFO": 1, "CONTRADICTED": 2}


def _citation_entries(corpus: Corpus, session: Session, matched_esi_levels: list[int]) -> list[dict[str, Any]]:
    """One entry per atom ever retrieved this session (``seen_atom_ids``),
    each honestly labeled with whether it was ever actually satisfied --
    see this module's docstring. Satisfied atoms sort first (most relevant
    to why the case concluded the way it did), contradicted ones last.

    Once ``matched_esi_levels`` is non-empty, narrowed to only the
    SATISFIED atom(s) at the single most severe (lowest-numbered) matched
    level -- see this module's docstring for why. An INCOMPLETE session
    (``matched_esi_levels`` empty) keeps the full unnarrowed list.
    """
    top_level = min(matched_esi_levels) if matched_esi_levels else None
    entries: list[dict[str, Any]] = []
    for atom_id in session.seen_atom_ids:
        atom = corpus.atom_by_id.get(atom_id)
        if atom is None:
            continue
        contradicted, unmet = atom_status(atom, session.facts)
        status = "CONTRADICTED" if contradicted else ("MISSING_INFO" if unmet else "SATISFIED")
        if top_level is not None and (status != "SATISFIED" or atom.get("decision_effect", {}).get("candidate_esi") != top_level):
            continue
        entries.append(
            {
                "atom_id": atom_id,
                "decision_point": atom.get("decision_point"),
                "criteria_text": atom.get("retrieval", {}).get("text"),
                "status": status,
                "satisfied_requirements": (
                    describe_satisfied_branch(atom, session.facts, corpus) if status == "SATISFIED" else []
                ),
            }
        )
    entries.sort(key=lambda entry: _CITATION_STATUS_ORDER[entry["status"]])
    return entries


def _subject_phrase(session: Session) -> str:
    if session.subject_type == "OTHER_PERSON" and session.subject_label:
        return session.subject_label
    return "bản thân bệnh nhân"


def _concept_names(corpus: Corpus, concept_ids: list[str]) -> list[str]:
    return [corpus.concept_by_id[c]["canonical_name"] for c in concept_ids if c in corpus.concept_by_id]


def _fact_lines(corpus: Corpus, facts: dict[str, Any]) -> list[str]:
    lines = []
    for fact_id, value in facts.items():
        fact = corpus.fact_by_id.get(fact_id)
        name = fact["name"] if fact else fact_id
        lines.append(f"{name}: {value}")
    return lines


def build_simple_agent_sbar(
    *,
    corpus: Corpus,
    session: Session,
    initial_message: str,
    final_message: str,
    matched_esi_levels: list[int],
) -> dict[str, Any]:
    """Assemble a nurse-readable SBAR-shaped dict from an already-finished session.

    Called once, at review-detail read time (``routes_nurse_simple.py``), on a
    session whose ``SimpleAgentChatSession.status`` is already ``COMPLETED`` --
    this never runs mid-conversation and never influences what the patient sees.
    """
    subject = _subject_phrase(session)
    concept_names = _concept_names(corpus, session.concept_order or sorted(session.concepts))

    situation = (
        f"Triệu chứng của {subject}: {', '.join(concept_names) if concept_names else 'chưa xác định concept cụ thể'}. "
        f"Mô tả ban đầu của bệnh nhân: “{initial_message.strip()}”."
    )

    fact_lines = _fact_lines(corpus, session.facts)
    observation_lines = [
        f"{corpus.fact_by_id[fid]['name'] if fid in corpus.fact_by_id else fid}: {text}"
        for fid, text in session.qualitative_observations.items()
    ]
    unknown_names = [
        corpus.fact_by_id[fid]["name"] if fid in corpus.fact_by_id else fid for fid in sorted(session.unknown_facts)
    ]
    background_parts = []
    if fact_lines:
        background_parts.append("Thông tin đã ghi nhận: " + "; ".join(fact_lines) + ".")
    if observation_lines:
        background_parts.append("Quan sát định tính (chưa quy đổi số liệu): " + "; ".join(observation_lines) + ".")
    if unknown_names:
        background_parts.append("Bệnh nhân không xác định được: " + ", ".join(unknown_names) + ".")
    background = " ".join(background_parts) if background_parts else "Không có thêm dữ liệu nền được ghi nhận."

    if matched_esi_levels:
        levels = ", ".join(str(level) for level in matched_esi_levels)
        assessment = (
            f"AI đề xuất mức ESI: {levels} (dựa trên các phác đồ đã khớp đầy đủ với dữ liệu đã ghi nhận). "
            f"Kết luận gửi bệnh nhân: “{final_message.strip()}”."
        )
    else:
        assessment = (
            "AI không đủ dữ liệu để kết luận mức ESI cụ thể (RETURN_INCOMPLETE). "
            f"Kết luận gửi bệnh nhân: “{final_message.strip()}”."
        )

    recommendation = "Đề nghị điều dưỡng xác nhận hoặc điều chỉnh mức ESI trước khi đóng ca."

    return {
        "situation": situation,
        "background": background,
        "assessment": assessment,
        "recommendation": recommendation,
        "citations": _citation_entries(corpus, session, matched_esi_levels),
    }
