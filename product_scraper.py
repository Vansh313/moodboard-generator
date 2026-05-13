import os, uuid, requests, base64

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REMOVEBG_KEY = os.environ.get("REMOVEBG_KEY", "")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def remove_background(image_path):
    if not REMOVEBG_KEY:
        return image_path
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://demo.api4ai.cloud/img-bg-removal/v1/general/results",
                files={"image": f},
                headers={"Authorization": f"Bearer {REMOVEBG_KEY}"},
                timeout=30
            )
        if r.status_code == 200:
            try:
                resp = r.json()
                entities = resp.get("results", [{}])[0].get("entities", [{}])
                if entities:
                    b64 = entities[0].get("image", "")
                    if b64:
                        new_path = image_path.rsplit(".", 1)[0] + "_nobg.png"
                        with open(new_path, "wb") as f: f.write(base64.b64decode(b64))
                        print(f"BG removed: {new_path}")
                        return new_path
            except Exception as e:
                print(f"BG parse error: {e}")
        else:
            print(f"BG removal failed: {r.status_code}")
        return image_path
    except Exception as e:
        print(f"BG removal error: {e}")
        return image_path

def download_image(url, index):
    try:
        r = requests.get(url.strip(), headers=HEADERS, timeout=20)
        r.raise_for_status()
        if len(r.content) < 5000:
            print(f"Product {index+1}: image too small, skipping")
            return None
        ext = ".png" if "png" in url.lower() else ".jpg"
        fp = os.path.join(TEMP_DIR, f"product_{index}_{uuid.uuid4().hex[:6]}{ext}")
        with open(fp, "wb") as f: f.write(r.content)
        print(f"Product {index+1} image saved: {fp} ({len(r.content)} bytes)")
        return fp
    except Exception as e:
        print(f"Product {index+1} download error: {e}")
        return None

def scrape_product(url, index):
    if not url or not url.strip().startswith("http"):
        return None
    url = url.strip()
    print(f"Downloading product image {index+1}: {url[:60]}")
    image_path = download_image(url, index)
    if not image_path:
        return None
    clean_path = remove_background(image_path)
    return {
        "title": f"Product {index+1}",
        "price": "",
        "image_path": clean_path,
        "url": url,
        "is_product": True
    }

def scrape_all_products(urls):
    results = []
    for i, url in enumerate(urls[:6]):
        results.append(scrape_product(url.strip(), i) if url and url.strip() else None)
    return results
