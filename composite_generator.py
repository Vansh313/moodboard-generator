import os, uuid, requests, time, base64

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def encode_image_base64(image_path):
    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        mime = {"png":"image/png","webp":"image/webp"}.get(ext,"image/jpeg")
        return f"data:{mime};base64,{data}"
    except Exception as e:
        print(f"Encode error: {e}")
        return None

def run_kontext_pass(image_url_1, image_url_2, prompt):
    headers = {"Authorization": f"Token {REPLICATE_KEY}", "Content-Type": "application/json"}
    payload = {
        "version": "flux-kontext-apps/multi-image-kontext-pro",
        "input": {"prompt": prompt, "input_image_1": image_url_1, "input_image_2": image_url_2, "aspect_ratio": "4:3", "output_format": "jpg"}
    }
    try:
        r = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        pred_id = r.json()["id"]
        print(f"Kontext pass submitted: {pred_id}")
        for _ in range(60):
            time.sleep(3)
            poll = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers={"Authorization": f"Token {REPLICATE_KEY}"}, timeout=15)
            result = poll.json()
            status = result.get("status")
            print(f"Status: {status}")
            if status == "succeeded":
                output = result.get("output")
                return output[0] if isinstance(output, list) else output
            elif status == "failed":
                print(f"Failed: {result.get('error')}")
                return None
    except Exception as e:
        print(f"Kontext error: {e}")
    return None

def download_image_from_url(url, index):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        fp = os.path.join(TEMP_DIR, f"composite_{index}_{uuid.uuid4().hex[:6]}.jpg")
        with open(fp, "wb") as f:
            f.write(r.content)
        print(f"Downloaded composite: {fp} ({len(r.content)} bytes)")
        return fp
    except Exception as e:
        print(f"Download error: {e}")
        return None

def generate_composite_room(reference_paths, room_prompt):
    if not reference_paths or len(reference_paths) < 2:
        return None
    if not REPLICATE_KEY:
        print("No REPLICATE_KEY")
        return None

    print(f"\n=== FLUX KONTEXT COMPOSITE: {len(reference_paths)} references ===")

    image_urls = []
    for path in reference_paths:
        if path and os.path.exists(path):
            url = encode_image_base64(path)
            if url:
                image_urls.append(url)

    if len(image_urls) < 2:
        print("Not enough images")
        return None

    print(f"\n--- Pass 1: images 1 + 2 ---")
    prompt_1 = f"Create a photorealistic interior room that incorporates the furniture, textures, and materials shown in both reference images. {room_prompt}. Photorealistic, interior design photography, natural lighting."
    current_url = run_kontext_pass(image_urls[0], image_urls[1], prompt_1)
    if not current_url:
        return None

    current_path = download_image_from_url(current_url, 0)
    if not current_path:
        return None

    for i, ref_url in enumerate(image_urls[2:], start=2):
        print(f"\n--- Pass {i}: incorporating reference {i+1} ---")
        current_data_url = encode_image_base64(current_path)
        if not current_data_url:
            break
        prompt_n = f"Refine this interior room to also incorporate the furniture, texture, or material shown in the second reference image. Keep everything already in the room. {room_prompt}. Photorealistic, interior design photography."
        new_url = run_kontext_pass(current_data_url, ref_url, prompt_n)
        if not new_url:
            print(f"Pass {i} failed, keeping previous result")
            break
        new_path = download_image_from_url(new_url, i)
        if new_path:
            current_path = new_path

    print(f"\nFinal composite: {current_path}")
    return current_path
