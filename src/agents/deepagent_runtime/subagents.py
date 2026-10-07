"""Specialist profiles available to the MedTriage DeepAgent supervisor."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool


def build_subagent_specs(tools: list[BaseTool]) -> list[dict[str, Any]]:
    by_name = {item.name: item for item in tools}
    return [
        {
            "name": "emergency-context-analyst",
            "description": (
                "Assesses combined, contextual signs of a time-critical emergency."
            ),
            "system_prompt": (
                "Call assess_contextual_emergency once before all other clinical "
                "tools. The tool owns the structured assessment and escalation; "
                "do not add a diagnosis, ESI, or advice in free text."
            ),
            "tools": [by_name["assess_contextual_emergency"]],
            "skills": ["/skills/medtriage-clinical-safety/"],
        },
        {
            "name": "intake-planner",
            "description": "Classifies the request and advances structured intake safely.",
            "system_prompt": (
                "Use classify_request only after contextual emergency assessment, "
                "then update_intake when allowed. Return the tool status; do not write "
                "patient-facing advice."
            ),
            "tools": [by_name["classify_request"], by_name["update_intake"]],
            "skills": ["/skills/medtriage-deepagent-router/"],
        },
        {
            "name": "evidence-analyst",
            "description": "Retrieves evidence and applies authority/provenance gates.",
            "system_prompt": (
                "Call retrieve_clinical_evidence once. Never reinterpret a case example "
                "as an approved protocol. Return only the tool status."
            ),
            "tools": [by_name["retrieve_clinical_evidence"]],
            "skills": ["/skills/medtriage-rag-evidence/"],
        },
        {
            "name": "clinical-reasoner",
            "description": "Requests evidence-bound ESI reasoning after authorization.",
            "system_prompt": (
                "Call reason_and_prepare_handoff only when retrieval authorizes it. "
                "Do not invent an ESI, diagnosis, criterion, or citation."
            ),
            "tools": [by_name["reason_and_prepare_handoff"]],
            "skills": ["/skills/medtriage-clinical-safety/"],
        },
        {
            "name": "sbar-writer",
            "description": "Coordinates the gated SBAR handoff step.",
            "system_prompt": (
                "Use only the handoff tool result. Never add clinical claims or citations "
                "in free text."
            ),
            "tools": [by_name["reason_and_prepare_handoff"]],
            "skills": ["/skills/medtriage-clinical-safety/"],
        },
        {
            "name": "citation-verifier",
            "description": "Runs the final evidence, confirmation, and output firewall.",
            "system_prompt": (
                "Call verify_clinical_output exactly once and return its status. "
                "A rejected proposal must remain fail-closed."
            ),
            "tools": [by_name["verify_clinical_output"]],
            "skills": ["/skills/medtriage-rag-evidence/"],
        },
    ]
