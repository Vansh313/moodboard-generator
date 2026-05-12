import os
import uuid
import requests
from urllib.parse import quote

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_single_image(prompt: str, index: int) -> str:
    """Generate a single image via Pollinations.ai (free, no API key) and return local file path."""

    # Truncate to 500 chars to avoid URL issues
    clean_prompt = prompt[:500].replace("\n", " ").strip()
    encoded_prompt = quote(clean_prompt)

    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true&enhance=true"

    try:
        response = requests.get(url, timeout=60)
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
    """Generate all 6 moodboard images. Returns list of local file paths."""

    image_paths = []

    for i, prompt in enumerate(prompts):
        print(f"Generating image {i+1}/6...")
        path = generate_single_image(prompt, i)
        image_paths.append(path)

    return image_paths
