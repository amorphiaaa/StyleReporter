from app.domain.questionnaire import (
    QUESTIONNAIRE_FIXTURE_VERSION,
    normalize_questionnaire_payload,
)


def test_fixture_questionnaire_normalizes_answers_and_image_links() -> None:
    normalized = normalize_questionnaire_payload(
        {
            "Email": " synthetic.client@example.test ",
            "Name": "Synthetic Client",
            "How would you describe your style today?": "elegant but repetitive",
            "What would you love your style to help you feel?": "More like myself",
            "Which sentence sounds MOST like you?": "B",
            "What usually makes an outfit feel wrong to you?": "A",
            "Feels Like Me images": "https://example.test/one.jpg,\nhttps://example.test/two.jpg",
            "Not Me image": "https://example.test/not-me.jpg",
            "Inspiration images": "https://example.test/inspiration.jpg",
            "Visual world": "B",
        },
        version=QUESTIONNAIRE_FIXTURE_VERSION,
    )

    assert normalized.email == "synthetic.client@example.test"
    assert normalized.display_name == "Synthetic Client"
    assert normalized.current_style == "elegant but repetitive"
    assert normalized.style_goal == "More like myself"
    assert normalized.feels_like_me_images == (
        "https://example.test/one.jpg",
        "https://example.test/two.jpg",
    )
    assert normalized.not_me_image == "https://example.test/not-me.jpg"
    assert normalized.missing_required_fields == ()


def test_fixture_questionnaire_reports_missing_fields_without_rejecting_raw_data() -> None:
    normalized = normalize_questionnaire_payload(
        {
            "Email": "synthetic.client@example.test",
            "Visual world": "B",
        },
        version=QUESTIONNAIRE_FIXTURE_VERSION,
    )

    assert normalized.email == "synthetic.client@example.test"
    assert "current_style" in normalized.missing_required_fields
    assert "visual_world" not in normalized.missing_required_fields


def test_fixture_questionnaire_uses_configured_identity_aliases_and_extra_fields() -> None:
    normalized = normalize_questionnaire_payload(
        {
            "Your email": "realistic.client@example.test",
            "Your name": "Realistic Client",
            "What feels hardest in your style right now?": "Getting dressed quickly",
        },
        version=QUESTIONNAIRE_FIXTURE_VERSION,
    )

    assert normalized.email == "realistic.client@example.test"
    assert normalized.display_name == "Realistic Client"
    assert normalized.answers["style_challenge"] == "Getting dressed quickly"


def test_unknown_questionnaire_version_falls_back_to_identity_fields() -> None:
    normalized = normalize_questionnaire_payload(
        {
            "Email": "synthetic.client@example.test",
            "Name": "Synthetic Client",
            "Visual world": "B",
        },
        version="future-v2",
    )

    assert normalized.version == "future-v2"
    assert normalized.email == "synthetic.client@example.test"
    assert normalized.display_name == "Synthetic Client"
    assert normalized.visual_world is None
    assert normalized.missing_required_fields == ()
