from app.domain.contracts import StyleReport, StyleReportRequest, StyleReportRuntime


class StubStyleReportRuntime(StyleReportRuntime):
    """Deterministic local runtime used until the real agent is wired in."""

    async def generate(self, request: StyleReportRequest) -> StyleReport:
        answered_fields = sorted(
            key
            for key, value in request.raw_payload.items()
            if value is not None and str(value).strip()
        )
        return StyleReport(
            report_version="stub-v1",
            runtime_type="stub",
            content={
                "title": "Style report draft",
                "summary": (
                    "This is a deterministic scaffold output. Replace the stub runtime "
                    "with the style-methodologist agent in a later iteration."
                ),
                "evidence": {
                    "source_submission_id": request.submission_id,
                    "answered_fields": answered_fields,
                },
                "sections": [
                    {
                        "key": "observations",
                        "title": "Observed questionnaire fields",
                        "items": answered_fields,
                    },
                    {
                        "key": "next_step",
                        "title": "Next implementation step",
                        "items": ["Connect a real methodologist runtime."],
                    },
                ],
            },
        )
