import anthropic
import base64
import os
import json

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def encode_image(image_path: str) -> tuple:
    try:
        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        if ext == "png": media_type = "image/png"
        elif ext == "webp": media_type = "image/webp"
        else: media_type = "image/jpeg"
        return data, media_type
    except Exception as e:
        print(f"Image encode error: {e}")
        return None, None

def analyze_reference_images(image_paths: list) -> list:
    if not image_paths:
        return []
    captions = []
    for i, path in enumerate(image_paths):
        if not path or not os.path.exists(path):
            captions.append(f"CLIENT REFERENCE {i+1}")
            continue
        data, media_type = encode_image(path)
        if not data:
            captions.append(f"CLIENT REFERENCE {i+1}")
            continue
        try:
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                        {"type": "text", "text": "In 3-5 words, describe what this interior design reference shows. Examples: 'Marble floor texture', 'Beige linen sofa', 'Brass pendant light'. Be specific and concise."}
                    ]
                }]
            )
            caption = response.content[0].text.strip().upper()
            captions.append(caption)
            print(f"Image {i+1} identified: {caption}")
        except Exception as e:
            print(f"Vision error {i+1}: {e}")
            captions.append(f"CLIENT REFERENCE {i+1}")
    return captions

def generate_room_composite_prompt(form: dict, reference_captions: list) -> str:
    """Generate a detailed prompt for Flux Kontext composite room generation."""
    elements = ", ".join(reference_captions) if reference_captions else ""
    prompt = f"{form.get('design_style', 'modern')} interior room"
    if form.get("room_types"):
        prompt = f"{form.get('design_style', 'modern')} {form.get('room_types', 'living room')}"
    if form.get("color_prefs"):
        prompt += f", color palette: {form.get('color_prefs', '')}"
    if form.get("mood_feel"):
        prompt += f", mood: {form.get('mood_feel', '')}"
    if elements:
        prompt += f", featuring: {elements}"
    return prompt

def generate_moodboard_content(form: dict) -> dict:
    has_references = form.get("has_reference_images", False)
    ref_count = form.get("reference_image_count", 0)
    ai_slots = max(0, 6 - ref_count - (1 if has_references else 0))  # -1 for composite hero

    prompt = f"""You are an expert interior design consultant creating a moodboard brief.

Client: {form.get('client_name', '')}
Project: {form.get('project_name', '')}
Rooms: {form.get('room_types', '')}
Style: {form.get('design_style', '')}
Colors: {form.get('color_prefs', '')}
Materials: {form.get('materials', '')}
Mood: {form.get('mood_feel', '')}
Budget: {form.get('budget_range', '')}
{"Note: Client has provided specific reference images. The moodboard will feature a composite room render plus their individual references." if has_references else ""}

Generate a moodboard brief in this EXACT JSON format:
{{
  "mood_title": "3-4 word evocative title",
  "tagline": "one line tagline under 12 words",
  "mood_description": "3-4 sentences describing the vision",
  "color_palette": [
    {{"hex": "#F5F1E8", "name": "Warm Ivory", "role": "Base"}},
    {{"hex": "#A8B5A0", "name": "Sage Green", "role": "Primary"}},
    {{"hex": "#D4A89A", "name": "Soft Terra", "role": "Accent"}},
    {{"hex": "#C9A96E", "name": "Muted Gold", "role": "Accent"}},
    {{"hex": "#B89E7E", "name": "Natural Oak", "role": "Neutral"}}
  ],
  "image_prompts": [],
  "materials_list": ["material 1", "material 2", "material 3", "material 4", "material 5", "material 6"],
  "designer_note": "warm personal note to client, 2-3 sentences"
}}

{"Generate 0 image_prompts since client references will fill all slots." if has_references and ai_slots == 0 else f"Generate {max(1, ai_slots)} detailed Flux image prompts for remaining slots."}
Return ONLY the JSON, no other text."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        content = json.loads(text)
        if "image_prompts" not in content:
            content["image_prompts"] = []
        return content
    except Exception as e:
        print(f"JSON parse error: {e}")
        return {
            "mood_title": "Design Vision",
            "tagline": "A space crafted with intention",
            "mood_description": f"A beautiful {form.get('design_style', 'modern')} space.",
            "color_palette": [
                {"hex": "#F5F1E8", "name": "Warm Ivory", "role": "Base"},
                {"hex": "#A8B5A0", "name": "Sage Green", "role": "Primary"},
                {"hex": "#D4A89A", "name": "Soft Terra", "role": "Accent"},
                {"hex": "#C9A96E", "name": "Muted Gold", "role": "Accent"},
                {"hex": "#B89E7E", "name": "Natural Oak", "role": "Neutral"}
            ],
            "image_prompts": [],
            "materials_list": ["Natural linen", "Raw oak", "Brushed brass", "Marble", "Washi paper", "Ceramic"],
            "designer_note": f"Dear {form.get('client_name', 'valued client')}, this moodboard captures your vision."
        }
