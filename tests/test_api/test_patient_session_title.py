from src.api.routes_patient import _session_title, _session_title_from_agent_result


def test_session_title_is_trimmed_and_bounded():
    assert _session_title("  Đau ngực  ") == "Đau ngực"
    assert _session_title("a" * 46) == f"{'a' * 45}..."


def test_session_title_uses_extracted_chief_complaint():
    result = {
        "clinical_blueprint": {
            "chief_complaint": ["Đau ngực", "khó thở"],
        },
    }

    assert _session_title_from_agent_result(result) == "Đau ngực, khó thở"


def test_session_title_does_not_use_ai_assessment_as_complaint():
    result = {
        "sbar_report": {"assessment": "AI đề xuất ESI 2"},
        "current_esi_level": 2,
    }

    assert _session_title_from_agent_result(result) == ""
