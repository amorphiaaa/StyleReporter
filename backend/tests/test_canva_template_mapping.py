from pathlib import Path

import pytest

from app.domain.contracts import CanvaTemplateDefinition, CanvaTemplateField
from app.services.canva_template_mapping import (
    flatten_manual_style_report,
    signature_style_template_definition,
)
from tests.fakes import InMemoryCanvaDesignProvider


def test_signature_style_template_has_stable_unique_field_names() -> None:
    template = signature_style_template_definition()
    keys = [field.key for field in template.fields]

    assert template.key == "signature-style-v1"
    assert template.brand_template_id is None
    assert len(keys) > 200
    assert len(keys) == len(set(keys))
    assert "REPORT_TITLE" in keys
    assert "PALETTE_FOUNDATION_1_HEX" in keys
    assert "SILHOUETTE_OUTER_LAYERS_1_DESCRIPTION" in keys
    assert "OUTFIT_FORMULA_4_STEP_5" in keys
    assert "ACTION_3_BODY" in keys
    assert "CLIENT_PORTRAIT" in keys


def test_flatten_manual_report_preserves_values_and_empty_slots() -> None:
    template = signature_style_template_definition()
    payload = flatten_manual_style_report(
        {
            "title": "Relaxed creative",
            "current_style_language": ["Casual", "Repetitive"],
            "color_palette": {
                "foundation": {
                    "colors": [{"name": "Olive", "hex": "#708238"}],
                },
            },
            "outfit_formulas": [{"occasions": ["Every day", "Lunch"]}],
        },
        template,
        asset_paths={"CLIENT_PORTRAIT": Path("portrait.jpg")},
    )

    assert payload.values["REPORT_TITLE"] == "Relaxed creative"
    assert payload.values["CURRENT_STYLE_1"] == "Casual"
    assert payload.values["CURRENT_STYLE_3"] == ""
    assert payload.values["PALETTE_FOUNDATION_1_NAME"] == "Olive"
    assert payload.values["PALETTE_FOUNDATION_1_HEX"] == "#708238"
    assert payload.values["PALETTE_FOUNDATION_2_NAME"] == ""
    assert payload.values["OUTFIT_FORMULA_1_OCCASIONS"] == "Every day\nLunch"
    assert payload.asset_paths == {"CLIENT_PORTRAIT": Path("portrait.jpg")}


@pytest.mark.asyncio
async def test_fake_canva_provider_runs_autofill_and_export_jobs() -> None:
    provider = InMemoryCanvaDesignProvider()
    template = CanvaTemplateDefinition(
        key="test-template",
        version="1",
        brand_template_id="brand-template-1",
        fields=(
            CanvaTemplateField("REPORT_TITLE", "text", "title"),
            CanvaTemplateField("PROFILE_IMAGE", "image", "profile_image"),
        ),
    )

    asset_id = await provider.upload_asset(local_path=Path("profile.jpg"), name="profile.jpg")
    job = await provider.create_autofill_job(
        template=template,
        values={"REPORT_TITLE": "Test report"},
        asset_ids={"PROFILE_IMAGE": asset_id},
    )
    export = await provider.create_export_job(design_id=job.design_id or "")

    assert job.status == "succeeded"
    assert job.design_url == "https://canva.example/designs/design-1"
    assert export.status == "succeeded"
    assert provider.autofill_requests == [
        ("test-template", {"REPORT_TITLE": "Test report"}, {"PROFILE_IMAGE": "asset-1"})
    ]
