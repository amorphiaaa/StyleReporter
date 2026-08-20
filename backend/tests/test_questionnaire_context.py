import json

from app.agents.questionnaire_context import build_questionnaire_context
from app.agents.runtime import _serialize_request
from app.domain.contracts import StyleReportRequest


def test_questionnaire_context_contains_typed_answers_and_excludes_identity() -> None:
    request = StyleReportRequest(
        client_id="client-1",
        submission_id="submission-1",
        questionnaire_version="fixture-v1",
        raw_payload={
            "Email": "client@example.test",
            "Name": "Synthetic Client",
            "Timestamp": "2026-01-15T10:30:00+00:00",
            "How would you describe your style today?": "elegant but repetitive",
            "What would you love your style to help you feel?": "More like myself",
            "Visual world": "B",
        },
    )

    context = build_questionnaire_context(request)
    serialized = _serialize_request(request)

    assert context["normalized_answers"]["current_style"] == "elegant but repetitive"
    assert context["normalized_answers"]["style_goal"] == "More like myself"
    assert context["raw_answers"]["Visual world"] == "B"
    assert "Email" not in context["raw_answers"]
    assert "Name" not in context["raw_answers"]
    assert "client@example.test" not in serialized
    assert json.loads(serialized)["questionnaire"] == context
