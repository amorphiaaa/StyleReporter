from app.domain.contracts import ImportRequest, ImportResult, QuestionnaireImporter


class ScaffoldQuestionnaireImporter(QuestionnaireImporter):
    """Future orchestration boundary for source rows and repositories."""

    async def import_rows(self, request: ImportRequest) -> ImportResult:
        raise NotImplementedError(
            "Questionnaire import is intentionally not implemented in the scaffold."
        )
