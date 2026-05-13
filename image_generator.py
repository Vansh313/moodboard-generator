import os, uuid, requests, time

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def generate_one(prompt, index):
    headers = {"Authorization": f"Token {REPLICATE_KEY}", "Content-Type": "application/json"}
    payload = {"version": "black-forest-labs/flux-schnell", "input": {"prompt": prompt[:400], "num_outputs": 1, "aspect_ratio": "4:3", "output_format": "jpg", "output_quality": 85}}
    for attempt in range(3):
        try:
            r = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers, timeout=30)
            if r.status_code == 429:
                print(f"Image {index+1} rate limited, waiting 15s...")
                time.sleep(15)
                continue
            r.raise_for_status()
            pid = r.json()["id"]
            print(f"Image {index+1} submitted: {pid}")
            for _ in range(50):
                time.sleep(2)
                p = requests.get(f"https://api.replicate.com/v1/predictions/{pid}", headers={"Authorization": f"Token {REPLICATE_KEY}"}, timeout=15)
                p.raise_for_status()
                res = p.json()
                if res["status"] == "succeeded":
                    url = res["output"][0] if isinstance(res["output"], list) else res["output"]
                    img = requests.get(url, timeout=30)
                    img.raise_for_status()
                    fp = os.path.join(TEMP_DIR, f"img_{index}_{uuid.uuid4().hex[:6]}.jpg")
                    with open(fp, "wb") as f: f.write(img.content)
                    print(f"Image {index+1} saved ({len(img.content)} bytes)")
                    return fp
                elif res["status"] == "failed":
                    print(f"Image {index+1} prediction failed")
                    return None
            return None
        except Exception as e:
            print(f"Image {index+1} attempt {attempt+1} error: {e}")
            time.sleep(5)
    return None

def generate_images(prompts, form=None):
    results = []
    for i, prompt in enumerate(prompts[:6]):
        print(f"\n--- Image {i+1}/6 ---")
        path = generate_one(prompt, i)
        results.append(path)
        if i < 5:
            print(f"Waiting 8s before next...")
            time.sleep(8)
    print(f"\nDone: {sum(1 for r in results if r)}/6")
    while len(results) < 6: results.append(None)
    return results
