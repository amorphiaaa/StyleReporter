"""Flexible mapping between a manual report and a Canva template manifest.

The agent chooses placements from the field descriptions. This module only
validates that plan and converts it into a provider-neutral payload; it never
calls Canva or invents report copy.
"""

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from app.domain.contracts import (
    CanvaAutofillPayload,
    CanvaFieldType,
    CanvaPlacementAssignment,
    CanvaPlacementPlan,
    CanvaTemplateDefinition,
    CanvaTemplateField,
    CanvaTemplatePage,
)


def template_definition_from_dataset(
    template_id: str,
    dataset: Mapping[str, CanvaFieldType],
) -> CanvaTemplateDefinition:
    """Create a provider-neutral definition from Canva's live dataset."""

    return CanvaTemplateDefinition(
        key=template_id,
        version="live",
        brand_template_id=template_id,
        pages=(),
        fields=tuple(
            CanvaTemplateField(
                key=key,
                field_type=field_type,
                page_number=1,
                description="Placement is chosen from the report content and field order.",
            )
            for key, field_type in dataset.items()
        ),
    )


def build_sequential_placement_plan(
    content: Mapping[str, Any],
    template: CanvaTemplateDefinition,
    asset_paths: Sequence[Path],
) -> CanvaPlacementPlan:
    """Place authored values and assets without generating or rewriting copy.

    The template fields are intentionally opaque. Until a richer placement agent is
    connected, this deterministic fallback keeps the workflow usable by pairing
    report leaves and local images in their stable order.
    """

    text_values = list(_iter_text_values(content))
    text_fields = [field for field in template.fields if field.field_type == "text"]
    image_fields = [field for field in template.fields if field.field_type == "image"]
    assignments: list[CanvaPlacementAssignment] = []
    for field, (source_path, value) in zip(text_fields, text_values, strict=False):
        if value.strip():
            assignments.append(
                CanvaPlacementAssignment(field.key, source_path, "Stable report order")
            )
    for field, asset_path in zip(image_fields, asset_paths, strict=False):
        assignments.append(
            CanvaPlacementAssignment(field.key, str(asset_path), "Stable asset order")
        )
    return CanvaPlacementPlan(assignments=tuple(assignments))


def _iter_text_values(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        if value.strip():
            yield path, value
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _iter_text_values(child, child_path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _iter_text_values(child, child_path)


def template_definition_from_manifest(
    manifest: Mapping[str, Any],
) -> CanvaTemplateDefinition:
    """Build a template definition from a human-authored manifest."""

    pages: list[CanvaTemplatePage] = []
    fields: list[CanvaTemplateField] = []
    seen_keys: set[str] = set()

    for page_data in _list_value(manifest, "pages"):
        page_number = _positive_int(page_data, "number")
        page_description = _required_text(page_data, "description")
        pages.append(CanvaTemplatePage(page_number, page_description))
        for field_data in _list_value(page_data, "fields"):
            key = _required_text(field_data, "key")
            if key in seen_keys:
                raise ValueError(f"Duplicate Canva template field key: {key}")
            seen_keys.add(key)
            field_type = field_data.get("type", "text")
            if field_type not in ("text", "image"):
                raise ValueError(f"Unsupported Canva field type for {key}: {field_type}")
            max_characters = field_data.get("max_characters")
            if max_characters is not None:
                max_characters = _positive_int(field_data, "max_characters")
            fields.append(
                CanvaTemplateField(
                    key=key,
                    field_type=field_type,
                    page_number=page_number,
                    description=_required_text(field_data, "description"),
                    required=bool(field_data.get("required", False)),
                    max_characters=max_characters,
                )
            )

    return CanvaTemplateDefinition(
        key=_required_text(manifest, "key"),
        version=_required_text(manifest, "version"),
        brand_template_id=manifest.get("brand_template_id"),
        pages=tuple(pages),
        fields=tuple(fields),
    )


def build_canva_payload(
    content: Mapping[str, Any],
    template: CanvaTemplateDefinition,
    plan: CanvaPlacementPlan,
    *,
    asset_paths: Mapping[str, Path] | None = None,
) -> CanvaAutofillPayload:
    """Validate an agent placement plan and create an autofill payload."""

    fields_by_key = {field.key: field for field in template.fields}
    assignments_by_key = {}
    errors: list[str] = []
    values: dict[str, str] = {}
    selected_assets = asset_paths or {}

    for assignment in plan.assignments:
        field = fields_by_key.get(assignment.field_key)
        if field is None:
            errors.append(f"Unknown template field: {assignment.field_key}")
            continue
        if assignment.field_key in assignments_by_key:
            errors.append(f"Field assigned more than once: {assignment.field_key}")
            continue
        assignments_by_key[assignment.field_key] = assignment

        if field.field_type == "image":
            if assignment.field_key not in selected_assets:
                errors.append(f"Missing local asset for image field: {assignment.field_key}")
            continue

        value = _stringify(_read_path(content, assignment.source_path))
        if not value:
            errors.append(f"Missing report content for field: {assignment.field_key}")
            continue
        if field.max_characters and len(value) > field.max_characters:
            errors.append(
                f"Content exceeds {field.max_characters} characters for field: "
                f"{assignment.field_key}"
            )
            continue
        values[assignment.field_key] = value

    for field in template.fields:
        if field.required and field.key not in assignments_by_key:
            errors.append(f"Required template field was not assigned: {field.key}")

    if errors:
        raise ValueError("; ".join(errors))

    return CanvaAutofillPayload(
        template_key=template.key,
        values=values,
        asset_paths={
            field_key: path
            for field_key, path in selected_assets.items()
            if field_key in assignments_by_key and fields_by_key[field_key].field_type == "image"
        },
    )


def _read_path(value: Any, source_path: str) -> Any:
    current = value
    for segment in source_path.split("."):
        if "[" in segment and segment.endswith("]"):
            key, index_text = segment[:-1].split("[", 1)
            current = current.get(key) if isinstance(current, Mapping) else None
            if not isinstance(current, Sequence) or isinstance(current, str):
                return None
            index = int(index_text)
            current = current[index] if index < len(current) else None
        else:
            current = current.get(segment) if isinstance(current, Mapping) else None
        if current is None:
            return None
    return current


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "\n".join(_stringify(item) for item in value)
    return str(value)


def _list_value(value: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    items = value.get(key, [])
    if not isinstance(items, list):
        raise ValueError(f"Manifest field must be a list: {key}")
    if not all(isinstance(item, Mapping) for item in items):
        raise ValueError(f"Manifest list must contain objects: {key}")
    return items


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"Manifest field must be a non-empty string: {key}")
    return item.strip()


def _positive_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
        raise ValueError(f"Manifest field must be a positive integer: {key}")
    return item
