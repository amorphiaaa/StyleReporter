from app.api.schemas.manual_reports import ManualStyleReportContent


def test_manual_report_schema_covers_template_sections() -> None:
    content = ManualStyleReportContent.model_validate(
        {
            "title": "Feminine Creative",
            "current_style_language": ["Feminine", "Practical"],
            "desired_style_language": ["Creative", "Confident"],
            "color_palette": {
                "foundation": {
                    "intro": "Soft neutrals create the foundation.",
                    "colors": [{"name": "Chocolate", "hex": "#5B3828"}],
                }
            },
            "outfit_formulas": [
                {
                    "name": "Artistic print + colourful basic",
                    "occasions": ["Every day"],
                    "logic": "Let one expressive piece lead.",
                    "steps": ["Start with one print."],
                }
            ],
            "action_plan": [{"title": "Use one expressive element", "body": "Start small."}],
        }
    )

    assert content.color_palette["foundation"].colors[0].hex == "#5B3828"
    assert content.outfit_formulas[0].occasions == ["Every day"]
    assert content.action_plan[0].title == "Use one expressive element"


def test_manual_report_schema_rejects_unknown_fields() -> None:
    try:
        ManualStyleReportContent.model_validate({"unexpected": "value"})
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("Unknown report fields must be rejected")
