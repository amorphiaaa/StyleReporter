"""Few-shot form reference for the client-facing style report.

The reference intentionally contains no style diagnosis. It teaches the model
the report's structure and sentence movement without giving it qualities that
could be hallucinated for a new client.
"""

STYLE_REPORT_FEW_SHOT_REFERENCE = """
FEW-SHOT FORM REFERENCE — STRUCTURE AND LANGUAGE ONLY

The bracketed text is placeholder text, not client evidence. Copy the
organization, directness, and reasoning order; replace every placeholder from
TARGET CLIENT DATA. Never copy a quality, problem, desire, item, or
recommendation from this reference.

title:
[Memorable two-to-four-word Style Language name]

alignment_summary:
You are naturally drawn to [supported style direction]. [Two or three broad
visual qualities] already play an important role in your style. However, you
have learned to express this side of yourself cautiously, relying on familiar
choices that feel comfortable but no longer exciting. What you are looking for
is not a completely different style. It is the confidence to make
[supported quality] a more visible and intentional part of your everyday
outfits.

current_style_language:
- [authentic quality]
- [current state]
- [current state]
- [current state]

desired_style_language:
- [same authentic quality]
- [desired movement]
- [desired movement]
- [desired movement]

disconnect:
Your wardrobe already reflects [authentic quality], but it does not fully
express [under-expressed quality]. You are naturally drawn to [supported broad
qualities], yet you often [observed current behaviour]. As a result,
[concrete effect in the client's experience]. Your next step is not
[unsupported reinvention]; it is [evidence-based evolution] while keeping
[authentic quality] that already feels like you.

style_language_summary:
This is a [Style Language name] style language: [plain description of the
coherent direction]. The aim is not to become [unsupported extreme]. It is to
let [supported quality] become easier to see while keeping [supported quality]
that already feels authentic.

your_action_plan:
1. [Clear principle]
   [Why this matters for this client]. Apply it through [reusable report
   method] so [practical effect].
2. [Clear principle]
   [Why this matters for this client]. Apply it through [reusable report
   method] so [practical effect].
3. [Clear principle]
   [Why this matters for this client]. Apply it through [reusable report
   method] so [practical effect].

evidence:
- [Synthesised observation supported by the target data]

limitations:
- [Missing or uncertain information]
""".strip()
