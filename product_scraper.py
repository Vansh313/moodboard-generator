import os, uuid, requests, re, base64
from urllib.parse import urlparse

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REMOVEBG_KEY = os.environ.get("REMOVEBG_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def get_domain(url):
    try: return urlparse(url).netloc.lower().replace("www.", "")
    except: return ""

def extract_og_image(html):
    for pat in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m: return m.group(1)
    return ""

def extract_og_title(html):
    for pat in [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r'<title>([^<]+)</title>',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m: return m.group(1).strip()[:80]
    return ""

def scrape_amazon(url):
    # Clean URL to just dp page
    match = re.search(r'/dp/([A-Z0-9]+)', url)
    if match:
        asin = match.group(1)
        url = f"https://www.amazon.com/dp/{asin}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        # Try Amazon-specific image patterns first
        img_url = ""
        for pat in [
            r'"large":"(https://m\.media-amazon\.com/images/[^"]+)"',
            r'"hiRes":"(https://[^"]+)"',
            r'data-old-hires="(https://[^"]+)"',
            r'"imageURL":"(https://m\.media-amazon\.com/images/[^"]+)"',
        ]:
            m = re.search(pat, html)
            if m: img_url = m.group(1); break
        # Fallback to OG image
        if not img_url:
            img_url = extract_og_image(html)
        title = ""
        t = re.search(r'<span id="productTitle"[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL)
        if t: title = t.group(1).strip()[:80]
        if not title: title = extract_og_title(html)
        price = ""
        for pat in [r'<span class="a-price-whole">([\d,]+)</span>', r'"priceAmount":([\d.]+)']:
            p = re.search(pat, html)
            if p: price = f"${p.group(1)}"; break
        return {"title": title, "price": price, "image_url": img_url}
    except Exception as e:
        print(f"Amazon scrape error: {e}")
        return {}

def scrape_generic(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text
        return {
            "title": extract_og_title(html),
            "price": "",
            "image_url": extract_og_image(html)
        }
    except Exception as e:
        print(f"Generic scrape error: {e}")
        return {}

def remove_background(image_path):
    if not REMOVEBG_KEY:
        print("No REMOVEBG_KEY, skipping")
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
                print(f"BG removal parse error: {e}")
            return image_path
        else:
            print(f"BG removal failed: {r.status_code}")
            return image_path
    except Exception as e:
        print(f"BG removal error: {e}")
        return image_path

def download_product_image(image_url, index):
    try:
        r = requests.get(image_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        ext = ".png" if "png" in image_url.lower() else ".jpg"
        fp = os.path.join(TEMP_DIR, f"product_{index}_{uuid.uuid4().hex[:6]}{ext}")
        with open(fp, "wb") as f: f.write(r.content)
        print(f"Product image saved: {fp} ({len(r.content)} bytes)")
        return fp
    except Exception as e:
        print(f"Product download error: {e}")
        return None

def scrape_product(url, index):
    if not url or not url.strip().startswith("http"): return None
    url = url.strip()
    domain = get_domain(url)
    print(f"Scraping product {index+1}: {domain} — {url[:60]}")
    data = scrape_amazon(url) if "amazon" in domain else scrape_generic(url)
    print(f"Product data: title='{data.get('title','')[:30]}' img='{data.get('image_url','')[:50]}'")
    if not data.get("image_url"):
        print(f"No image found for {url[:60]}")
        return None
    image_path = download_product_image(data["image_url"], index)
    if not image_path: return None
    clean_path = remove_background(image_path)
    return {"title": data.get("title", "Product"), "price": data.get("price", ""), "image_path": clean_path, "url": url, "is_product": True}

def scrape_all_products(urls):
    results = []
    for i, url in enumerate(urls[:6]):
        results.append(scrape_product(url.strip(), i) if url and url.strip() else None)
    return results
