"""Generate the canonical, Unicode-safe SBAR handoff PDF."""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT_REGULAR = "SbarUnicode"
FONT_BOLD = "SbarUnicode-Bold"

NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#075985")
SLATE_50 = colors.HexColor("#F8FAFC")
SLATE_100 = colors.HexColor("#F1F5F9")
SLATE_200 = colors.HexColor("#E2E8F0")
SLATE_500 = colors.HexColor("#64748B")
SLATE_700 = colors.HexColor("#334155")
ROSE = colors.HexColor("#BE123C")
AMBER = colors.HexColor("#B45309")
EMERALD = colors.HexColor("#047857")

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


@dataclass(frozen=True)
class SbarPdfData:
    """Persisted fields required to produce a deterministic SBAR PDF.

    ``esi_level`` remains the result that is prominent in the status box for
    backwards compatibility.  The optional review fields retain the two
    distinct clinical facts needed for a transparent HITL record: what AI
    proposed and what the nurse ultimately decided.  The PDF never derives a
    decision from either value.
    """

    session_id: str
    patient_name: str
    age: int | None
    gender: str | None
    relationship_type: str | None
    created_at: datetime
    chief_complaint: str
    esi_level: int | None
    review_status: str
    reviewer_name: str | None
    reviewed_at: datetime | None
    situation: str
    background: str
    assessment: str
    recommendation: str
    citations: tuple[str, ...]
    ai_proposed_esi: int | None = None
    final_esi: int | None = None
    decision_type: str | None = None
    decision_reason_code: str | None = None
    decision_note: str | None = None


def _font_candidates() -> tuple[tuple[Path, Path], ...]:
    configured_regular = os.getenv("SBAR_PDF_FONT_REGULAR")
    configured_bold = os.getenv("SBAR_PDF_FONT_BOLD")
    windows_fonts = Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts"
    configured = (
        ((Path(configured_regular), Path(configured_bold)),)
        if configured_regular and configured_bold
        else ()
    )
    return configured + (
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
            Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
        ),
        (
            windows_fonts / "arial.ttf",
            windows_fonts / "arialbd.ttf",
        ),
    )


@lru_cache(maxsize=1)
def register_pdf_fonts() -> tuple[str, str]:
    """Register a font pair with Vietnamese glyph coverage exactly once."""

    for regular_path, bold_path in _font_candidates():
        if regular_path.is_file() and bold_path.is_file():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
            return FONT_REGULAR, FONT_BOLD
    raise RuntimeError(
        "Không tìm thấy font Unicode dùng để tạo PDF SBAR. "
        "Hãy cài fonts-dejavu-core/Arial hoặc cấu hình "
        "SBAR_PDF_FONT_REGULAR/SBAR_PDF_FONT_BOLD."
    )


def _markup(value: object, fallback: str = "Chưa ghi nhận") -> str:
    text = CONTROL_CHARACTERS.sub("", str(value or "").strip()) or fallback
    return escape(text).replace("\n", "<br/>")


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Chưa ghi nhận"
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    local_value = normalized.astimezone(ZoneInfo("Asia/Bangkok"))
    return local_value.strftime("%H:%M, ngày %d/%m/%Y")


def _esi_presentation(level: int | None) -> tuple[str, colors.Color]:
    labels = {
        1: "ESI 1 — Hồi sức",
        2: "ESI 2 — Nguy kịch",
        3: "ESI 3 — Khẩn cấp",
        4: "ESI 4 — Ít khẩn",
        5: "ESI 5 — Không khẩn",
    }
    color = ROSE if level in {1, 2} else AMBER if level == 3 else EMERALD
    return labels.get(level, "Chưa có kết luận ESI"), color


def _review_label(status: str) -> str:
    return {
        "APPROVED": "Đã thẩm định",
        "OVERRIDDEN": "Đã điều chỉnh và thẩm định",
        "PENDING_REVIEW": "Đang chờ thẩm định",
        "EMERGENCY_REJECTED": "Đã chuyển xử trí khẩn cấp",
    }.get(status, "Chưa xác định")


def _valid_esi(value: int | None) -> int | None:
    return value if value in {1, 2, 3, 4, 5} else None


