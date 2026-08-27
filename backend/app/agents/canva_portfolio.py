from __future__ import annotations

import json
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.domain.contracts import (
    CanvaDesignCandidate,
    CanvaPortfolioRequest,
    CanvaPortfolioResult,
    CanvaPortfolioRuntime,
)

CANVA_PORTFOLIO_INSTRUCTIONS = """
You are the Canva production designer for StyleReporter. Create presentation
design candidates for a client-facing Signature Style portfolio using the
provided completed style analysis and questionnaire evidence.

This is the candidate-generation stage only. Do not edit or delete existing
Canva designs, do not create the final editable design from a candidate, and
do not invent client facts, wardrobe items, images, or claims. Preserve the
meaning of the completed report; Canva is responsible for visual structure,
not for re-analysing the client.

Use the Canva connector to generate presentation candidates when the connected
Canva environment supports it. The preferred narrative is:
1. cover and named Style Language;
2. client-facing alignment summary;
3. Current Style Language beside Desired Style Language;
4. The Disconnect;
5. style anchors and visual direction;
6. Your Action Plan;
7. evidence, limitations, and a restrained closing page.

The visual direction should feel editorial, calm, warm, readable, and
personal rather than like a generic AI pitch deck. Use the report's exact
client-facing wording where practical. Keep text legible and leave room for
client outfit/reference images when they are available.

The questionnaire context may contain image URLs and verified local image
paths. Use only supplied image sources. If a supplied remote URL is reachable,
the Canva connector may upload it as an asset; if it is private or unavailable,
continue without it and explain that limitation in `note`. Never fabricate an
image or a successful upload.

Return only one JSON object matching the provided schema. Map every candidate
returned by Canva to its candidate ID, generation job ID, title, design URL,
and thumbnail URL when available. If the Canva workflow requires an
interactive template or user choice that this worker cannot complete, return
`status: "needs_input"`, an empty candidate list, and a concise explanation.
""".strip()


class CanvaDesignCandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    job_id: str
    title: str
    design_url: str | None = Field(...)
    thumbnail_url: str | None = Field(...)


class CanvaPortfolioOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "needs_input", "failed"]
    candidates: list[CanvaDesignCandidateOutput] = Field(min_length=0, max_length=3)
    note: str


class CodexCliCanvaPortfolioRuntime(CanvaPortfolioRuntime):
    """Generate Canva candidates through the host-side Codex CLI worker."""

    def __init__(
        self,
        *,
        runner_url: str,
        runner_token: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 900.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.runner_url = runner_url.rstrip("/")
        self.runner_token = runner_token
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def generate_candidates(self, request: CanvaPortfolioRequest) -> CanvaPortfolioResult:
        headers = {"Content-Type": "application/json"}
        if self.runner_token:
            headers["X-Codex-Runner-Token"] = self.runner_token

        prompt = (
            f"{CANVA_PORTFOLIO_INSTRUCTIONS}\n\n"
            "Return only one JSON object that conforms exactly to the provided output schema.\n\n"
            "Portfolio request:\n"
            f"{json.dumps({
                'client_id': request.client_id,
                'report_run_id': request.report_run_id,
                'client_name': request.client_name,
                'report': request.report,
                'questionnaire_context': request.questionnaire_context,
            }, ensure_ascii=False, sort_keys=True)}"
        )
        payload = {
            "prompt": prompt,
            "model": self.model,
            "output_schema": CanvaPortfolioOutput.model_json_schema(),
            "image_paths": list(request.asset_paths),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.runner_url}/v1/canva/design-candidates",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Codex CLI worker is unreachable: {exc}") from exc

        if response.is_error:
            detail = _response_error_detail(response)
            raise RuntimeError(f"Codex CLI worker returned HTTP {response.status_code}: {detail}")

        try:
            worker_payload = response.json()
            output = CanvaPortfolioOutput.model_validate(worker_payload["result"])
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(
                "Codex CLI worker returned an invalid Canva portfolio payload."
            ) from exc

        return CanvaPortfolioResult(
            status=output.status,
            candidates=[
                CanvaDesignCandidate(
                    candidate_id=item.candidate_id,
                    job_id=item.job_id,
                    title=item.title,
                    design_url=item.design_url,
                    thumbnail_url=item.thumbnail_url,
                )
                for item in output.candidates
            ],
            note=output.note,
        )


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No additional details."
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"][:500]
    return "No additional details."
