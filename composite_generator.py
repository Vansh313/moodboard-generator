import os
import uuid
import requests
import base64
import json

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

def encode_image_base64(image_path: str) -> tuple:
    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        if ext == "png": mime = "image/png"
        elif ext == "webp": mime = "image/webp"
        else: mime = "image/jpeg"
        return data, mime
    except Exception as e:
        print(f"Encode error: {e}")
        return None, None

def generate_composite_room(reference_paths: list, room_prompt: str) -> str:
    if not reference_paths:
        return None
    if not GEMINI_KEY:
        print("No GEMINI_API_KEY")
        return None

    print(f"\n=== GEMINI COMPOSITE: {len(reference_paths)} references ===")

    parts = []
    for i, path in enumerate(reference_paths[:6]):
        if not path or not os.path.exists(path):
            continue
        data, mime = encode_image_base64(path)
        if not data:
            continue
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
        print(f"Added image {i+1}: {os.path.basename(path)}")

    if not parts:
        print("No valid images")
        return None

    parts.append({"text": f"""You are an expert interior designer and 3D visualizer.

Using the furniture pieces, materials, and textures shown in the reference images, create a single photorealistic interior room render.

Place ALL the furniture and apply ALL the materials/textures shown into one cohesive room.
Room type and style: {room_prompt}
Make it look like a professional interior design render - photorealistic, wide angle, beautiful lighting.

Generate the room image now."""})

    # Try models in order
    models = [
        "gemini-3.1-flash-image-preview",
        "gemini-3-pro-image-preview", 
        "gemini-2.5-flash-image",
    ]

    for model in models:
        print(f"Trying model: {model}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["Text", "Image"]}
        }
        try:
            r = requests.post(url, json=payload, timeout=180)
            print(f"Status: {r.status_code}")
            
            if r.status_code == 200:
                response = r.json()
                candidates = response.get("candidates", [])
                if not candidates:
                    print("No candidates")
                    continue
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
                        print(f"Composite saved: {fp} ({size} bytes)")
                        return fp
                print(f"No image in response from {model}")
            else:
                print(f"Error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"Exception with {model}: {e}")
            continue

    print("All Gemini models failed")
    return None
