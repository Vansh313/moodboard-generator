import os, uuid, requests, time, base64

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

ANGLE_PROMPTS = [
    "Wide angle shot of the full room showing all furniture and materials, interior design photography, natural lighting, photorealistic",
    "Zoomed in on the sofa and coffee table area, warm lighting, photorealistic interior photography, shallow depth of field",
    "Close-up detail shot of the flooring texture and lower furniture legs, material detail, photorealistic",
    "View of the storage wall and cabinetry, showing shelving details and decorative objects, photorealistic interior",
    "Window corner shot showing natural light, curtains, and ambient mood, golden hour lighting, photorealistic",
    "Dining area perspective looking toward the living space, showing the full room depth, photorealistic",
]

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
        "input": {
            "prompt": prompt,
            "input_image_1": image_url_1,
            "input_image_2": image_url_2,
            "aspect_ratio": "4:3",
            "output_format": "jpg"
        }
    }
    try:
        r = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        pred_id = r.json()["id"]
        print(f"Kontext submitted: {pred_id}")
        for _ in range(60):
            time.sleep(3)
            poll = requests.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers={"Authorization": f"Token {REPLICATE_KEY}"}, timeout=15
            )
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

def download_image(url, index):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        fp = os.path.join(TEMP_DIR, f"render_{index}_{uuid.uuid4().hex[:6]}.jpg")
        with open(fp, "wb") as f:
            f.write(r.content)
        print(f"Saved render {index}: {fp} ({len(r.content)} bytes)")
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

    print(f"\n=== GENERATING BASE ROOM from {len(reference_paths)} references ===")

    # Convert all references to base64
    image_urls = []
    for path in reference_paths:
        if path and os.path.exists(path):
            url = encode_image_base64(path)
            if url:
                image_urls.append(url)

    if len(image_urls) < 2:
        print("Not enough images")
        return None

    # Pass 1: Generate base room from first 2 references
    print(f"\n--- Pass 1: Building base room ---")
    base_prompt = f"Create a photorealistic interior room incorporating the furniture, textures and materials from both reference images. {room_prompt}. Wide angle, professional interior design photography, natural lighting."
    base_url = run_kontext_pass(image_urls[0], image_urls[1], base_prompt)
    if not base_url:
        print("Base room generation failed")
        return None

    base_path = download_image(base_url, 0)
    if not base_path:
        return None

    # Pass 2+: Incorporate remaining reference images into base room
    current_path = base_path
    current_url = base_url
    for i, ref_url in enumerate(image_urls[2:], start=2):
        print(f"\n--- Pass {i}: Adding reference {i+1} ---")
        current_data_url = encode_image_base64(current_path)
        if not current_data_url:
            break
        prompt_n = f"Refine this interior room to incorporate the furniture or material from the second reference image. Keep all existing elements. {room_prompt}. Photorealistic interior design photography."
        new_url = run_kontext_pass(current_data_url, ref_url, prompt_n)
        if not new_url:
            break
        new_path = download_image(new_url, i)
        if new_path:
            current_path = new_path
            current_url = new_url

    print(f"\nBase room complete: {current_path}")
    return current_path, current_url

def generate_room_angles(reference_paths, room_prompt):
    """
    Generate 6 different angle renders of the same room.
    Returns list of 6 image paths.
    """
    if not reference_paths or len(reference_paths) < 2:
        return []
    if not REPLICATE_KEY:
        print("No REPLICATE_KEY")
        return []

    result = generate_composite_room(reference_paths, room_prompt)
    if not result:
        return []

    base_path, base_url = result
    render_paths = [base_path]  # Slot 1 = wide angle base room

    base_data_url = encode_image_base64(base_path)
    if not base_data_url:
        return render_paths

    # Generate 5 more angles from the base room
    for i, angle_prompt in enumerate(ANGLE_PROMPTS[1:3], start=1):
        print(f"\n--- Angle {i+1}: {angle_prompt[:50]}... ---")
        full_prompt = f"This is the same room. {angle_prompt}. Same materials: {room_prompt}. Keep all design elements consistent."
        angle_url = run_kontext_pass(base_data_url, base_data_url, full_prompt)
        if angle_url:
            angle_path = download_image(angle_url, f"angle_{i}")
            if angle_path:
                render_paths.append(angle_path)
                print(f"Angle {i+1} saved")
        else:
            print(f"Angle {i+1} failed, skipping")

    print(f"\nGenerated {len(render_paths)} room renders")
    return render_paths


HF_API_KEY = os.environ.get("HF_API_KEY", "")

def generate_hf_image(prompt, index=0):
    """Generate image using Hugging Face Inference API - free tier."""
    if not HF_API_KEY:
        print("No HF_API_KEY")
        return None
    try:
        url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": prompt, "parameters": {"width": 768, "height": 512, "num_inference_steps": 20}}
        print(f"HF render {index}: {prompt[:60]}...")
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            fp = os.path.join(TEMP_DIR, f"hf_{index}_{uuid.uuid4().hex[:6]}.jpg")
            with open(fp, "wb") as f:
                f.write(r.content)
            print(f"HF saved: {fp} ({len(r.content)} bytes)")
            return fp
        else:
            print(f"HF error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"HF error: {e}")
        return None

HF_PROMPTS = [
    "photorealistic interior living room, sofa and coffee table detail, warm ivory and brass tones, European contemporary, professional photography",
    "photorealistic interior close-up flooring and furniture detail, marble and oak textures, warm lighting, interior design photography",
    "photorealistic interior cabinet and shelving wall, fluted glass panels, brass hardware, European luxury style, interior photography",
    "photorealistic interior window corner, natural light, linen curtains, golden hour, warm ivory room, interior design photography",
    "photorealistic interior dining area, European contemporary style, warm ivory and brass, wide angle, interior design photography",
]

def generate_supporting_renders(base_room_path, room_prompt, count=5):
    """Generate supporting room renders using HuggingFace."""
    renders = []
    style = f"photorealistic interior design photography, {room_prompt}, European contemporary, warm ivory and brass tones, professional lighting"
    for i in range(min(count, len(HF_PROMPTS))):
        print(f"
--- HF render {i+1} ---")
        full_prompt = f"{HF_PROMPTS[i]}. {style}"
        path = generate_hf_image(full_prompt, index=i)
        if path:
            renders.append(path)
        else:
            print(f"HF render {i+1} failed")
    print(f"Generated {len(renders)} HF renders")
    return renders
