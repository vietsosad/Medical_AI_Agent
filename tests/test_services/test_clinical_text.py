from src.models.patient_schemas import SbarReportDTO
from src.services.clinical_text import normalize_clinical_display_text


def test_known_hitl_actions_are_separated_from_preceding_vietnamese_text() -> None:
    assert normalize_clinical_display_text("để quyết địnhAPPROVE hoặc chọnOVERRIDE") == (
        "để quyết định APPROVE hoặc chọn OVERRIDE"
    )


def test_sbar_dto_repairs_legacy_persisted_recommendation_spacing() -> None:
    report = SbarReportDTO(
        situation="Tình trạng",
        background="Bối cảnh",
        assessment="Nhận định",
        recommendation="để quyết địnhAPPROVE hoặc OVERRIDE cấp ESI",
    )

    assert report.recommendation == "để quyết định APPROVE hoặc OVERRIDE cấp ESI"
