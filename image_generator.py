import os
import uuid
import requests

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

UNSPLASH_KEY = os.environ.get("UNSPLASH_KEY", "")

SLOT_QUERIES = [
    "minimalist living room interior design",
    "modern sofa furniture interior",
    "marble wood texture detail interior",
    "warm cozy room lighting interior",
    "home decor vase plant styling",
    "neutral color palette interior design",
]

def download_image(url: str, index: int) -> str:
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = os.path.join(TEMP_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Image {index+1} saved")
        return filepath
    except Exception as e:
        print(f"Image {index+1} download failed: {e}")
        return None

def fetch_unsplash_image(query: str, index: int, style: str = "") -> str:
    full_query = f"{query} {style}".strip()[:100]
    url = "https://api.unsplash.com/photos/random"
    params = {"query": full_query, "orientation": "landscape", "content_filter": "high"}
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return download_image(data["urls"]["regular"], index)
    except Exception as e:
        print(f"Unsplash {index+1} failed: {e}")
        return None

def generate_images(prompts: list, form: dict = None) -> list:
    style = form.get("design_style", "") if form else ""
    results = []
    for i, query in enumerate(SLOT_QUERIES):
        print(f"Fetching image {i+1}/6...")
        path = fetch_unsplash_image(query, i, style)
        results.append(path)
    while len(results) < 6:
        results.append(None)
    return results
