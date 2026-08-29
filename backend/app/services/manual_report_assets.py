"""Persistent image storage for user-created manual report groups."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def manual_report_image_directory(root: Path, client_id: str, submission_id: str) -> Path:
    return root / "clients" / _safe_segment(client_id) / "submissions" / _safe_segment(
        submission_id
    ) / "manual-images"


def find_manual_report_image(
    root: Path,
    *,
    client_id: str,
    submission_id: str,
    asset_key: str,
) -> Path | None:
    if not _is_safe_asset_key(asset_key):
        return None
    directory = manual_report_image_directory(root, client_id, submission_id)
    for candidate in directory.glob(f"{asset_key}.*"):
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _safe_segment(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not value or any(character not in allowed for character in value):
        raise ValueError("Unsafe path segment.")
    return value


def _is_safe_asset_key(value: str) -> bool:
    return value.startswith("manual-") and all(
        character in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    )
