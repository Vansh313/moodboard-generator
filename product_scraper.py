import os, uuid, requests, re
from urllib.parse import urlparse

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
REMOVEBG_KEY = os.environ.get("REMOVEBG_KEY", "")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}

def get_domain(url):
    try: return urlparse(url).netloc.lower().replace("www.", "")
    except: return ""

def scrape_generic(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text
        title = ""
        t = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if not t: t = re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:title"', html)
        if t: title = t.group(1).strip()[:80]
        price = ""
        p = re.search(r'"price":\s*"?([\d.]+)"?', html)
        if p: price = f"${p.group(1)}"
        img_url = ""
        i = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if not i: i = re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html)
        if i: img_url = i.group(1)
        return {"title": title, "price": price, "image_url": img_url}
    except Exception as e:
        print(f"Scrape error: {e}")
        return {}

def scrape_amazon(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text
        title = ""
        t = re.search(r'<span id="productTitle"[^>]*>(.*?)</span>', html, re.DOTALL)
        if t: title = t.group(1).strip()[:80]
        price = ""
        p = re.search(r'<span class="a-price-whole">([\d,]+)</span>', html)
        if p: price = f"${p.group(1)}"
        img_url = ""
        for pat in [r'"large":"(https://m\.media-amazon\.com/images/[^"]+)"', r'data-old-hires="(https://[^"]+)"', r'"hiRes":"(https://[^"]+)"']:
            i = re.search(pat, html)
            if i: img_url = i.group(1); break
        return {"title": title or scrape_generic(url).get("title",""), "price": price, "image_url": img_url or scrape_generic(url).get("image_url","")}
    except: return scrape_generic(url)

def remove_background(image_path):
    if not REMOVEBG_KEY: return image_path
    try:
        with open(image_path, "rb") as f:
            r = requests.post("https://api.api4.ai/v1/background-removal", files={"image": f}, headers={"Authorization": f"Bearer {REMOVEBG_KEY}"}, timeout=30)
        if r.status_code == 200:
            new_path = image_path.rsplit(".", 1)[0] + "_nobg.png"
            with open(new_path, "wb") as f: f.write(r.content)
            print(f"BG removed: {new_path}")
            return new_path
        else:
            print(f"BG removal failed: {r.status_code} {r.text[:100]}")
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
        print(f"Product image saved: {fp}")
        return fp
    except Exception as e:
        print(f"Product image download error: {e}")
        return None

def scrape_product(url, index):
    if not url or not url.strip().startswith("http"): return None
    url = url.strip()
    domain = get_domain(url)
    print(f"Scraping product {index+1}: {domain}")
    data = scrape_amazon(url) if "amazon" in domain else scrape_generic(url)
    if not data.get("image_url"):
        print(f"No image found for {url}")
        return None
    image_path = download_product_image(data["image_url"], index)
    if not image_path: return None
    clean_path = remove_background(image_path)
    return {"title": data.get("title", "Product"), "price": data.get("price", ""), "image_path": clean_path, "url": url, "is_product": True}

def scrape_all_products(urls):
    results = []
    for i, url in enumerate(urls[:6]):
        if url and url.strip():
            results.append(scrape_product(url.strip(), i))
        else:
            results.append(None)
    return results
