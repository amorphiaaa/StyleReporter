"""Redacted few-shot reference for the client-facing style report.

This example is adapted from the supplied reference portfolio. It preserves
the reasoning order and voice, but contains no client name, contact details,
image URLs, or client-specific wardrobe facts. It is a style exemplar only;
the model must derive every fact in a new report from the target submission.
"""

STYLE_REPORT_FEW_SHOT_REFERENCE = """
FEW-SHOT REFERENCE REPORT (REDACTED STYLE EXEMPLAR ONLY)

Use this example to learn the voice, level of specificity, reasoning order,
and shape of the client-facing answer. Do not copy its facts, identity,
visual observations, title, or exact style terms unless the target evidence
supports them. The target client below is the only source of truth.

title:
Feminine Creative Ease

alignment_summary:
You are naturally drawn to femininity with a creative touch. Soft shapes,
beautiful colour, and thoughtful detail already play an important role in your
style. However, you have learned to express this side of yourself cautiously,
relying on familiar combinations that feel comfortable but no longer exciting.
What you are looking for is not a completely different style. It is the
confidence to make your creative side a more visible and intentional part of
your everyday outfits.

current_style_language:
- Feminine
- Practical
- Soft
- Safe
- Under-expressive

desired_style_language:
- Feminine
- Creative
- Confident
- Intentional
- Individual

disconnect:
Your wardrobe already reflects your feminine nature, but it does not fully
express your creative personality. You are naturally drawn to expressive
colour, interesting texture, and details with character, yet you often stop
short of letting those qualities lead the whole impression. As a result, your
style can feel softer than your personality and more practical than inspiring.
Your next step is not becoming more feminine. It is bringing more individuality
and creativity into your wardrobe while keeping the comfort and ease that
already feel authentically you.

style_language_summary:
This is a feminine style language with room to breathe. It feels soft and
wearable, but never anonymous: colour, texture, pattern, or a thoughtful detail
gives the look a clear point of view. The aim is not to become louder or trendier.
It is to let the creative side already present become easier to see while
keeping the comfort and warmth that make the wardrobe feel like you.

style_language_anchors:
- Softness
- Creativity
- Confidence

your_action_plan:
1. FOLLOW THE OUTFIT FORMULAS BEFORE TRYING TO INVENT YOUR OWN.
   Right now, the challenge is not a lack of beautiful clothes. It is knowing
   how to combine them. Start with the outfit formulas in the report, choose
   the main visual idea for the look, let one element lead, and keep the
   surrounding choices simple. This builds confidence without creating more
   decisions.

2. INTRODUCE COLOUR WITH INTENTION.
   Begin with one expressive colour and let the rest of the look support it
   calmly. As confidence grows, combine more than one accent only when the
   relationship between them is clear. The point is not to wear more colour;
   it is to make colour feel like a deliberate part of your expression.

3. FINISH EVERY OUTFIT WITH ONE STYLING LAYER.
   Before an outfit feels complete, add one layer of texture, shape, movement,
   or detail that connects the separate choices. This gives a simple look more
   intention and personality without making it feel overworked.

evidence:
- Repeated questionnaire and image signals should be synthesised into a few
  concrete observations rather than copied as an inventory.

limitations:
- State missing lifestyle, wardrobe, image, or occasion information instead
  of filling it with assumptions.
""".strip()
