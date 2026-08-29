from pathlib import Path

import httpx
import pytest

from app.domain.contracts import CanvaTemplateDefinition, CanvaTemplateField, CanvaTemplatePage
from app.services.report_placement_agent import OpenAIReportPlacementAgent


@pytest.mark.asyncio
async def test_openai_placement_agent_returns_text_and_image_assignments() -> None:
    response_json = {
        "output_text": (
            '{"text_assignments":[{"field_key":"field_001",'
            '"value":"Feminine Creative","rationale":"Cover title"}],'
            '"image_assignments":[{"field_key":"image_001",'
            '"asset_key":"portrait.jpg:1","rationale":"Portrait slot"}],'
            '"unplaced_source_paths":[]}'
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json=response_json, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        agent = OpenAIReportPlacementAgent(
            api_key="test-key",
            model="test-model",
            base_url="https://api.openai.test/v1",
            client=client,
        )
        plan = await agent.create_plan(
            source_text="Feminine Creative\nA manually authored report.",
            image_groups=[
                {
                    "group_key": "portraits",
                    "label": "Portraits",
                    "instructions": "Client portrait",
                    "asset_keys": ["portrait.jpg:1"],
                }
            ],
            template=CanvaTemplateDefinition(
                key="template",
                version="live",
                brand_template_id="template",
                pages=(CanvaTemplatePage(1, "Cover"),),
                fields=(
                    CanvaTemplateField("field_001", "text", 1, "Cover title"),
                    CanvaTemplateField("image_001", "image", 1, "Portrait"),
                ),
                source_type="design",
            ),
            assets={"portrait.jpg:1": Path("portrait.jpg")},
        )

    assert len(plan.assignments) == 2
    assert plan.assignments[0].value == "Feminine Creative"
    assert plan.assignments[1].source_path == "portrait.jpg"