def _decision_label(decision_type: str | None, review_status: str) -> str:
    if decision_type == "CONFIRM_ESI":
        return "Điều dưỡng xác nhận đề xuất AI"
    if decision_type == "ADJUST_ESI":
        return "Điều dưỡng điều chỉnh mức ưu tiên"
    if review_status == "APPROVED":
        return "Điều dưỡng đã xác nhận kết quả"
    if review_status == "OVERRIDDEN":
        return "Điều dưỡng đã điều chỉnh mức ưu tiên"
    return "Chưa có quyết định cuối cùng của điều dưỡng"


def _reason_label(reason_code: str | None) -> str | None:
    """Render persisted nurse reason codes in patient-readable Vietnamese.

    The same canonical PDF is shared by the production and Simple Agent
    workflows, so this covers their currently allowed codes and falls back to
    the stored code for future values rather than inventing a meaning.
    """

    labels = {
        "AI_EVIDENCE_MATCH": "Dữ liệu phù hợp với căn cứ ESI",
        "CLINICAL_FINDING_CHANGED": "Có ghi nhận lâm sàng mới",
        "RISK_FACTOR": "Có yếu tố nguy cơ liên quan",
        "DATA_CORRECTION": "Có điều chỉnh dữ liệu đầu vào",
        "MATCHES_PROTOCOL": "Thông tin phù hợp với phác đồ",
        "ADDITIONAL_CLINICAL_JUDGMENT": "Có cân nhắc lâm sàng bổ sung",
        "INSUFFICIENT_PATIENT_DATA": "Dữ liệu người bệnh chưa đầy đủ",
        "OTHER": "Lý do khác",
    }
    if not reason_code:
        return None
    return labels.get(reason_code, reason_code.replace("_", " ").capitalize())


def _draw_page_chrome(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setTitle("Phiếu bàn giao lâm sàng SBAR")
    canvas.setAuthor("AI Triage")
    canvas.setSubject("SBAR clinical handoff record")

    page_width, _ = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 7 * mm, page_width, 7 * mm, stroke=0, fill=1)

    canvas.setStrokeColor(SLATE_200)
    canvas.setLineWidth(0.6)
    canvas.line(doc.leftMargin, 15 * mm, page_width - doc.rightMargin, 15 * mm)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(doc.leftMargin, 10 * mm, "TÀI LIỆU Y KHOA BẢO MẬT — CHỈ DÙNG CHO BÀN GIAO LÂM SÀNG")
    canvas.drawRightString(
        page_width - doc.rightMargin,
        10 * mm,
        f"Trang {doc.page}",
    )
    canvas.restoreState()


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "eyebrow": ParagraphStyle(
            "SbarEyebrow",
            fontName=FONT_BOLD,
            fontSize=8.5,
            leading=11,
            textColor=BLUE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "SbarTitle",
            fontName=FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SbarSubtitle",
            fontName=FONT_REGULAR,
            fontSize=9,
            leading=13,
            textColor=SLATE_700,
            alignment=TA_CENTER,
        ),
        "label": ParagraphStyle(
            "SbarLabel",
            fontName=FONT_BOLD,
            fontSize=8,
            leading=11,
            textColor=SLATE_500,
        ),
        "value": ParagraphStyle(
            "SbarValue",
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=13,
            textColor=NAVY,
        ),
        "body": ParagraphStyle(
            "SbarBody",
            fontName=FONT_REGULAR,
            fontSize=9.5,
            leading=14,
            textColor=NAVY,
            alignment=TA_LEFT,
        ),
        "body_bold": ParagraphStyle(
            "SbarBodyBold",
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=14,
            textColor=NAVY,
            alignment=TA_LEFT,
        ),
        "section": ParagraphStyle(
            "SbarSection",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=NAVY,
        ),
        "small": ParagraphStyle(
            "SbarSmall",
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=12,
            textColor=SLATE_700,
        ),
        "small_right": ParagraphStyle(
            "SbarSmallRight",
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=12,
            textColor=SLATE_700,
            alignment=TA_RIGHT,
        ),
    }


