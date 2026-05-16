import os, re, uuid, requests

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def extract_folder_id(url):
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else ""

def get_file_ids_from_folder(folder_id):
    """Scrape file IDs from Google Drive folder using the export URL."""
    file_ids = []
    
    # Try the folder page
    try:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        
        # Pattern 1: file IDs in data-id attributes
        ids1 = re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', html)
        # Pattern 2: file IDs in href links
        ids2 = re.findall(r'/file/d/([a-zA-Z0-9_-]{25,})/', html)
        # Pattern 3: general long IDs
        ids3 = re.findall(r'"([a-zA-Z0-9_-]{33,44})"', html)
        
        all_ids = ids1 + ids2 + ids3
        seen = set([folder_id])
        for fid in all_ids:
            if fid not in seen:
                seen.add(fid)
                file_ids.append(fid)
        
        print(f"Found {len(file_ids)} candidate file IDs")
    except Exception as e:
        print(f"Folder page error: {e}")
    
    return file_ids[:20]

def download_file(file_id, index):
    """Download file trying multiple Google Drive download methods."""
    methods = [
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=1",
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=1",
        f"https://drive.google.com/uc?id={file_id}&export=download",
    ]
    
    session = requests.Session()
    
    for method_url in methods:
        try:
            r = session.get(method_url, headers=HEADERS, timeout=30, allow_redirects=True)
            
            content = r.content
            content_type = r.headers.get('Content-Type', '')
            
            # Skip if it's HTML (means we got a warning page or error)
            if b'<!DOCTYPE' in content[:100] or b'<html' in content[:100]:
                # Try to find confirm token
                confirm = re.search(rb'confirm=([0-9A-Za-z_-]+)', content)
                if confirm:
                    confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm.group(1).decode()}"
                    r2 = session.get(confirm_url, headers=HEADERS, timeout=30)
                    if len(r2.content) > 10000 and b'<!DOCTYPE' not in r2.content[:100]:
                        content = r2.content
                        content_type = r2.headers.get('Content-Type', '')
                    else:
                        continue
                else:
                    continue
            
            if len(content) < 10000:
                continue
            
            # Determine extension
            if 'png' in content_type:
                ext = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif content[:4] == b'\x89PNG':
                ext = '.png'
            elif content[:3] == b'\xff\xd8\xff':
                ext = '.jpg'
            else:
                ext = '.jpg'
            
            fp = os.path.join(TEMP_DIR, f"ref_{index}_{uuid.uuid4().hex[:6]}{ext}")
            with open(fp, 'wb') as f:
                f.write(content)
            print(f"Downloaded ref {index}: {fp} ({len(content)} bytes)")
            return fp
            
        except Exception as e:
            print(f"Method failed for {file_id}: {e}")
            continue
    
    print(f"All methods failed for file {index} ({file_id})")
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
    for i, fid in enumerate(file_ids):
        if len(paths) >= 6:
            break
        path = download_file(fid, i)
        if path:
            paths.append(path)
    
    print(f"Successfully downloaded {len(paths)} images")
    return paths
