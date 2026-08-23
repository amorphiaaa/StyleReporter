"""Local filesystem workspace for questionnaire evidence and image references."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.domain.contracts import (
    AssetDownloader,
    AssetWorkspace,
    AssetWorkspaceResult,
    ClientRecord,
    QuestionnaireAsset,
    QuestionnaireSubmission,
)


class LocalAssetWorkspace(AssetWorkspace):
    """Create a durable, provider-neutral folder for each client submission."""

    def __init__(self, root: Path, downloader: AssetDownloader | None = None) -> None:
        self.root = root
        self.downloader = downloader

    async def register_submission(
        self,
        *,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        assets: Sequence[QuestionnaireAsset],
    ) -> AssetWorkspaceResult:
        (
            client_directory,
            submission_directory,
            manifest_path,
            manifest_assets,
        ) = await asyncio.to_thread(
            self._prepare_submission,
            client,
            submission,
            tuple(assets),
        )

        downloaded_count = 0
        if self.downloader is not None:
            for manifest_asset in manifest_assets:
                destination_stem = self.root / manifest_asset["planned_relative_path"]
                _remove_previous_downloads(destination_stem)
                result = await self.downloader.download(
                    source_url=manifest_asset["source_url"],
                    destination_stem=destination_stem,
                )
                manifest_asset.update(
                    {
                        "status": result.status,
                        "filename": result.filename,
                        "content_type": result.content_type,
                        "size_bytes": result.size_bytes,
                        "sha256": result.sha256,
                        "error": result.error,
                    }
                )
                if result.status == "downloaded" and result.filename:
                    manifest_asset["local_relative_path"] = (
                        destination_stem.parent / result.filename
                    ).relative_to(self.root).as_posix()
                    downloaded_count += 1

        await asyncio.to_thread(
            _write_json,
            manifest_path,
            {
                "manifest_version": 2,
                "client_id": submission.client_id,
                "submission_id": submission.id,
                "downloaded": bool(manifest_assets) and downloaded_count == len(manifest_assets),
                "downloaded_count": downloaded_count,
                "assets": manifest_assets,
            },
        )

        return AssetWorkspaceResult(
            client_directory=_relative_to_root(client_directory, self.root),
            submission_directory=_relative_to_root(submission_directory, self.root),
            manifest_relative_path=_relative_to_root(manifest_path, self.root),
            asset_count=len(assets),
            downloaded_count=downloaded_count,
        )

    async def get_verified_image_paths(
        self,
        *,
        client_id: str,
        submission_id: str,
    ) -> Sequence[str]:
        return await asyncio.to_thread(
            self._read_verified_image_paths,
            client_id,
            submission_id,
        )

    def _prepare_submission(
        self,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        assets: tuple[QuestionnaireAsset, ...],
    ) -> tuple[Path, Path, Path, list[dict[str, Any]]]:
        client_directory = self.root / "clients" / _safe_segment(client.id)
        submission_directory = client_directory / "submissions" / _safe_segment(submission.id)
        submission_directory.mkdir(parents=True, exist_ok=True)

        _write_json(
            client_directory / "client.json",
            {
                "client_id": client.id,
                "email_normalized": client.email_normalized,
                "display_name": client.display_name,
            },
        )
        _write_json(
            submission_directory / "questionnaire.json",
            {
                "client_id": submission.client_id,
                "submission_id": submission.id,
                "source": {
                    "type": submission.source_type,
                    "spreadsheet_id": submission.source_spreadsheet_id,
                    "sheet_name": submission.source_sheet_name,
                    "row_number": submission.source_row_number,
                    "row_hash": submission.source_row_hash,
                },
                "questionnaire_version": submission.questionnaire_version,
                "submitted_at": submission.submitted_at.isoformat()
                if submission.submitted_at
                else None,
                "raw_payload": dict(submission.raw_payload),
            },
        )

        manifest_assets: list[dict[str, Any]] = []
        for asset in assets:
            role = _safe_segment(asset.field_key)
            image_directory = submission_directory / "images" / role
            image_directory.mkdir(parents=True, exist_ok=True)
            planned_path = image_directory / f"{asset.ordinal:02d}"
            manifest_assets.append(
                {
                    "field_key": asset.field_key,
                    "ordinal": asset.ordinal,
                    "source_url": asset.source_url,
                    "status": "reference_only" if self.downloader is None else "pending",
                    "planned_relative_path": _relative_to_root(planned_path, self.root),
                }
            )

        manifest_path = submission_directory / "manifest.json"
        _write_json(
            manifest_path,
            {
                "manifest_version": 2,
                "client_id": submission.client_id,
                "submission_id": submission.id,
                "downloaded": False,
                "downloaded_count": 0,
                "assets": manifest_assets,
            },
        )
        return client_directory, submission_directory, manifest_path, manifest_assets

    def _read_verified_image_paths(self, client_id: str, submission_id: str) -> list[str]:
        submission_directory = (
            self.root
            / "clients"
            / _safe_segment(client_id)
            / "submissions"
            / _safe_segment(submission_id)
        )
        manifest_path = submission_directory / "manifest.json"
        if not manifest_path.is_file():
            return []

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict) or not isinstance(payload.get("assets"), list):
            return []

        verified: list[str] = []
        for asset in payload["assets"]:
            if not isinstance(asset, dict) or asset.get("status") != "downloaded":
                continue
            local_relative_path = asset.get("local_relative_path")
            if not isinstance(local_relative_path, str):
                continue
            candidate = (self.root / local_relative_path).resolve()
            try:
                candidate.relative_to(self.root.resolve())
            except ValueError:
                continue
            if candidate.is_file() and candidate.stat().st_size > 0:
                verified.append(candidate.relative_to(self.root.resolve()).as_posix())
        return verified


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _relative_to_root(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _remove_previous_downloads(destination_stem: Path) -> None:
    for candidate in destination_stem.parent.glob(f"{destination_stem.name}.*"):
        if candidate.is_file() and candidate.suffix.lower() in {
            ".gif",
            ".heic",
            ".jpg",
            ".png",
            ".webp",
        }:
            candidate.unlink()


def _safe_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return segment[:100] or "unknown"
