import json
import re
from datetime import datetime
from hashlib import sha256

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str | None) -> str | None:
    """Return a trimmed, case-folded email or None for blank/invalid input."""

    if not value:
        return None

    normalized = value.strip().casefold()
    if not normalized or not _EMAIL_PATTERN.fullmatch(normalized):
        return None
    return normalized


def normalize_display_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def parse_submission_timestamp(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None

    timestamp = value.strip()
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"

    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def hash_row(values: dict[str, str]) -> str:
    serialized = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()
