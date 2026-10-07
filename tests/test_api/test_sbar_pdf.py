import io
from datetime import datetime

import pdfplumber

from src.services.sbar_pdf import SbarPdfData, build_sbar_pdf, register_pdf_fonts


def _sample_pdf_data() -> SbarPdfData:
    return SbarPdfData(
        session_id="49c27c80-dbfd-45ee-a619-551cc4831ea6",
        patient_name="Phạm Tuấn Việt",
        age=30,
        gender="Nam",
        relationship_type="Bản thân",
        created_at=datetime(2026, 8, 13, 6, 56, 33),
        chief_complaint="Đau đầu, tiêu chảy, đau đầu liên miên",
        esi_level=2,
        review_status="APPROVED",
        reviewer_name="BS. Nguyễn Minh Anh",
        reviewed_at=datetime(2026, 8, 13, 7, 15),
        situation="Bệnh nhân khai đau đầu kéo dài từ hôm qua.",
        background="Chưa ghi nhận bệnh nền, dị ứng hoặc thuốc dùng hằng ngày.",
        assessment="Đánh giá mức độ khẩn cấp ESI 2.",
        recommendation="Đến cơ sở cấp cứu gần nhất để được đánh giá trực tiếp.",
        citations=("mietic_06356", "mietic_06355", "mietic_04869"),
    )


def test_sbar_pdf_embeds_unicode_fonts() -> None:
    regular_font, bold_font = register_pdf_fonts()
    pdf_bytes = build_sbar_pdf(_sample_pdf_data())

    assert regular_font == "SbarUnicode"
    assert bold_font == "SbarUnicode-Bold"
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"/ToUnicode" in pdf_bytes
    assert any(
        font_name in pdf_bytes
        for font_name in (b"DejaVuSans", b"NotoSans", b"FreeSans", b"Arial")
    )


def test_sbar_pdf_escapes_reportlab_markup_from_database_text() -> None:
    data = _sample_pdf_data()
    unsafe_data = SbarPdfData(
        **{
            **data.__dict__,
            "situation": "Đau đầu <script>alert('x')</script> & chóng mặt",
        }
    )

    pdf_bytes = build_sbar_pdf(unsafe_data)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 10_000


def test_sbar_pdf_records_ai_proposal_and_persisted_nurse_adjustment() -> None:
    data = SbarPdfData(
        **{
            **_sample_pdf_data().__dict__,
            "esi_level": 2,
            "review_status": "OVERRIDDEN",
            "ai_proposed_esi": 4,
            "final_esi": 2,
            "decision_type": "ADJUST_ESI",
            "decision_reason_code": "ADDITIONAL_CLINICAL_JUDGMENT",
            "decision_note": "Đau tăng nhanh, cần được đánh giá ưu tiên.",
        }
    )

    with pdfplumber.open(io.BytesIO(build_sbar_pdf(data))) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "THẨM ĐỊNH ĐIỀU DƯỠNG" in text
    assert "ESI 4 — Ít khẩn" in text
    assert "ESI 2 — Nguy kịch" in text
    assert "Chuyển đổi ESI" in text
    assert "ESI 4 — Ít khẩn → ESI 2 — Nguy kịch" in text
    assert "Điều dưỡng điều chỉnh mức ưu tiên" in text
    assert "Đau tăng nhanh, cần được đánh giá ưu tiên." in text
