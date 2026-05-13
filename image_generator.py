import os
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def generate_single_image(prompt: str, index: int) -> tuple:
    headers = {
        "Authorization": f"Token {REPLICATE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "version": "black-forest-labs/flux-schnell",
        "input": {
            "prompt": prompt,
            "num_outputs": 1,
            "aspect_ratio": "4:3",
            "output_format": "jpg",
            "output_quality": 90
        }
    }
    try:
        resp = requests.post("https://api.replicate.com/v1/predictions",
                           json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        prediction = resp.json()
        pred_id = prediction["id"]

        # Poll for result
        for _ in range(30):
            import time
            time.sleep(2)
            poll = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                              headers=headers, timeout=15)
            poll.raise_for_status()
            result = poll.json()
            if result["status"] == "succeeded":
                img_url = result["output"][0]
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()
                filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
                filepath = os.path.join(TEMP_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)
                print(f"Image {index+1} saved: {filepath}")
                return (index, filepath)
            elif result["status"] == "failed":
                print(f"Image {index+1} failed: {result.get('error')}")
                return (index, None)
        return (index, None)
    except Exception as e:
        print(f"Image {index+1} error: {e}")
        return (index, None)

def generate_images(prompts: list, form: dict = None) -> list:
    results = [None] * 6
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(generate_single_image, p, i): i
                   for i, p in enumerate(prompts[:6])}
        for future in as_completed(futures):
            idx, path = future.result()
            results[idx] = path
    success = sum(1 for r in results if r is not None)
    print(f"Images generated: {success}/6")
    while len(results) < 6:
        results.append(None)
    return results
