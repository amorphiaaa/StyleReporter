"""Mapping from the manual report model to a versioned Canva field contract.

This module deliberately does not call Canva. It produces a deterministic
payload that a later Canva Connect adapter can submit to an autofill job.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.domain.contracts import (
    CanvaAutofillPayload,
    CanvaTemplateDefinition,
    CanvaTemplateField,
)

SIGNATURE_STYLE_TEMPLATE_KEY = "signature-style-v1"
MAX_LIST_ITEMS = 5
MAX_PALETTE_COLORS = 5
MAX_SILHOUETTES_PER_GROUP = 5
MAX_ACCESSORY_CATEGORIES = 6
MAX_OUTFIT_FORMULAS = 4
MAX_STYLE_ANCHORS = 4
MAX_BRAND_CATEGORIES = 11
MAX_MOODBOARD_ITEMS = 3
MAX_ACTION_ITEMS = 3
IMAGE_SLOTS = (
    "CLIENT_PORTRAIT",
    "CLIENT_BODY_PROPORTION",
    "CLIENT_GOOD_OUTFIT_1",
    "CLIENT_GOOD_OUTFIT_2",
    "CLIENT_GOOD_OUTFIT_3",
    "CLIENT_NOT_ME_1",
    "CLIENT_NOT_ME_2",
    "CLIENT_INSPIRATION_1",
    "CLIENT_INSPIRATION_2",
    "CLIENT_INSPIRATION_3",
)

PALETTE_KEYS = ("foundation", "accent", "portrait")
SILHOUETTE_GROUPS = (
    ("OUTER_LAYERS", "outer_layers"),
    ("BOTTOMS", "bottoms"),
    ("TOPS_AND_KNITWEAR", "tops_and_knitwear"),
    ("DRESSES", "dresses"),
)
ACCESSORY_CATEGORIES = (
    "EYEWEAR",
    "WATCHES",
    "BAGS",
    "JEWELLERY_BELTS",
    "SCARVES",
    "SHOES",
)
BRAND_CATEGORIES = (
    "COATS_JACKETS",
    "BOTTOMS",
    "KNITWEAR",
    "DRESSES",
    "SHIRTS_BLOUSES_TSHIRTS",
    "DENIM",
    "JEWELLERY",
    "ACCESSORIES",
    "SUNGLASSES",
    "BAGS",
    "SHOES",
)


def signature_style_template_definition() -> CanvaTemplateDefinition:
    """Return the field names to use when the Canva template is created."""

    fields: list[CanvaTemplateField] = []

    def text(key: str, source_path: str, *, required: bool = False) -> None:
        fields.append(CanvaTemplateField(key, "text", source_path, required))

    def text_list(prefix: str, source_path: str, count: int = MAX_LIST_ITEMS) -> None:
        for index in range(count):
            text(f"{prefix}_{index + 1}", f"{source_path}[{index}]")

    text("HOW_TO_USE_INTRO", "how_to_use.intro")
    text_list("HOW_TO_USE_ITEM", "how_to_use.items", 3)
    text("REPORT_TITLE", "title", required=True)
    text("ALIGNMENT_SUMMARY", "alignment_summary")
    text_list("CURRENT_STYLE", "current_style_language")
    text_list("DESIRED_STYLE", "desired_style_language")
    text("DISCONNECT", "disconnect")
    text("STYLE_LANGUAGE_SUMMARY", "style_language_summary")
    text_list("STYLE_LANGUAGE_ANCHOR", "style_language_anchors", 3)

    for palette_key in PALETTE_KEYS:
        prefix = palette_key.upper()
        text(f"PALETTE_{prefix}_INTRO", f"color_palette.{palette_key}.intro")
        for index in range(MAX_PALETTE_COLORS):
            base = f"PALETTE_{prefix}_{index + 1}"
            source = f"color_palette.{palette_key}.colors[{index}]"
            text(f"{base}_NAME", f"{source}.name")
            text(f"{base}_HEX", f"{source}.hex")
            text(f"{base}_DESCRIPTION", f"{source}.description")
            text(f"{base}_WORKS_WITH", f"{source}.works_with")

    text("PRINTS_TEXTURES_INTRO", "prints_and_textures.intro")
    text_list("PRINTS_WHAT_WORKS", "prints_and_textures.what_works")
    text_list("PRINTS_HOW_TO_USE", "prints_and_textures.how_to_use")

    text("SILHOUETTES_INTRO", "silhouettes.intro")
    for group_key, source_key in SILHOUETTE_GROUPS:
        for index in range(MAX_SILHOUETTES_PER_GROUP):
            base = f"SILHOUETTE_{group_key}_{index + 1}"
            source = f"silhouettes.{source_key}[{index}]"
            text(f"{base}_NAME", f"{source}.name")
            text(f"{base}_DESCRIPTION", f"{source}.description")

    text("ACCESSORIES_INTRO", "accessories.intro")
    text_list("ACCESSORIES_CORE_ELEMENT", "accessories.core_elements")
    text_list("ACCESSORIES_USE_PRINCIPLE", "accessories.use_principles")
    for index, category_key in enumerate(ACCESSORY_CATEGORIES):
        source = f"accessories.categories[{index}]"
        text(f"ACCESSORIES_{category_key}_NAME", f"{source}.name")
        text_list(f"ACCESSORIES_{category_key}_ITEM", f"{source}.items")

    for index in range(MAX_OUTFIT_FORMULAS):
        base = f"OUTFIT_FORMULA_{index + 1}"
        source = f"outfit_formulas[{index}]"
        text(f"{base}_NAME", f"{source}.name")
        text(f"{base}_OCCASIONS", f"{source}.occasions")
        text(f"{base}_LOGIC", f"{source}.logic")
        text_list(f"{base}_STEP", f"{source}.steps")

    for index in range(MAX_STYLE_ANCHORS):
        source = f"style_anchors[{index}]"
        text(f"STYLE_ANCHOR_{index + 1}_NAME", f"{source}.name")
        text(f"STYLE_ANCHOR_{index + 1}_DESCRIPTION", f"{source}.description")

    text("DISTRACTIONS_INTRO", "what_can_distract.intro")
    text_list("DISTRACTIONS_COLOR", "what_can_distract.colors")
    text_list("DISTRACTIONS_PRINT", "what_can_distract.prints")
    text_list("DISTRACTIONS_SILHOUETTE", "what_can_distract.silhouettes")

    for index, category_key in enumerate(BRAND_CATEGORIES):
        source = f"brands[{index}]"
        text(f"BRANDS_{category_key}_CATEGORY", f"{source}.category")
        text_list(f"BRANDS_{category_key}", f"{source}.brands")

    for index in range(MAX_MOODBOARD_ITEMS):
        base = f"MOODBOARD_{index + 1}"
        source = f"moodboard[{index}]"
        text(f"{base}_LABEL", f"{source}.label")
        text(f"{base}_URL", f"{source}.url")
        text(f"{base}_NOTE", f"{source}.note")

    for index in range(MAX_ACTION_ITEMS):
        base = f"ACTION_{index + 1}"
        source = f"action_plan[{index}]"
        text(f"{base}_TITLE", f"{source}.title")
        text(f"{base}_BODY", f"{source}.body")

    for image_key in IMAGE_SLOTS:
        fields.append(CanvaTemplateField(image_key, "image", f"assets.{image_key.lower()}"))

    return CanvaTemplateDefinition(
        key=SIGNATURE_STYLE_TEMPLATE_KEY,
        version="1",
        brand_template_id=None,
        fields=tuple(fields),
    )


def flatten_manual_style_report(
    content: Mapping[str, Any],
    template: CanvaTemplateDefinition | None = None,
    *,
    asset_paths: Mapping[str, Path] | None = None,
) -> CanvaAutofillPayload:
    """Flatten structured report content into named template values.

    Missing slots are emitted as empty strings so a fixed Canva template can
    keep its layout when a report has fewer items than its maximum capacity.
    """

    definition = template or signature_style_template_definition()
    values: dict[str, str] = {}
    image_paths: dict[str, Path] = {}
    supplied_assets = asset_paths or {}

    for field in definition.fields:
        if field.field_type == "text":
            values[field.key] = _stringify(_read_path(content, field.source_path))
        elif field.key in supplied_assets:
            image_paths[field.key] = supplied_assets[field.key]

    return CanvaAutofillPayload(
        template_key=definition.key,
        values=values,
        asset_paths=image_paths,
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
