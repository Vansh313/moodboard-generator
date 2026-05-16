import os, re, uuid, requests

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def extract_folder_id(url):
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else ""

def download_file(file_id, index):
    session = requests.Session()
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        r = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        # Handle confirmation page for large files
        if b'confirm=' in r.content or b'virus scan' in r.content.lower():
            confirm = re.search(r'confirm=([0-9A-Za-z_]+)', r.text)
            if confirm:
                url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm.group(1)}"
                r = session.get(url, headers=HEADERS, timeout=30)
        
        content = r.content
        if len(content) < 10000:
            print(f"File {index} too small ({len(content)} bytes), skipping")
            return None
            
        content_type = r.headers.get('Content-Type', '')
        ext = '.png' if 'png' in content_type else '.jpg'
        fp = os.path.join(TEMP_DIR, f"ref_{index}_{uuid.uuid4().hex[:6]}{ext}")
        with open(fp, 'wb') as f:
            f.write(content)
        print(f"Downloaded ref {index}: {fp} ({len(content)} bytes)")
        return fp
    except Exception as e:
        print(f"Download error {index}: {e}")
        return None

def get_file_ids_from_folder(folder_id):
    """Get direct download file IDs from Google Drive folder."""
    # Try the folder API endpoint
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        
        # Find file IDs - they appear in specific data attributes
        ids = re.findall(r'"([a-zA-Z0-9_-]{33})"', html)
        ids += re.findall(r'"([a-zA-Z0-9_-]{44})"', html)
        
        seen = set()
        unique = []
        for fid in ids:
            if fid not in seen and fid != folder_id:
                seen.add(fid)
                unique.append(fid)
        
        print(f"Found {len(unique)} file IDs")
        return unique[:12]
    except Exception as e:
        print(f"Folder fetch error: {e}")
        return []

def download_reference_images(drive_url):
    if not drive_url or not drive_url.startswith("http"):
        return []
    
    drive_url = drive_url.strip()
    print(f"Processing: {drive_url[:80]}")
    
    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        print("No folder ID found")
        return []
    
    print(f"Folder ID: {folder_id}")
    file_ids = get_file_ids_from_folder(folder_id)
    
    paths = []
    for i, fid in enumerate(file_ids):
        if len(paths) >= 6:
            break
        path = download_file(fid, i)
        if path:
            paths.append(path)
    
    print(f"Successfully downloaded {len(paths)} images")
    return paths
