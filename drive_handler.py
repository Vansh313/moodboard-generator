import os, re, uuid, requests

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def extract_folder_id(url):
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else ""

def get_file_ids_from_folder(folder_id):
    """Get file IDs using Google Drive folder export as RSS/atom feed."""
    file_ids = []
    
    # Method 1: Google Drive folder as a list page
    urls_to_try = [
        f"https://drive.google.com/drive/folders/{folder_id}",
        f"https://drive.google.com/embeddedfolderview?id={folder_id}#list",
        f"https://drive.google.com/embeddedfolderview?id={folder_id}#grid",
    ]
    
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            html = r.text
            
            # Extract all patterns of file IDs
            found = set()
            
            # Pattern: /file/d/FILE_ID
            for m in re.finditer(r'/file/d/([a-zA-Z0-9_-]{20,})', html):
                found.add(m.group(1))
            
            # Pattern: id=FILE_ID in URLs  
            for m in re.finditer(r'[?&]id=([a-zA-Z0-9_-]{20,})', html):
                fid = m.group(1)
                if fid != folder_id:
                    found.add(fid)
            
            # Pattern: "FILE_ID" as standalone quoted string (common in Drive JS)
            for m in re.finditer(r'"([a-zA-Z0-9_-]{33})"', html):
                fid = m.group(1)
                if fid != folder_id:
                    found.add(fid)
                    
            # Pattern: data-id attribute
            for m in re.finditer(r'data-id="([a-zA-Z0-9_-]{20,})"', html):
                found.add(m.group(1))

            if found:
                unique = [f for f in found if f != folder_id]
                print(f"Method {url[-20:]}: found {len(unique)} IDs")
                file_ids.extend(unique)
                
        except Exception as e:
            print(f"URL error: {e}")
    
    # Deduplicate
    seen = set()
    unique_ids = []
    for fid in file_ids:
        if fid not in seen:
            seen.add(fid)
            unique_ids.append(fid)
    
    print(f"Total unique candidate IDs: {len(unique_ids)}")
    return unique_ids[:20]

def download_file(file_id, index):
    """Try multiple download strategies for a Google Drive file."""
    session = requests.Session()
    
    strategies = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=1",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=1",
        f"https://drive.google.com/uc?export=download&id={file_id}",
    ]
    
    for url in strategies:
        try:
            r = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            content = r.content
            content_type = r.headers.get('Content-Type', '')
            
            # Skip HTML responses (error/warning pages)
            if b'<!DOCTYPE' in content[:200] or b'<html' in content[:200]:
                # Check for virus scan confirm token
                confirm = re.search(rb'confirm=([0-9A-Za-z_-]+)', content)
                if confirm:
                    confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm.group(1).decode()}"
                    r2 = session.get(confirm_url, headers=HEADERS, timeout=30)
                    content = r2.content
                    content_type = r2.headers.get('Content-Type', '')
                    if b'<!DOCTYPE' in content[:200]:
                        continue
                else:
                    continue
            
            # Must be at least 10KB to be a real image
            if len(content) < 10000:
                continue
            
            # Detect image type
            if content[:8] == b'\x89PNG\r\n\x1a\n':
                ext = '.png'
            elif content[:3] == b'\xff\xd8\xff':
                ext = '.jpg'
            elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
                ext = '.webp'
            elif 'png' in content_type:
                ext = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # Not an image
                continue
            
            fp = os.path.join(TEMP_DIR, f"ref_{index}_{uuid.uuid4().hex[:6]}{ext}")
            with open(fp, 'wb') as f:
                f.write(content)
            print(f"Downloaded ref {index}: {fp} ({len(content)} bytes)")
            return fp
            
        except Exception as e:
            print(f"Strategy failed for {file_id}: {e}")
    
    return None

def download_reference_images(drive_url):
    if not drive_url or not drive_url.startswith("http"):
        return []
    
    drive_url = drive_url.strip()
    print(f"Processing Drive URL: {drive_url[:80]}")
    
    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        print("No folder ID found")
        return []
    
    print(f"Folder ID: {folder_id}")
    file_ids = get_file_ids_from_folder(folder_id)
    
    if not file_ids:
        print("No file IDs found")
        return []
    
    paths = []
    attempted = 0
    for fid in file_ids:
        if len(paths) >= 6:
            break
        if attempted >= 15:  # Don't try too many
            break
        attempted += 1
        path = download_file(fid, len(paths))
        if path:
            paths.append(path)
    
    print(f"Successfully downloaded {len(paths)} images (attempted {attempted} IDs)")
    return paths
