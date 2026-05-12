import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def generate_moodboard_content(form: dict) -> dict:
    """
    Call Claude to generate all moodboard text content + 6 image prompts.
    Returns a structured dict.
    """

    prompt = f"""You are an expert interior design consultant creating a luxury moodboard for a client.

Here are the project details:
- Client Name: {form['client_name']}
- Project Name: {form['project_name']}
- Designer: {form['designer_name']}
- Room Type(s): {form['room_types']}
- Design Style: {form['design_style']}
- Color Preferences: {form['color_prefs']}
- Materials/Textures: {form['materials']}
- Mood/Feel: {form['mood_feel']}
- Budget Range: {form['budget_range']}

Generate a complete moodboard content package. Return ONLY a valid JSON object with NO extra text or markdown, using this exact structure:

{{
  "mood_title": "A poetic 3-5 word title capturing the essence of this design (e.g. 'Warm Forest Minimalism')",
  "tagline": "A single evocative sentence, 10-15 words, that captures the feeling of this space",
  "mood_description": "A rich 3-4 sentence paragraph describing the overall mood and vision for this space. Use sensory language.",
  "color_palette": [
    {{"name": "Color Name", "hex": "#RRGGBB", "role": "Primary/Accent/Neutral/Base"}},
    {{"name": "Color Name", "hex": "#RRGGBB", "role": "Primary/Accent/Neutral/Base"}},
    {{"name": "Color Name", "hex": "#RRGGBB", "role": "Primary/Accent/Neutral/Base"}},
    {{"name": "Color Name", "hex": "#RRGGBB", "role": "Primary/Accent/Neutral/Base"}},
    {{"name": "Color Name", "hex": "#RRGGBB", "role": "Primary/Accent/Neutral/Base"}}
  ],
  "materials_list": [
    "Material or finish recommendation 1",
    "Material or finish recommendation 2",
    "Material or finish recommendation 3",
    "Material or finish recommendation 4",
    "Material or finish recommendation 5",
    "Material or finish recommendation 6"
  ],
  "designer_note": "A warm, professional 2-3 sentence note from the designer to the client about this moodboard and the vision behind it.",
  "image_prompts": [
    "Photorealistic interior photography, [main room type] wide shot, [design style] style, [colors], [materials], [mood], soft natural lighting, architectural digest quality, 4k",
    "Photorealistic interior photography, close-up of statement furniture piece, [design style], [materials], [colors], warm lighting, magazine quality",
    "Photorealistic texture detail shot, [materials] surface close-up, [colors], macro photography, luxury interior material, studio lighting",
    "Photorealistic interior photography, [mood] lighting atmosphere in [room type], [design style], golden hour light, [colors], cinematic",
    "Photorealistic interior styling detail, decorative accent objects, [design style], [colors], [materials], editorial photography style",
    "Photorealistic interior photography, color palette showcased in real space, [colors] tones, [design style], cohesive vignette shot"
  ]
}}

IMPORTANT for image_prompts: Replace all [placeholders] with actual specific details from the project. Each prompt must be a complete, detailed image generation prompt ready to send to an AI image generator. Make them vivid and specific."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    content = json.loads(raw)
    return content
