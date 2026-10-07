"""Kiểm định chuẩn hóa số điện thoại Việt Nam cho endpoint PATCH /api/v1/auth/me/phone."""

import pytest
from pydantic import ValidationError

from src.models.auth_schemas import UpdatePhoneNumberRequestDTO, normalize_vietnam_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0912345678", "0912345678"),
        ("  0912345678  ", "0912345678"),
        ("0912 345 678", "0912345678"),
        ("0912-345-678", "0912345678"),
        ("+84912345678", "0912345678"),
        ("+84 912 345 678", "0912345678"),
        ("84912345678", "0912345678"),
        ("0243936141 4", "02439361414"),
        ("(024) 3936 1414", "02439361414"),
    ],
)
def test_valid_vietnam_numbers_normalize_to_one_stored_form(raw: str, expected: str) -> None:
    assert normalize_vietnam_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "091234567",  # thiếu một chữ số
        "09123456789",  # thừa một chữ số
        "0112345678",  # đầu số 01 không còn hiệu lực
        "0243936141",  # số cố định thiếu chữ số
        "0912345abc",
        "+1 415 555 0100",  # ngoài kho số Việt Nam
        "0912345678901234567890123456",  # vượt ngưỡng độ dài thô
    ],
)
def test_invalid_numbers_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_vietnam_phone(raw)


def test_blank_input_clears_the_stored_number() -> None:
    assert UpdatePhoneNumberRequestDTO(phoneNumber="   ").phoneNumber is None
    assert UpdatePhoneNumberRequestDTO(phoneNumber=None).phoneNumber is None
    assert UpdatePhoneNumberRequestDTO().phoneNumber is None


def test_dto_rejects_an_oversized_payload_before_normalisation() -> None:
    with pytest.raises(ValidationError):
        UpdatePhoneNumberRequestDTO(phoneNumber="0" * 200)


def test_dto_carries_no_user_identifier() -> None:
    """Danh tính phải đến từ Bearer Token, không bao giờ từ payload của client."""
    assert set(UpdatePhoneNumberRequestDTO.model_fields) == {"phoneNumber"}
