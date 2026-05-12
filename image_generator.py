import os
import uuid
import requests
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

def generate_single_image(prompt: str, index: int) -> tuple:
    clean_prompt = prompt[:400].replace("\n", " ").strip()
    encoded_prompt = quote(clean_prompt)
    for attempt in range(3):
        seed = index * 10 + attempt
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true&seed={seed}&model=flux"
        try:
            print(f"Image {index+1} attempt {attempt+1}...")
            response = requests.get(url, timeout=55)
            response.raise_for_status()
            if len(response.content) < 5000:
                time.sleep(2)
                continue
            filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
            filepath = os.path.join(TEMP_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Image {index+1} saved: {filepath}")
            return (index, filepath)
        except Exception as e:
            print(f"Image {index+1} attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return (index, None)

def generate_images(prompts: list) -> list:
    results = [None] * 6
    prompts = prompts[:6]
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(generate_single_image, p, i): i for i, p in enumerate(prompts)}
        for future in as_completed(futures):
            idx, path = future.result()
            results[idx] = path
    while len(results) < 6:
        results.append(None)
    return results
