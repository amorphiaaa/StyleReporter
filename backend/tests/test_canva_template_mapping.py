from pathlib import Path

import pytest

from app.domain.contracts import CanvaPlacementAssignment, CanvaPlacementPlan
from app.services.canva_template_mapping import (
    build_canva_payload,
    build_sequential_placement_plan,
    template_definition_from_dataset,
    template_definition_from_manifest,
)
from tests.fakes import InMemoryCanvaDesignProvider

TEMPLATE_MANIFEST = {
    "key": "signature-style-template",
    "version": "1",
    "brand_template_id": None,
    "pages": [
        {
            "number": 1,
            "description": "Cover and style positioning",
            "fields": [
                {
                    "key": "field_001",
                    "type": "text",
                    "description": "The large title shown on the cover",
                    "required": True,
                    "max_characters": 80,
                },
                {
                    "key": "field_002",
                    "type": "text",
                    "description": "Short positioning statement below the title",
                },
                {
                    "key": "image_001",
                    "type": "image",
                    "description": "Client portrait used on the cover",
                },
            ],
        }
    ],
}


def test_manifest_keeps_technical_keys_separate_from_semantic_descriptions() -> None:
    template = template_definition_from_manifest(TEMPLATE_MANIFEST)

    assert template.key == "signature-style-template"
    assert template.pages[0].description == "Cover and style positioning"
    assert template.fields[0].key == "field_001"
    assert template.fields[0].description == "The large title shown on the cover"
    assert template.fields[0].page_number == 1
    assert template.fields[2].field_type == "image"


def test_agent_plan_maps_existing_report_content_to_arbitrary_fields() -> None:
    template = template_definition_from_manifest(TEMPLATE_MANIFEST)
    plan = CanvaPlacementPlan(
        assignments=(
            CanvaPlacementAssignment("field_001", "title", "Best short title for the cover"),
            CanvaPlacementAssignment(
                "field_002",
                "alignment_summary",
                "The summary fits the descriptive field",
            ),
            CanvaPlacementAssignment("image_001", "assets.client_portrait", "Portrait slot"),
        )
    )

    payload = build_canva_payload(
        {"title": "Relaxed creative", "alignment_summary": "A calm, expressive wardrobe"},
        template,
        plan,
        asset_paths={"image_001": Path("portrait.jpg")},
    )

    assert payload.template_key == "signature-style-template"
    assert payload.values == {
        "field_001": "Relaxed creative",
        "field_002": "A calm, expressive wardrobe",
    }
    assert payload.asset_paths == {"image_001": Path("portrait.jpg")}


def test_agent_plan_rejects_unknown_or_missing_required_fields() -> None:
    template = template_definition_from_manifest(TEMPLATE_MANIFEST)

    with pytest.raises(ValueError, match="Unknown template field.*Required template field"):
        build_canva_payload(
            {},
            template,
            CanvaPlacementPlan(
                assignments=(CanvaPlacementAssignment("unknown", "title"),)
            ),
        )


def test_sequential_plan_keeps_authored_values_and_assets_in_stable_order() -> None:
    template = template_definition_from_dataset(
        "template-1",
        {"field_001": "text", "field_002": "text", "image_001": "image"},
    )

    plan = build_sequential_placement_plan(
        {"title": "Report title", "summary": "Report summary"},
        template,
        [Path("first.jpg")],
    )

    assert [(item.field_key, item.source_path) for item in plan.assignments] == [
        ("field_001", "title"),
        ("field_002", "summary"),
        ("image_001", "first.jpg"),
    ]


@pytest.mark.asyncio
async def test_fake_canva_provider_runs_autofill_and_export_jobs() -> None:
    provider = InMemoryCanvaDesignProvider()
    template = template_definition_from_manifest(TEMPLATE_MANIFEST)

    asset_id = await provider.upload_asset(local_path=Path("profile.jpg"), name="profile.jpg")
    job = await provider.create_autofill_job(
        template=template,
        values={"field_001": "Test report"},
        asset_ids={"image_001": asset_id},
    )
    export = await provider.create_export_job(design_id=job.design_id or "")

    assert job.status == "succeeded"
    assert job.design_url == "https://canva.example/designs/design-1"
    assert export.status == "succeeded"
