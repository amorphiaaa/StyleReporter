from collections.abc import Mapping
from typing import Any

from app.domain.contracts import StyleReportRequest
from app.domain.questionnaire import normalize_questionnaire_payload
from app.domain.questionnaire_definitions import identity_headers_for_version


def build_questionnaire_context(request: StyleReportRequest) -> dict[str, Any]:
    """Build the privacy-conscious, typed context passed to the methodologist."""

    normalized = normalize_questionnaire_payload(
        request.raw_payload,
        version=request.questionnaire_version,
    )
    normalized_answers: dict[str, object] = {
        "current_style": normalized.current_style,
        "style_goal": normalized.style_goal,
        "style_self_perception": normalized.style_self_perception,
        "style_discomfort": normalized.style_discomfort,
        "feels_like_me_images": list(normalized.feels_like_me_images),
        "not_me_image": normalized.not_me_image,
        "inspiration_images": list(normalized.inspiration_images),
        "visual_world": normalized.visual_world,
    }
    normalized_answers.update({
        key: _json_safe_value(value) for key, value in normalized.answers.items()
    })
    return {
        "questionnaire_version": normalized.version,
        "normalized_answers": normalized_answers,
        "missing_report_fields": list(normalized.missing_report_fields),
        "raw_answers": _source_evidence_without_identity(
            request.raw_payload,
            version=request.questionnaire_version,
        ),
    }


def _source_evidence_without_identity(
    raw_payload: Mapping[str, Any],
    *,
    version: str | None,
) -> dict[str, Any]:
    identity_headers = {
        header.strip().casefold()
        for header in identity_headers_for_version(version)
    }
    identity_headers.update({"email", "name", "timestamp"})
    return {
        key: value
        for key, value in raw_payload.items()
        if key.strip().casefold() not in identity_headers
    }


def _json_safe_value(value: object) -> object:
    if isinstance(value, tuple):
        return list(value)
    return value
