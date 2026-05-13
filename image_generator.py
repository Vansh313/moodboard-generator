import os
import uuid
import requests
import time

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def generate_single_image(prompt: str, index: int) -> tuple:
    headers = {
        "Authorization": f"Token {REPLICATE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": "black-forest-labs/flux-schnell",
        "input": {
            "prompt": prompt[:400],
            "num_outputs": 1,
            "aspect_ratio": "4:3",
            "output_format": "jpg",
            "output_quality": 85
        }
    }
    try:
        resp = requests.post(
            "https://api.replicate.com/v1/predictions",
            json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()
        pred = resp.json()
        pred_id = pred["id"]
        print(f"Image {index+1} submitted: {pred_id}")
        poll_headers = {"Authorization": f"Token {REPLICATE_KEY}"}
        for attempt in range(40):
            time.sleep(2)
            poll = requests.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers=poll_headers, timeout=15
            )
            poll.raise_for_status()
            result = poll.json()
            status = result.get("status")
            print(f"Image {index+1} poll {attempt+1}: {status}")
            if status == "succeeded":
                output = result.get("output")
                if not output:
                    return (index, None)
                img_url = output[0] if isinstance(output, list) else output
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()
                filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
                filepath = os.path.join(TEMP_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)
                print(f"Image {index+1} saved ({len(img_resp.content)} bytes)")
                return (index, filepath)
            elif status == "failed":
                print(f"Image {index+1} failed: {result.get('error')}")
                return (index, None)
        return (index, None)
    except Exception as e:
        print(f"Image {index+1} exception: {e}")
        return (index, None)

def generate_images(prompts: list, form: dict = None) -> list:
    results = [None] * 6
    for i, prompt in enumerate(prompts[:6]):
        print(f"\n--- Generating image {i+1}/6 ---")
        idx, path = generate_single_image(prompt, i)
        results[idx] = path
        time.sleep(2)
    success = sum(1 for r in results if r is not None)
    print(f"\nTotal images: {success}/6")
    while len(results) < 6:
        results.append(None)
    return results
