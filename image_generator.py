import os
import uuid
import requests
import time

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def submit_prediction(prompt: str, index: int):
    headers = {"Authorization": f"Token {REPLICATE_KEY}", "Content-Type": "application/json"}
    payload = {"version": "black-forest-labs/flux-schnell", "input": {"prompt": prompt[:400], "num_outputs": 1, "aspect_ratio": "4:3", "output_format": "jpg", "output_quality": 85}}
    try:
        resp = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        pred_id = resp.json()["id"]
        print(f"Image {index+1} submitted: {pred_id}")
        return pred_id
    except Exception as e:
        print(f"Image {index+1} submit failed: {e}")
        return None

def download_image(img_url: str, index: int):
    try:
        img_resp = requests.get(img_url, timeout=30)
        img_resp.raise_for_status()
        filename = f"img_{index}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = os.path.join(TEMP_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(img_resp.content)
        print(f"Image {index+1} saved ({len(img_resp.content)} bytes)")
        return filepath
    except Exception as e:
        print(f"Image {index+1} download failed: {e}")
        return None

def generate_images(prompts: list, form: dict = None) -> list:
    prompts = prompts[:6]
    results = [None] * 6
    poll_headers = {"Authorization": f"Token {REPLICATE_KEY}"}

    # Submit all with 2s gap
    pred_ids = {}
    for i, prompt in enumerate(prompts):
        pid = submit_prediction(prompt, i)
        if pid:
            pred_ids[i] = pid
        time.sleep(2)

    print(f"Submitted {len(pred_ids)}/6. Polling...")

    # Poll all together
    pending = dict(pred_ids)
    for round_num in range(45):
        if not pending:
            break
        time.sleep(2)
        done = []
        for idx, pid in pending.items():
            try:
                poll = requests.get(f"https://api.replicate.com/v1/predictions/{pid}", headers=poll_headers, timeout=15)
                poll.raise_for_status()
                result = poll.json()
                status = result.get("status")
                if status == "succeeded":
                    output = result.get("output")
                    if output:
                        img_url = output[0] if isinstance(output, list) else output
                        results[idx] = download_image(img_url, idx)
                    done.append(idx)
                elif status == "failed":
                    print(f"Image {idx+1} failed")
                    done.append(idx)
            except Exception as e:
                print(f"Poll error img {idx+1}: {e}")
        for idx in done:
            pending.pop(idx)
        print(f"Round {round_num+1}: {sum(1 for r in results if r)}/6 done, {len(pending)} pending")

    print(f"Final: {sum(1 for r in results if r)}/6 images")
    return results
