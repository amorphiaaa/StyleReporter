from typing import Any

from app.domain.contracts import StyleReportRequest
from app.domain.questionnaire import normalize_questionnaire_payload


def build_questionnaire_context(request: StyleReportRequest) -> dict[str, Any]:
    """Build the privacy-conscious, typed context passed to the methodologist."""

    normalized = normalize_questionnaire_payload(
        request.raw_payload,
        version=request.questionnaire_version,
    )
    return {
        "questionnaire_version": normalized.version,
        "normalized_answers": {
            "current_style": normalized.current_style,
            "style_goal": normalized.style_goal,
            "style_self_perception": normalized.style_self_perception,
            "style_discomfort": normalized.style_discomfort,
            "feels_like_me_images": list(normalized.feels_like_me_images),
            "not_me_image": normalized.not_me_image,
            "inspiration_images": list(normalized.inspiration_images),
            "visual_world": normalized.visual_world,
        },
        "missing_report_fields": list(normalized.missing_report_fields),
        "raw_answers": _source_evidence_without_identity(request.raw_payload),
    }


def _source_evidence_without_identity(raw_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in raw_payload.items()
        if key.strip().lower() not in {"email", "name", "timestamp"}
    }
