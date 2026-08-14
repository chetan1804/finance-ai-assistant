import math
import re
import unicodedata
from datetime import date
from numbers import Real


MAX_QUESTION_LENGTH = 2000
MAX_THREAD_ID_LENGTH = 128
MAX_MONEY_VALUE = 1_000_000_000_000_000
THREAD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def validate_positive_id(value, field_name="id") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def validate_text(
    value,
    field_name,
    *,
    max_length=255,
    required=True,
    allow_newlines=False,
):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    cleaned = value.strip()
    if required and not cleaned:
        raise ValueError(f"{field_name} is required.")
    if len(cleaned) > max_length:
        raise ValueError(
            f"{field_name} must be at most {max_length} characters."
        )

    for character in cleaned:
        if character in "\n\t" and allow_newlines:
            continue
        if unicodedata.category(character) == "Cc":
            raise ValueError(f"{field_name} contains unsupported characters.")
    return cleaned


def validate_money(value, field_name="amount", *, allow_none=False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a number.")

    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be a finite number greater than zero.")
    if numeric > MAX_MONEY_VALUE:
        raise ValueError(f"{field_name} exceeds the supported limit.")
    return numeric


def validate_finite_number(value, field_name, *, allow_none=False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a number.")

    numeric = float(value)
    if not math.isfinite(numeric) or abs(numeric) > MAX_MONEY_VALUE:
        raise ValueError(f"{field_name} must be a finite supported number.")
    return numeric


def validate_iso_date(value, field_name="date", *, allow_none=True):
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from error


def validate_date_range(start_date=None, end_date=None):
    start = validate_iso_date(start_date, "start_date")
    end = validate_iso_date(end_date, "end_date")
    if start and end and start > end:
        raise ValueError("start_date must not be after end_date.")
    return start, end


def validate_email(value) -> str:
    email = validate_text(value, "email", max_length=254)
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("email must be a valid email address.")
    return email.casefold()


def validate_currency(value) -> str:
    currency = validate_text(value, "currency", max_length=16).upper()
    if not CURRENCY_PATTERN.fullmatch(currency):
        raise ValueError("currency must be a three-letter ISO code.")
    return currency


def validate_chat_request(user_id, thread_id, question):
    user_id = validate_positive_id(user_id, "user_id")
    thread_id = validate_text(
        thread_id,
        "thread_id",
        max_length=MAX_THREAD_ID_LENGTH,
    )
    if not THREAD_ID_PATTERN.fullmatch(thread_id):
        raise ValueError(
            "thread_id may contain only letters, numbers, dot, underscore, "
            "colon, and hyphen."
        )
    question = validate_text(
        question,
        "question",
        max_length=MAX_QUESTION_LENGTH,
        allow_newlines=True,
    )
    return user_id, thread_id, question
