import os
import uuid
import requests
import time
import base64

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REPLICATE_KEY = os.environ.get("REPLICATE_KEY", "")

def upload_image_to_replicate(image_path: str) -> str:
    """Upload a local image to Replicate and get a URL back."""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        
        # Convert to base64 data URI
        ext = image_path.lower().split(".")[-1]
        mime = "image/png" if ext == "png" else "image/jpeg"
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def run_kontext_pass(image_url_1: str, image_url_2: str, prompt: str) -> str:
    """Run one pass of multi-image-kontext-pro. Returns output image URL."""
    headers = {
        "Authorization": f"Token {REPLICATE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": "flux-kontext-apps/multi-image-kontext-pro",
        "input": {
            "prompt": prompt,
            "input_image_1": image_url_1,
            "input_image_2": image_url_2,
            "aspect_ratio": "4:3",
            "output_format": "jpg",
        }
    }
    try:
        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            json=payload, headers=headers, timeout=30
        )
        r.raise_for_status()
        pred_id = r.json()["id"]
        print(f"Kontext pass submitted: {pred_id}")

        poll_headers = {"Authorization": f"Token {REPLICATE_KEY}"}
        for _ in range(60):
            time.sleep(3)
            poll = requests.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers=poll_headers, timeout=15
            )
            poll.raise_for_status()
            result = poll.json()
            status = result.get("status")
            print(f"Status: {status}")
            if status == "succeeded":
                output = result.get("output")
                if isinstance(output, list): return output[0]
                return output
            elif status == "failed":
                print(f"Failed: {result.get('error')}")
                return None
        return None
    except Exception as e:
        print(f"Kontext pass error: {e}")
        return None

def download_image_from_url(url: str, index: int) -> str:
    """Download an image from URL to local file."""
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

def generate_composite_room(reference_paths: list, room_prompt: str) -> str:
    """
    Chain multi-image-kontext-pro passes to incorporate all reference images.
    Returns path to final composite room image.
    """
    if not reference_paths:
        return None
    
    if len(reference_paths) == 1:
        # Only one reference — use flux-schnell with the reference as style
        return None  # Fall back to AI generation
    
    print(f"\n=== COMPOSITE GENERATION: {len(reference_paths)} references ===")
    
    # Convert all local images to base64 data URIs
    image_urls = []
    for path in reference_paths:
        if path and os.path.exists(path):
            url = upload_image_to_replicate(path)
            if url:
                image_urls.append(url)
    
    if len(image_urls) < 2:
        print("Not enough valid images for composite")
        return None
    
    # Pass 1: Combine first two references
    print(f"\n--- Pass 1: images 1 + 2 ---")
    prompt_1 = f"Create a photorealistic interior room that incorporates the furniture, textures, and materials shown in both reference images. {room_prompt}. Photorealistic, interior design photography, natural lighting."
    
    current_url = run_kontext_pass(image_urls[0], image_urls[1], prompt_1)
    if not current_url:
        print("Pass 1 failed")
        return None
    
    # Save pass 1 result
    current_path = download_image_from_url(current_url, 0)
    if not current_path:
        return None
    
    # Subsequent passes: incorporate remaining references one by one
    for i, ref_url in enumerate(image_urls[2:], start=2):
        print(f"\n--- Pass {i}: incorporating reference {i+1} ---")
        
        current_data_url = upload_image_to_replicate(current_path)
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
            current_url = new_url
    
    print(f"\nFinal composite saved: {current_path}")
    return current_path
