import os
import uuid
import requests
from urllib.parse import quote

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_single_image(prompt: str, index: int) -> str:
    clean_prompt = prompt[:400].replace("\n", " ").strip()
    encoded_prompt = quote(clean_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"
    try:
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = os.path.join(TEMP_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Image {index+1} saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"Image {index+1} failed: {e}")
        return None


def generate_images(prompts: list) -> list:
    """Generate up to 6 images. Returns list of local file paths (None for failed)."""
    image_paths = []
    # Only use first 6 prompts
    for i, prompt in enumerate(prompts[:6]):
        print(f"Generating image {i+1}/{min(len(prompts), 6)}...")
        path = generate_single_image(prompt, i)
        image_paths.append(path)
    # Pad to 6 if fewer prompts
    while len(image_paths) < 6:
        image_paths.append(None)
    return image_paths
