import os, uuid, requests
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content, analyze_reference_images, generate_room_composite_prompt
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf
from composite_generator import generate_composite_room
from moodboard_page_builder import build_moodboard_page

app = Flask(__name__)
OUTPUT_DIR = "outputs"
TEMP_DIR = "temp_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def download_tally_images(file_list):
    if not file_list:
        return []
    paths = []
    for i, item in enumerate(file_list[:10]):
        try:
            if isinstance(item, dict): url = item.get("url", "")
            elif isinstance(item, str): url = item
            else: continue
            if not url.startswith("http"): continue
            print(f"Downloading reference image {i+1}: {url[:60]}")
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if len(r.content) < 5000: continue
            content = r.content
            if content[:8] == b'\x89PNG\r\n\x1a\n': ext = '.png'
            elif content[:3] == b'\xff\xd8\xff': ext = '.jpg'
            elif content[:4] == b'RIFF': ext = '.webp'
            else: ext = '.jpg'
            fp = os.path.join(TEMP_DIR, f"ref_{i}_{uuid.uuid4().hex[:6]}{ext}")
            with open(fp, 'wb') as f: f.write(content)
            print(f"Saved: {fp} ({len(content)} bytes)")
            paths.append(fp)
        except Exception as e:
            print(f"Download error for image {i+1}: {e}")
    print(f"Downloaded {len(paths)} reference images from Tally")
    return paths

@app.route("/generate-moodboard", methods=["POST"])
def generate_moodboard():
    try:
        data = request.get_json(force=True)
        if "client_name" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        form = {
            "client_name":    data.get("client_name", "Client"),
            "project_name":   data.get("project_name", "Project"),
            "designer_name":  data.get("designer_name", "Designer"),
            "designer_email": data.get("designer_email", ""),
            "client_email":   data.get("client_email", ""),
            "room_types":     data.get("room_types", ""),
            "design_style":   data.get("design_style", "Modern"),
            "color_prefs":    data.get("color_prefs", ""),
            "materials":      data.get("materials", ""),
            "mood_feel":      data.get("mood_feel", ""),
            "budget_range":   data.get("budget_range", ""),
            "logo_url":       data.get("logo_url", ""),
        }

        reference_files = data.get("reference_images", [])
        reference_paths = download_tally_images(reference_files) if reference_files else []
        reference_captions = []

        if reference_paths:
            print(f"Analyzing {len(reference_paths)} images with Claude Vision...")
            reference_captions = analyze_reference_images(reference_paths)

        form["has_reference_images"] = len(reference_paths) > 0
        form["reference_image_count"] = len(reference_paths)

        # Generate composite room
        composite_path = None
        if len(reference_paths) >= 2:
            print("Generating composite room with Flux Kontext...")
            room_prompt = generate_room_composite_prompt(form, reference_captions)
            result = generate_composite_room(reference_paths, room_prompt)
            composite_path = result[0] if isinstance(result, tuple) else result

        content = generate_moodboard_content(form)

        # Build image grid
        image_paths = []
        captions = []

        # Slot 1: composite room
        if composite_path:
            image_paths.append(composite_path)
            captions.append("YOUR ROOM VISION")

        # Slots 2-6: client reference photos
        for i, path in enumerate(reference_paths):
            if len(image_paths) >= 6: break
            image_paths.append(path)
            cap = reference_captions[i] if i < len(reference_captions) else f"REFERENCE {i+1}"
            captions.append(cap)

        image_paths = image_paths[:6]
        captions = captions[:6]

        uid = uuid.uuid4().hex[:8]
        pdf_filename = f"moodboard_{uid}.pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        build_moodboard_pdf(form, content, image_paths, pdf_path, captions=captions)

        page_filename = f"moodboard_{uid}.html"
        page_path = os.path.join(OUTPUT_DIR, page_filename)
        build_moodboard_page(form, content, image_paths, captions, page_path)

        base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        return jsonify({
            "success": True,
            "pdf_url": f"{base_url}/outputs/{pdf_filename}",
            "page_url": f"{base_url}/outputs/{page_filename}",
            "mood_title": content["mood_title"],
            "designer_email": form["designer_email"],
            "client_email": form["client_email"],
            "client_name": form["client_name"],
            "project_name": form["project_name"],
            "reference_images_used": len(reference_paths),
            "composite_generated": composite_path is not None,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/outputs/<filename>")
def serve_output(filename): return send_from_directory(OUTPUT_DIR, filename)

@app.route("/health")
def health(): return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
