"""Input validation utilities."""

import re
from decimal import Decimal, InvalidOperation


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip())) if email else False


def validate_positive_number(value, allow_zero: bool = False) -> bool:
    try:
        n = float(value)
        return n >= 0 if allow_zero else n > 0
    except (TypeError, ValueError):
        return False


def validate_non_negative_int(value) -> bool:
    try:
        n = int(value)
        return n >= 0
    except (TypeError, ValueError):
        return False


def validate_required_string(value: str, max_length: int = 255) -> bool:
    return bool(value and value.strip() and len(value.strip()) <= max_length)


def to_decimal(value, default=Decimal('0.00')) -> Decimal:
    """Safely convert a value to Decimal."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def sanitize_string(value: str) -> str:
    """Strip whitespace from string inputs."""
    return value.strip() if value else ''
