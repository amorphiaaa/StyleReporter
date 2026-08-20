from collections.abc import Mapping
from dataclasses import dataclass

QUESTIONNAIRE_FIXTURE_VERSION = "fixture-v1"


@dataclass(frozen=True)
class QuestionnaireField:
    key: str
    headers: tuple[str, ...]
    report_required: bool = True
    multiple: bool = False


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


QUESTIONNAIRE_FIELDS = (
    QuestionnaireField(
        key="current_style",
        headers=("How would you describe your style today?",),
    ),
    QuestionnaireField(
        key="style_goal",
        headers=("What would you love your style to help you feel?",),
    ),
    QuestionnaireField(
        key="style_self_perception",
        headers=("Which sentence sounds MOST like you?",),
    ),
    QuestionnaireField(
        key="style_discomfort",
        headers=("What usually makes an outfit feel wrong to you?",),
    ),
    QuestionnaireField(
        key="feels_like_me_images",
        headers=("Feels Like Me images",),
        multiple=True,
    ),
    QuestionnaireField(
        key="not_me_image",
        headers=("Not Me image",),
    ),
    QuestionnaireField(
        key="inspiration_images",
        headers=("Inspiration images",),
        multiple=True,
    ),
    QuestionnaireField(
        key="visual_world",
        headers=("Visual world",),
    ),
)


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

    if version != QUESTIONNAIRE_FIXTURE_VERSION:
        return NormalizedQuestionnaire(
            version=version,
            email=_text(raw_payload.get(email_header)),
            display_name=(
                _text(raw_payload.get(display_name_header)) if display_name_header else None
            ),
            current_style=None,
            style_goal=None,
            style_self_perception=None,
            style_discomfort=None,
            feels_like_me_images=(),
            not_me_image=None,
            inspiration_images=(),
            visual_world=None,
            missing_report_fields=(),
        )

    values = {
        field.key: _field_value(raw_payload, field)
        for field in QUESTIONNAIRE_FIELDS
    }
    missing_report_fields = tuple(
        field.key
        for field in QUESTIONNAIRE_FIELDS
        if field.report_required and not values[field.key]
    )

    return NormalizedQuestionnaire(
        version=version,
        email=_text(raw_payload.get(email_header)),
        display_name=(
            _text(raw_payload.get(display_name_header)) if display_name_header else None
        ),
        current_style=_as_text_value(values["current_style"]),
        style_goal=_as_text_value(values["style_goal"]),
        style_self_perception=_as_text_value(values["style_self_perception"]),
        style_discomfort=_as_text_value(values["style_discomfort"]),
        feels_like_me_images=_as_image_values(values["feels_like_me_images"]),
        not_me_image=_as_text_value(values["not_me_image"]),
        inspiration_images=_as_image_values(values["inspiration_images"]),
        visual_world=_as_text_value(values["visual_world"]),
        missing_report_fields=missing_report_fields,
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


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
