import os
import re
import uuid
import requests

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

def extract_folder_id(drive_url: str) -> str:
    """Extract folder ID from various Google Drive URL formats."""
    patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
    ]
    for pat in patterns:
        m = re.search(pat, drive_url)
        if m:
            return m.group(1)
    return ""

def extract_file_id(file_url: str) -> str:
    """Extract file ID from Google Drive file URL."""
    patterns = [
        r'/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
    ]
    for pat in patterns:
        m = re.search(pat, file_url)
        if m:
            return m.group(1)
    return ""

def download_drive_file(file_id: str, index: int) -> str:
    """Download a single file from Google Drive by file ID."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        session = requests.Session()
        r = session.get(url, headers=HEADERS, timeout=30, stream=True)
        
        # Handle large file warning page
        for key, value in r.cookies.items():
            if 'download_warning' in key:
                url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={value}"
                r = session.get(url, headers=HEADERS, timeout=30, stream=True)
                break

        content_type = r.headers.get('Content-Type', '')
        if 'image' in content_type:
            ext = '.jpg' if 'jpeg' in content_type else '.png'
        else:
            ext = '.jpg'

        filepath = os.path.join(TEMP_DIR, f"ref_{index}_{uuid.uuid4().hex[:6]}{ext}")
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size = os.path.getsize(filepath)
        if size < 5000:
            print(f"File {index} too small ({size} bytes), skipping")
            os.remove(filepath)
            return None

        print(f"Downloaded reference image {index}: {filepath} ({size} bytes)")
        return filepath

    except Exception as e:
        print(f"Download error for file {index}: {e}")
        return None

def get_folder_files(folder_id: str) -> list:
    """Get list of image file IDs from a public Google Drive folder."""
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        
        # Extract file IDs from folder page
        file_ids = re.findall(r'"([a-zA-Z0-9_-]{25,})"', html)
        
        # Filter unique IDs that look like file IDs
        seen = set()
        unique_ids = []
        for fid in file_ids:
            if fid not in seen and len(fid) >= 25 and fid != folder_id:
                seen.add(fid)
                unique_ids.append(fid)
        
        print(f"Found {len(unique_ids)} potential file IDs in folder")
        return unique_ids[:10]  # Max 10 files
        
    except Exception as e:
        print(f"Folder fetch error: {e}")
        return []

def download_reference_images(drive_url: str) -> list:
    """
    Main function. Takes a Google Drive folder URL.
    Returns list of local image file paths (up to 6).
    """
    if not drive_url or not drive_url.strip().startswith("http"):
        return []
    
    drive_url = drive_url.strip()
    print(f"Processing Drive URL: {drive_url[:60]}")
    
    # Check if it's a direct file link
    if '/file/' in drive_url or '/d/' in drive_url:
        file_id = extract_file_id(drive_url)
        if file_id:
            path = download_drive_file(file_id, 0)
            return [path] if path else []
    
    # It's a folder link
    folder_id = extract_folder_id(drive_url)
    if not folder_id:
        print("Could not extract folder ID from URL")
        return []
    
    print(f"Folder ID: {folder_id}")
    file_ids = get_folder_files(folder_id)
    
    if not file_ids:
        print("No files found in folder — trying direct folder download approach")
        # Try Google Drive API public approach
        api_url = f"https://www.googleapis.com/drive/v3/files?q='{folder_id}'+in+parents&key=AIzaSyD-placeholder"
        return []
    
    # Download up to 6 images
    paths = []
    for i, fid in enumerate(file_ids[:6]):
        path = download_drive_file(fid, i)
        if path:
            paths.append(path)
        if len(paths) >= 6:
            break
    
    print(f"Downloaded {len(paths)} reference images")
    return paths
