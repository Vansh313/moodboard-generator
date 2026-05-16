import anthropic
import base64
import os
import json

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def encode_image(image_path: str) -> tuple:
    """Encode image to base64 for Claude Vision."""
    try:
        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        media_type = "image/png" if ext == "png" else "image/jpeg"
        return data, media_type
    except Exception as e:
        print(f"Image encode error: {e}")
        return None, None

def analyze_reference_images(image_paths: list) -> list:
    """Use Claude Vision to analyze each reference image and identify what it is."""
    if not image_paths:
        return []
    
    captions = []
    for i, path in enumerate(image_paths):
        if not path or not os.path.exists(path):
            captions.append(f"Reference {i+1}")
            continue
        
        data, media_type = encode_image(path)
        if not data:
            captions.append(f"Reference {i+1}")
            continue
        
        try:
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": data}
                        },
                        {
                            "type": "text",
                            "text": "In 3-5 words, describe what this interior design reference shows. Examples: 'Marble floor texture', 'Beige linen sofa', 'Brass pendant light', 'Oak wood flooring'. Be specific and concise."
                        }
                    ]
                }]
            )
            caption = response.content[0].text.strip()
            captions.append(caption.upper())
            print(f"Image {i+1} identified as: {caption}")
        except Exception as e:
            print(f"Vision analysis error for image {i+1}: {e}")
            captions.append(f"CLIENT REFERENCE {i+1}")
    
    return captions

def generate_moodboard_content(form: dict) -> dict:
    """Generate moodboard content using Claude."""
    
    has_references = form.get("has_reference_images", False)
    ref_count = form.get("reference_image_count", 0)
    ai_slots = max(0, 6 - ref_count)
    
    prompt = f"""You are an expert interior design consultant creating a moodboard brief.

Client: {form.get('client_name', '')}
Project: {form.get('project_name', '')}
Rooms: {form.get('room_types', '')}
Style: {form.get('design_style', '')}
Colors: {form.get('color_prefs', '')}
Materials: {form.get('materials', '')}
Mood: {form.get('mood_feel', '')}
Budget: {form.get('budget_range', '')}
{"Note: Client has provided " + str(ref_count) + " specific reference images that will be used directly in the moodboard." if has_references else ""}

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
  "image_prompts": {json.dumps([f"prompt {i+1}" for i in range(ai_slots)])},
  "materials_list": ["material 1", "material 2", "material 3", "material 4", "material 5", "material 6"],
  "designer_note": "warm personal note to client, 2-3 sentences"
}}

For image_prompts, generate {ai_slots} detailed Flux image generation prompts for interior photography.
Each prompt should be 20-30 words describing a specific interior scene matching the style.
Return ONLY the JSON, no other text."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    
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
            "mood_description": f"A beautiful {form.get('design_style', 'modern')} space designed for {form.get('client_name', 'the client')}.",
            "color_palette": [
                {"hex": "#F5F1E8", "name": "Warm Ivory", "role": "Base"},
                {"hex": "#A8B5A0", "name": "Sage Green", "role": "Primary"},
                {"hex": "#D4A89A", "name": "Soft Terra", "role": "Accent"},
                {"hex": "#C9A96E", "name": "Muted Gold", "role": "Accent"},
                {"hex": "#B89E7E", "name": "Natural Oak", "role": "Neutral"}
            ],
            "image_prompts": [],
            "materials_list": ["Natural linen", "Raw oak", "Brushed brass", "Marble", "Washi paper", "Ceramic"],
            "designer_note": f"Dear {form.get('client_name', 'valued client')}, this moodboard captures your vision beautifully."
        }
