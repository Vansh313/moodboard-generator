import os
import uuid
import requests
import base64
import json

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

def encode_image_base64(image_path: str) -> tuple:
    """Encode image to base64."""
    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        if ext == "png":
            mime = "image/png"
        elif ext == "webp":
            mime = "image/webp"
        else:
            mime = "image/jpeg"
        return data, mime
    except Exception as e:
        print(f"Encode error: {e}")
        return None, None

def generate_composite_room(reference_paths: list, room_prompt: str) -> str:
    """
    Use Gemini to generate a composite room image incorporating all reference images.
    Returns path to generated image.
    """
    if not reference_paths:
        return None
    
    if not GEMINI_KEY:
        print("No GEMINI_API_KEY set")
        return None

    print(f"\n=== GEMINI COMPOSITE: {len(reference_paths)} references ===")

    # Build the parts list — images first, then the prompt
    parts = []

    # Add all reference images
    for i, path in enumerate(reference_paths[:10]):
        if not path or not os.path.exists(path):
            continue
        data, mime = encode_image_base64(path)
        if not data:
            continue
        parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": data
            }
        })
        print(f"Added reference image {i+1}: {os.path.basename(path)}")

    if not parts:
        print("No valid images to send")
        return None

    # Add the text prompt
    parts.append({
        "text": f"""You are an expert interior designer and architectural visualizer.

Using ALL the furniture, materials, textures, and design elements shown in the reference images above, create a single photorealistic interior room image.

Requirements:
- Include ALL the furniture pieces and decorative elements from the reference images, placed naturally in the room
- Apply the textures and materials shown (flooring, wall materials, etc.) to the room surfaces
- The room should be: {room_prompt}
- Style: photorealistic interior design photography, professional lighting, wide angle shot showing the full room
- Make it look like a real luxury interior design render, not an illustration
- Everything should feel cohesive and professionally designed

Generate the complete room image now."""
    })

    # Call Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["Text", "Image"]
        }
    }

    try:
        print("Sending to Gemini...")
        r = requests.post(url, json=payload, timeout=120)
        print(f"Gemini response status: {r.status_code}")
        
        if r.status_code != 200:
            print(f"Gemini error: {r.text[:300]}")
            return None

        response = r.json()
        
        # Extract image from response
        candidates = response.get("candidates", [])
        if not candidates:
            print("No candidates in response")
            return None

        parts_out = candidates[0].get("content", {}).get("parts", [])
        for part in parts_out:
            if "inlineData" in part:
                image_data = part["inlineData"].get("data", "")
                mime_type = part["inlineData"].get("mimeType", "image/png")
                ext = ".png" if "png" in mime_type else ".jpg"
                
                fp = os.path.join(TEMP_DIR, f"composite_gemini_{uuid.uuid4().hex[:8]}{ext}")
                with open(fp, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                size = os.path.getsize(fp)
                print(f"Gemini composite saved: {fp} ({size} bytes)")
                return fp

        print("No image found in Gemini response")
        print(f"Response preview: {str(response)[:300]}")
        return None

    except Exception as e:
        print(f"Gemini API error: {e}")
        return None
