"""Read verified local questionnaire images for the client profile API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FOLDER_LABELS: dict[str, str] = {
    "questionnaire": "Questionnaire",
    "good_outfits": "Good Outfits",
    "bad_outfits": "Bad Outfits",
    "inspiration": "Inspiration",
    "final_report": "Final Report",
}
FOLDER_ORDER = tuple(FOLDER_LABELS)


@dataclass(frozen=True)
class LocalClientAsset:
    submission_id: str
    field_key: str
    ordinal: int
    folder_key: str
    folder_label: str
    filename: str
    content_type: str
    path: Path


def list_downloaded_assets(root: Path, client_id: str) -> list[LocalClientAsset]:
    """Return only downloaded files that remain inside the configured asset root."""

    client_directory = root / "clients" / client_id
    if not client_directory.is_dir():
        return []

    assets: list[LocalClientAsset] = []
    for manifest_path in sorted(client_directory.glob("submissions/*/manifest.json")):
        payload = _read_manifest(manifest_path)
        submission_id = payload.get("submission_id")
        manifest_assets = payload.get("assets")
        if not isinstance(submission_id, str) or not isinstance(manifest_assets, list):
            continue

        for manifest_asset in manifest_assets:
            asset = _to_local_asset(root, submission_id, manifest_asset)
            if asset is not None:
                assets.append(asset)

    return sorted(
        assets,
        key=lambda asset: (
            _folder_sort_key(asset.folder_key),
            asset.submission_id,
            asset.field_key,
            asset.ordinal,
        ),
    )


def find_downloaded_asset(
    root: Path,
    *,
    client_id: str,
    submission_id: str,
    field_key: str,
    ordinal: int,
) -> LocalClientAsset | None:
    """Find one downloaded asset using manifest metadata, never a user-built path."""

    return next(
        (
            asset
            for asset in list_downloaded_assets(root, client_id)
            if asset.submission_id == submission_id
            and asset.field_key == field_key
            and asset.ordinal == ordinal
        ),
        None,
    )


def _to_local_asset(
    root: Path,
    submission_id: str,
    manifest_asset: Any,
) -> LocalClientAsset | None:
    if not isinstance(manifest_asset, dict):
        return None
    if manifest_asset.get("status") != "downloaded":
        return None

    field_key = manifest_asset.get("field_key")
    ordinal = manifest_asset.get("ordinal")
    local_relative_path = manifest_asset.get("local_relative_path")
    if not isinstance(field_key, str) or not isinstance(ordinal, int):
        return None
    if not isinstance(local_relative_path, str):
        return None

    candidate = (root / local_relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or candidate.stat().st_size <= 0:
        return None

    folder_key = manifest_asset.get("drive_folder")
    if not isinstance(folder_key, str) or folder_key not in FOLDER_LABELS:
        folder_key = "questionnaire"
    filename = manifest_asset.get("filename")
    if not isinstance(filename, str) or not filename:
        filename = candidate.name
    content_type = manifest_asset.get("content_type")
    if not isinstance(content_type, str) or not content_type:
        content_type = "application/octet-stream"

    return LocalClientAsset(
        submission_id=submission_id,
        field_key=field_key,
        ordinal=ordinal,
        folder_key=folder_key,
        folder_label=FOLDER_LABELS[folder_key],
        filename=filename,
        content_type=content_type,
        path=candidate,
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _folder_sort_key(folder_key: str) -> int:
    try:
        return FOLDER_ORDER.index(folder_key)
    except ValueError:
        return len(FOLDER_ORDER)
