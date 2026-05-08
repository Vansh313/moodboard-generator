import os
import uuid
import requests
import fal_client

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_single_image(prompt: str, index: int) -> str:
    """Generate a single image via fal.ai Flux Dev and return local file path."""

    result = fal_client.subscribe(
        "fal-ai/flux/dev",
        arguments={
            "prompt": prompt,
            "image_size": "landscape_4_3",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
        }
    )

    image_url = result["images"][0]["url"]

    # Download image
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()

    filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
    filepath = os.path.join(TEMP_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(response.content)

    return filepath


def generate_images(prompts: list) -> list:
    """Generate all 6 moodboard images. Returns list of local file paths."""

    image_paths = []

    for i, prompt in enumerate(prompts):
        try:
            print(f"Generating image {i+1}/6...")
            path = generate_single_image(prompt, i)
            image_paths.append(path)
        except Exception as e:
            print(f"Image {i+1} failed: {e}")
            # Use placeholder path — pdf_builder handles missing images gracefully
            image_paths.append(None)

    return image_paths
