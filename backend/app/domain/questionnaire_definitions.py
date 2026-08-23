"""Load versioned questionnaire mappings from repository configuration files."""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

QUESTIONNAIRE_DEFINITIONS_DIR = Path(__file__).with_name("questionnaire_definitions")


@dataclass(frozen=True)
class QuestionnaireFieldDefinition:
    key: str
    headers: tuple[str, ...]
    report_required: bool = True
    multiple: bool = False
    value_type: str = "text"
    asset_folder: str | None = None
    asset_folder_by_ordinal: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class QuestionnaireDefinition:
    version: str
    email_headers: tuple[str, ...]
    display_name_headers: tuple[str, ...]
    fields: tuple[QuestionnaireFieldDefinition, ...]

    @property
    def identity_headers(self) -> tuple[str, ...]:
        return self.email_headers + self.display_name_headers


@lru_cache(maxsize=1)
def load_questionnaire_definitions() -> dict[str, QuestionnaireDefinition]:
    definitions: dict[str, QuestionnaireDefinition] = {}
    for path in sorted(QUESTIONNAIRE_DEFINITIONS_DIR.glob("*.json")):
        definition = _load_definition(path)
        if definition.version in definitions:
            raise ValueError(f"Duplicate questionnaire definition: {definition.version}")
        definitions[definition.version] = definition
    return definitions


def get_questionnaire_definition(version: str | None) -> QuestionnaireDefinition | None:
    if not version:
        return None
    return load_questionnaire_definitions().get(version)


def identity_headers_for_version(version: str | None) -> tuple[str, ...]:
    definition = get_questionnaire_definition(version)
    if definition is not None:
        return definition.identity_headers

    headers: list[str] = []
    for known_definition in load_questionnaire_definitions().values():
        for header in known_definition.identity_headers:
            if header not in headers:
                headers.append(header)
    return tuple(headers)


def _load_definition(path: Path) -> QuestionnaireDefinition:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Questionnaire definition must be an object: {path}")

    version = _required_text(payload, "version", path)
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ValueError(f"Questionnaire definition identity is invalid: {path}")

    fields_payload = payload.get("fields")
    if not isinstance(fields_payload, list):
        raise ValueError(f"Questionnaire definition fields are invalid: {path}")

    fields = tuple(_load_field(field, path) for field in fields_payload)
    field_keys = [field.key for field in fields]
    if len(field_keys) != len(set(field_keys)):
        raise ValueError(f"Questionnaire definition has duplicate field keys: {path}")

    return QuestionnaireDefinition(
        version=version,
        email_headers=_headers(identity.get("email"), "email", path),
        display_name_headers=_headers(identity.get("display_name"), "display_name", path),
        fields=fields,
    )


def _load_field(payload: Any, path: Path) -> QuestionnaireFieldDefinition:
    if not isinstance(payload, dict):
        raise ValueError(f"Questionnaire field is invalid: {path}")
    asset_folder = payload.get("asset_folder")
    if asset_folder is not None and (
        not isinstance(asset_folder, str) or not asset_folder.strip()
    ):
        raise ValueError(f"Questionnaire field asset_folder is invalid: {path}")

    raw_asset_folder_by_ordinal = payload.get("asset_folder_by_ordinal", {})
    if not isinstance(raw_asset_folder_by_ordinal, dict):
        raise ValueError(f"Questionnaire field asset_folder_by_ordinal is invalid: {path}")
    asset_folder_by_ordinal: dict[int, str] = {}
    for raw_ordinal, raw_folder in raw_asset_folder_by_ordinal.items():
        try:
            ordinal = int(raw_ordinal)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Questionnaire field asset ordinal is invalid: {path}"
            ) from exc
        if ordinal < 1 or not isinstance(raw_folder, str) or not raw_folder.strip():
            raise ValueError(f"Questionnaire field asset folder mapping is invalid: {path}")
        asset_folder_by_ordinal[ordinal] = raw_folder.strip()

    return QuestionnaireFieldDefinition(
        key=_required_text(payload, "key", path),
        headers=_headers(payload.get("headers"), "headers", path),
        report_required=bool(payload.get("report_required", True)),
        multiple=bool(payload.get("multiple", False)),
        value_type=str(payload.get("value_type", "text")),
        asset_folder=asset_folder.strip() if isinstance(asset_folder, str) else None,
        asset_folder_by_ordinal=asset_folder_by_ordinal,
    )


def _headers(value: Any, label: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Questionnaire {label} headers are invalid: {path}")
    headers = tuple(item.strip() for item in value if item.strip())
    if not headers:
        raise ValueError(f"Questionnaire {label} headers are empty: {path}")
    return headers


def _required_text(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Questionnaire definition field {key!r} is invalid: {path}")
    return value.strip()
