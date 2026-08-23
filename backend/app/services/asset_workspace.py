"""Local filesystem workspace for questionnaire evidence and image references."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from app.domain.contracts import (
    AssetWorkspace,
    AssetWorkspaceResult,
    ClientRecord,
    QuestionnaireAsset,
    QuestionnaireSubmission,
)


class LocalAssetWorkspace(AssetWorkspace):
    """Create a durable, provider-neutral folder for each client submission.

    This first slice registers source URLs and creates the future image
    directories. It deliberately does not download provider files yet.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    async def register_submission(
        self,
        *,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        assets: tuple[QuestionnaireAsset, ...] | list[QuestionnaireAsset],
    ) -> AssetWorkspaceResult:
        return await asyncio.to_thread(
            self._register_submission,
            client,
            submission,
            tuple(assets),
        )

    def _register_submission(
        self,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        assets: tuple[QuestionnaireAsset, ...],
    ) -> AssetWorkspaceResult:
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
            manifest_assets.append(
                {
                    "field_key": asset.field_key,
                    "ordinal": asset.ordinal,
                    "source_url": asset.source_url,
                    "status": "reference_only",
                    "planned_relative_path": (
                        Path("images") / role / f"{asset.ordinal:02d}"
                    ).as_posix(),
                }
            )

        _write_json(
            submission_directory / "manifest.json",
            {
                "manifest_version": 1,
                "client_id": submission.client_id,
                "submission_id": submission.id,
                "downloaded": False,
                "assets": manifest_assets,
            },
        )

        return AssetWorkspaceResult(
            client_directory=_relative_to_root(client_directory, self.root),
            submission_directory=_relative_to_root(submission_directory, self.root),
            manifest_relative_path=_relative_to_root(
                submission_directory / "manifest.json",
                self.root,
            ),
            asset_count=len(assets),
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _safe_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return segment[:100] or "unknown"
