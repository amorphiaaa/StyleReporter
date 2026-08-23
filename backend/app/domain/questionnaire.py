from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.questionnaire_definitions import (
    QuestionnaireFieldDefinition,
    get_questionnaire_definition,
)

QUESTIONNAIRE_FIXTURE_VERSION = "fixture-v1"


QuestionnaireField = QuestionnaireFieldDefinition


@dataclass(frozen=True)
class NormalizedQuestionnaire:
    """Typed questionnaire context derived from raw source answers.

    The importer keeps the original row as raw JSONB. This object is a stable
    contract for later report and agent work, so adding a new source column does
    not require changing the persistence model immediately.
    """

    version: str | None
    email: str | None
    display_name: str | None
    current_style: str | None
    style_goal: str | None
    style_self_perception: str | None
    style_discomfort: str | None
    feels_like_me_images: tuple[str, ...]
    not_me_image: str | None
    inspiration_images: tuple[str, ...]
    visual_world: str | None
    missing_report_fields: tuple[str, ...]
    answers: Mapping[str, str | tuple[str, ...] | None]


QUESTIONNAIRE_FIELDS = get_questionnaire_definition(QUESTIONNAIRE_FIXTURE_VERSION).fields


def normalize_questionnaire_payload(
    raw_payload: Mapping[str, object],
    *,
    version: str | None,
    email_header: str = "Email",
    display_name_header: str | None = "Name",
) -> NormalizedQuestionnaire:
    """Map a versioned source row into the stable questionnaire contract.

    Unknown or missing versions intentionally use only the generic identity
    fields. The raw payload remains importable while a future version mapping
    can be introduced without a database migration.
    """

    definition = get_questionnaire_definition(version)
    identity_email_headers = _preferred_headers(
        email_header,
        definition.email_headers if definition else (),
    )
    identity_display_name_headers = _preferred_headers(
        display_name_header,
        definition.display_name_headers if definition else (),
    )
    email = _first_text(raw_payload, identity_email_headers)
    display_name = _first_text(raw_payload, identity_display_name_headers)

    if definition is None:
        return NormalizedQuestionnaire(
            version=version,
            email=email,
            display_name=display_name,
            current_style=None,
            style_goal=None,
            style_self_perception=None,
            style_discomfort=None,
            feels_like_me_images=(),
            not_me_image=None,
            inspiration_images=(),
            visual_world=None,
            missing_report_fields=(),
            answers={},
        )

    values = {
        field.key: _field_value(raw_payload, field)
        for field in definition.fields
    }
    missing_report_fields = tuple(
        field.key
        for field in definition.fields
        if field.report_required and not values[field.key]
    )

    return NormalizedQuestionnaire(
        version=version,
        email=email,
        display_name=display_name,
        current_style=_as_text_value(values.get("current_style")),
        style_goal=_as_text_value(values.get("style_goal")),
        style_self_perception=_as_text_value(values.get("style_self_perception")),
        style_discomfort=_as_text_value(values.get("style_discomfort")),
        feels_like_me_images=_as_image_values(values.get("feels_like_me_images")),
        not_me_image=_as_text_value(values.get("not_me_image")),
        inspiration_images=_as_image_values(values.get("inspiration_images")),
        visual_world=_as_text_value(values.get("visual_world")),
        missing_report_fields=missing_report_fields,
        answers=values,
    )


def _field_value(
    raw_payload: Mapping[str, object], field: QuestionnaireField
) -> str | tuple[str, ...] | None:
    for header in field.headers:
        value = _text(raw_payload.get(header))
        if value is None:
            continue
        if field.multiple:
            return tuple(
                part.strip()
                for part in value.replace("\n", ",").split(",")
                if part.strip()
            )
        return value
    return None


def _as_text_value(value: str | tuple[str, ...] | None) -> str | None:
    return value if isinstance(value, str) else None


def _as_image_values(value: str | tuple[str, ...] | None) -> tuple[str, ...]:
    return value if isinstance(value, tuple) else ()


def _preferred_headers(primary: str | None, aliases: tuple[str, ...]) -> tuple[str, ...]:
    headers = [primary] if primary else []
    headers.extend(alias for alias in aliases if alias not in headers)
    return tuple(headers)


def _first_text(raw_payload: Mapping[str, object], headers: tuple[str, ...]) -> str | None:
    for header in headers:
        value = _text(raw_payload.get(header))
        if value is not None:
            return value
    return None


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
