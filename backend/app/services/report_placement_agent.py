"""AI-assisted placement of authored report content into Canva fields."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx

from app.domain.contracts import (
    CanvaPlacementAssignment,
    CanvaPlacementPlan,
    CanvaTemplateDefinition,
)


class ReportPlacementError(RuntimeError):
    """Raised when the placement model cannot return a safe plan."""


class OpenAIReportPlacementAgent:
    """Use OpenAI Structured Outputs to place text and image groups.

    The model is instructed to copy text from the user's source verbatim. It
    only decides which existing text or image belongs in a template field.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def create_plan(
        self,
        *,
        source_text: str,
        image_groups: Sequence[Mapping[str, Any]],
        template: CanvaTemplateDefinition,
        assets: Mapping[str, Path],
    ) -> CanvaPlacementPlan:
        if not source_text.strip() and not image_groups:
            return CanvaPlacementPlan(assignments=())

        input_payload = {
            "source_text": source_text,
            "image_groups": [dict(group) for group in image_groups],
            "available_assets": sorted(assets),
            "template": {
                "pages": [
                    {"number": page.page_number, "description": page.description}
                    for page in template.pages
                ],
                "fields": [
                    {
                        "key": field.key,
                        "type": field.field_type,
                        "page": field.page_number,
                        "description": field.description,
                        "required": field.required,
                        "max_characters": field.max_characters,
                    }
                    for field in template.fields
                ],
            },
        }
        response = await self._request(input_payload)
        parsed = _parse_response_json(response)
        return _placement_plan_from_response(parsed, source_text, template, assets)

    async def _request(self, input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        request_body = {
            "model": self._model,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You place user-authored report content into a Canva template. "
                                "Return only a valid placement plan. Never invent, summarize, "
                                "translate, or rewrite text. Text values must be exact substrings "
                                "copied from source_text. Use each template field at most once. "
                                "Only choose image asset keys from available_assets."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(input_payload)}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "canva_placement_plan",
                    "strict": True,
                    "schema": _placement_schema(),
                }
            },
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client = self._client
        if client is None:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client_http:
                response = await client_http.post(
                    f"{self._base_url}/responses",
                    json=request_body,
                    headers=headers,
                )
        else:
            response = await client.post(
                f"{self._base_url}/responses",
                json=request_body,
                headers=headers,
            )
        if response.is_error:
            raise ReportPlacementError("The placement agent request failed.")
        body = response.json()
        if not isinstance(body, Mapping):
            raise ReportPlacementError("The placement agent returned an invalid response.")
        return body


def _placement_schema() -> dict[str, Any]:
    assignment = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field_key": {"type": "string"},
            "value": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": ["field_key", "value", "rationale"],
    }
    image_assignment = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field_key": {"type": "string"},
            "asset_key": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": ["field_key", "asset_key", "rationale"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "text_assignments": {"type": "array", "items": assignment},
            "image_assignments": {"type": "array", "items": image_assignment},
            "unplaced_source_paths": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["text_assignments", "image_assignments", "unplaced_source_paths"],
    }


def _parse_response_json(response: Mapping[str, Any]) -> Mapping[str, Any]:
    output_text = response.get("output_text")
    if not isinstance(output_text, str):
        output_text = _find_output_text(response.get("output"))
    if not output_text:
        raise ReportPlacementError("The placement agent returned no structured output.")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise ReportPlacementError("The placement agent returned invalid JSON.") from exc
    if not isinstance(parsed, Mapping):
        raise ReportPlacementError("The placement agent returned an invalid placement plan.")
    return parsed


def _find_output_text(output: Any) -> str | None:
    if not isinstance(output, list):
        return None
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if isinstance(content_item, Mapping) and content_item.get("type") == "output_text":
                text = content_item.get("text")
                if isinstance(text, str):
                    return text
    return None


def _placement_plan_from_response(
    response: Mapping[str, Any],
    source_text: str,
    template: CanvaTemplateDefinition,
    assets: Mapping[str, Path],
) -> CanvaPlacementPlan:
    fields = {field.key: field for field in template.fields}
    assignments: list[CanvaPlacementAssignment] = []
    seen_fields: set[str] = set()

    for item in _list_of_mappings(response, "text_assignments"):
        field_key = _required_string(item, "field_key")
        value = _required_string(item, "value")
        field = fields.get(field_key)
        if field is None or field.field_type != "text":
            raise ReportPlacementError(
                f"Placement agent selected an invalid text field: {field_key}"
            )
        if field_key in seen_fields:
            raise ReportPlacementError(f"Placement agent assigned a field twice: {field_key}")
        if value not in source_text:
            raise ReportPlacementError(
                f"Placement agent rewrote text for field: {field_key}"
            )
        seen_fields.add(field_key)
        assignments.append(
            CanvaPlacementAssignment(
                field_key=field_key,
                source_path="",
                rationale=_optional_string(item, "rationale"),
                value=value,
            )
        )

    for item in _list_of_mappings(response, "image_assignments"):
        field_key = _required_string(item, "field_key")
        asset_key = _required_string(item, "asset_key")
        field = fields.get(field_key)
        if field is None or field.field_type != "image":
            raise ReportPlacementError(
                f"Placement agent selected an invalid image field: {field_key}"
            )
        if field_key in seen_fields:
            raise ReportPlacementError(f"Placement agent assigned a field twice: {field_key}")
        if asset_key not in assets:
            raise ReportPlacementError(
                f"Placement agent selected an unavailable image: {asset_key}"
            )
        seen_fields.add(field_key)
        assignments.append(
            CanvaPlacementAssignment(
                field_key=field_key,
                source_path=str(assets[asset_key]),
                rationale=_optional_string(item, "rationale"),
            )
        )

    unplaced = response.get("unplaced_source_paths", [])
    if not isinstance(unplaced, list) or not all(isinstance(item, str) for item in unplaced):
        raise ReportPlacementError("Placement agent returned invalid unplaced paths.")
    return CanvaPlacementPlan(assignments=tuple(assignments), unplaced_source_paths=tuple(unplaced))


def _list_of_mappings(response: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = response.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ReportPlacementError(f"Placement agent returned invalid {key}.")
    return value


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ReportPlacementError(f"Placement agent returned an empty {key}.")
    return item


def _optional_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key, "")
    return item if isinstance(item, str) else ""