def _metadata_table(data: SbarPdfData, styles: dict[str, ParagraphStyle]) -> Table:
    patient_details = " • ".join(
        part
        for part in (
            f"{data.age} tuổi" if data.age is not None else None,
            data.gender,
            data.relationship_type,
        )
        if part
    ) or "Chưa ghi nhận"
    rows = [
        [
            Paragraph("NGƯỜI BỆNH", styles["label"]),
            Paragraph("MÃ PHIẾU", styles["label"]),
        ],
        [
            Paragraph(_markup(data.patient_name), styles["value"]),
            Paragraph(_markup(data.session_id[-8:]).upper(), styles["value"]),
        ],
        [
            Paragraph(_markup(patient_details), styles["small"]),
            Paragraph(_markup(_format_datetime(data.created_at)), styles["small"]),
        ],
    ]
    table = Table(rows, colWidths=[112 * mm, 61 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                ("BOX", (0, 0), (-1, -1), 0.8, SLATE_200),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_200),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _status_table(data: SbarPdfData, styles: dict[str, ParagraphStyle]) -> Table:
    displayed_esi = (
        _valid_esi(data.final_esi)
        if data.review_status in {"APPROVED", "OVERRIDDEN"} and _valid_esi(data.final_esi) is not None
        else _valid_esi(data.esi_level)
    )
    esi_label, esi_color = _esi_presentation(displayed_esi)
    reviewer = data.reviewer_name or "Chưa ghi nhận người thẩm định"
    review_details = f"{_review_label(data.review_status)}<br/><font size='8'>{_markup(reviewer)}</font>"
    if data.reviewed_at:
        review_details += f"<br/><font size='8'>{_markup(_format_datetime(data.reviewed_at))}</font>"

    esi_style = ParagraphStyle(
        "SbarEsi",
        parent=styles["value"],
        fontSize=15,
        leading=19,
        textColor=esi_color,
    )
    review_style = ParagraphStyle(
        "SbarReview",
        parent=styles["value"],
        fontSize=9,
        leading=13,
        alignment=TA_RIGHT,
    )
    table = Table(
        [
            [
                Paragraph("MỨC ĐỘ ƯU TIÊN", styles["label"]),
                Paragraph("TRẠNG THÁI HỒ SƠ", styles["label"]),
            ],
            [
                Paragraph(_markup(esi_label), esi_style),
                Paragraph(review_details, review_style),
            ],
        ],
        colWidths=[86.5 * mm, 86.5 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                ("BOX", (0, 0), (-1, -1), 0.9, NAVY),
                ("LINEBEFORE", (1, 0), (1, -1), 0.6, SLATE_200),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _nurse_review_table(data: SbarPdfData, styles: dict[str, ParagraphStyle]) -> Table:
    """Show the persisted nurse decision without replacing the AI proposal.

    A nurse note is free text supplied by a clinician, so it is escaped by
    ``_markup`` exactly like all other persisted PDF content.
    """

    ai_esi = _valid_esi(data.ai_proposed_esi)
    final_esi = _valid_esi(data.final_esi)
    if data.review_status in {"APPROVED", "OVERRIDDEN"} and final_esi is not None:
        final_text = _esi_presentation(final_esi)[0]
    else:
        final_text = "Chưa có quyết định cuối cùng của điều dưỡng"

    ai_text = _esi_presentation(ai_esi)[0] if ai_esi is not None else "Chưa có đề xuất ESI từ AI"
    note = data.decision_note.strip() if data.decision_note and data.decision_note.strip() else "Không có ghi chú bổ sung."
    reason = _reason_label(data.decision_reason_code)
    rows: list[list[Paragraph]] = [
        [Paragraph("THẨM ĐỊNH ĐIỀU DƯỠNG", styles["label"]), Paragraph("", styles["label"])],
        [Paragraph("Đề xuất AI", styles["small"]), Paragraph(_markup(ai_text), styles["value"])],
        [Paragraph("Quyết định điều dưỡng", styles["small"]), Paragraph(_markup(final_text), styles["value"])],
        [
            Paragraph("Hình thức quyết định", styles["small"]),
            Paragraph(_markup(_decision_label(data.decision_type, data.review_status)), styles["small"]),
        ],
    ]
    if data.review_status in {"APPROVED", "OVERRIDDEN"} and ai_esi is not None and final_esi is not None:
        rows.append(
            [
                Paragraph("Chuyển đổi ESI", styles["small"]),
                Paragraph(_markup(f"{ai_text} → {final_text}"), styles["value"]),
            ]
        )
    if reason:
        rows.append([Paragraph("Lý do đã chọn", styles["small"]), Paragraph(_markup(reason), styles["small"])])
    rows.append([Paragraph("Ghi chú điều dưỡng", styles["small"]), Paragraph(_markup(note), styles["small"])])

    table = Table(rows, colWidths=[48 * mm, 125 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), SLATE_100),
                ("BACKGROUND", (0, 1), (0, -1), SLATE_50),
                ("BOX", (0, 0), (-1, -1), 0.8, SLATE_200),
                ("INNERGRID", (0, 1), (-1, -1), 0.5, SLATE_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _sbar_section(
    code: str,
    title: str,
    content: str,
    styles: dict[str, ParagraphStyle],
    *,
    emphasize: bool = False,
) -> KeepTogether:
    heading = Table(
        [[Paragraph(f"{code} — {title}", styles["section"])]],
        colWidths=[173 * mm],
        hAlign="LEFT",
    )
    heading.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SLATE_100),
                ("LINEBEFORE", (0, 0), (0, -1), 3, BLUE if not emphasize else NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    body_style = styles["body_bold"] if emphasize else styles["body"]
    return KeepTogether(
        [
            heading,
            Spacer(1, 4),
            Paragraph(_markup(content), body_style),
            Spacer(1, 10),
        ]
    )


def build_sbar_pdf(data: SbarPdfData) -> bytes:
    """Build the single canonical A4 PDF used by all SBAR download actions."""

    register_pdf_fonts()
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=21 * mm,
        title="Phiếu bàn giao lâm sàng SBAR",
        author="AI Triage",
        subject="SBAR clinical handoff record",
    )

    story = [
        Paragraph("AI TRIAGE • HỒ SƠ BÀN GIAO", styles["eyebrow"]),
        Paragraph("PHIẾU BÀN GIAO LÂM SÀNG SBAR", styles["title"]),
        Paragraph(
            "Tóm tắt phục vụ tiếp nhận và trao đổi giữa người bệnh với nhân viên y tế",
            styles["subtitle"],
        ),
        Spacer(1, 9),
        HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=12),
        _metadata_table(data, styles),
        Spacer(1, 11),
        _status_table(data, styles),
        Spacer(1, 11),
        _nurse_review_table(data, styles),
        Spacer(1, 11),
        Paragraph("TRIỆU CHỨNG CHÍNH", styles["label"]),
        Spacer(1, 3),
        Paragraph(_markup(data.chief_complaint), styles["body_bold"]),
        Spacer(1, 10),
        _sbar_section("S", "SITUATION / Tình trạng hiện tại", data.situation, styles),
        _sbar_section("B", "BACKGROUND / Tiền sử liên quan", data.background, styles),
        _sbar_section("A", "ASSESSMENT / Đánh giá", data.assessment, styles),
        _sbar_section(
            "R",
            "RECOMMENDATION / Khuyến nghị",
            data.recommendation,
            styles,
            emphasize=True,
        ),
    ]

    citations = ", ".join(dict.fromkeys(data.citations)) or "Chưa ghi nhận"
    story.extend(
        [
            HRFlowable(width="100%", thickness=0.7, color=SLATE_200, spaceBefore=2, spaceAfter=8),
            Table(
                [
                    [
                        Paragraph(
                            f"<b>NGUỒN THAM CHIẾU ĐÃ LƯU</b><br/>{_markup(citations)}",
                            styles["small"],
                        ),
                        Paragraph(
                            "<b>XÁC NHẬN TIẾP NHẬN</b><br/><br/>Ký và ghi rõ họ tên",
                            styles["small_right"],
                        ),
                    ]
                ],
                colWidths=[112 * mm, 61 * mm],
                hAlign="LEFT",
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 13),
            Paragraph(
                "Lưu ý: Phiếu SBAR hỗ trợ bàn giao thông tin và không thay thế chẩn đoán, "
                "khám trực tiếp hoặc quyết định chuyên môn của nhân viên y tế.",
                styles["small"],
            ),
        ]
    )

    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    return buffer.getvalue()
