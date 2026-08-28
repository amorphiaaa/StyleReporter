# Canva template integration

The Canva integration uses a flexible template manifest. A manifest describes
the pages and the visual purpose of each field; it does not prescribe which
report section must go into that field. The agent makes that placement decision
from the report content and the descriptions.

Canva still needs a unique technical key for every autofill field. Keys such
as `field_001` are intentionally opaque. Their meaning lives in the
description, page context, and optional constraints in the manifest.

The example structure is in
`docs/integrations/canva-template-manifest.example.json`.

## Manifest format

```json
{
  "key": "signature-style-template",
  "version": "1",
  "brand_template_id": null,
  "pages": [
    {
      "number": 1,
      "description": "Cover and personal style positioning",
      "fields": [
        {
          "key": "field_001",
          "type": "text",
          "description": "Large title for the report cover",
          "required": true,
          "max_characters": 80
        },
        {
          "key": "image_001",
          "type": "image",
          "description": "Portrait image placed beside the title"
        }
      ]
    }
  ]
}
```

The template author can describe a field by visual role, for example:

- “short headline above the palette”;
- “three compact bullets beside the outfit image”;
- “large paragraph explaining the client’s style direction”;
- “image slot for a full-body example”;
- “small footer note for practical next steps”.

Descriptions should include enough context for an agent to make a placement
decision. `max_characters` is a layout constraint, not a semantic field name.

## Agent placement plan

The agent receives:

1. the structured, user-authored manual report;
2. the template manifest with page descriptions and field descriptions;
3. available local client image assets;
4. optional layout constraints such as character limits.

It returns a validated plan such as:

```json
{
  "assignments": [
    {
      "field_key": "field_001",
      "source_path": "title",
      "rationale": "The cover field is the best fit for the report title"
    },
    {
      "field_key": "field_014",
      "source_path": "alignment_summary",
      "rationale": "This page field is described as a longer positioning paragraph"
    },
    {
      "field_key": "image_001",
      "source_path": "assets.client_portrait",
      "rationale": "The page requests a portrait image"
    }
  ],
  "unplaced_source_paths": ["action_plan[2].body"]
}
```

The backend validates unknown fields, duplicate assignments, required fields,
missing content, image availability, and character limits before an Autofill
job can start. The agent may leave content unplaced; it must not invent or
rewrite the user's report text.

## Canva setup

Create the visual design in Canva and add Autofill fields with arbitrary stable
technical keys. Then provide the resulting template ID and the page/field
descriptions so the manifest can be completed. The Canva dataset API exposes
the available field keys and types; the human descriptions are kept in this
manifest because they are application-level placement guidance.

The planned runtime is:

```text
Manual report + local assets
        ↓
Agent placement plan
        ↓
Validation against template manifest
        ↓
Upload selected assets
        ↓
Canva Autofill job
        ↓
Design URL for final human review in Canva
```

No Canva credentials, template IDs, or client assets belong in the repository.
