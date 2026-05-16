import os, uuid
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content, analyze_reference_images
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf
from drive_handler import download_reference_images

app = Flask(__name__)
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            "product_links":  data.get("product_links", ""),
            "drive_url":      data.get("drive_url", ""),
        }

        # Step 1: Download client reference images from Google Drive
        reference_paths = []
        reference_captions = []
        
        if form["drive_url"]:
            print(f"Downloading reference images from Drive...")
            reference_paths = download_reference_images(form["drive_url"])
            if reference_paths:
                print(f"Analyzing {len(reference_paths)} reference images with Claude Vision...")
                reference_captions = analyze_reference_images(reference_paths)
                print(f"Reference captions: {reference_captions}")

        # Update form with reference info for Claude
        form["has_reference_images"] = len(reference_paths) > 0
        form["reference_image_count"] = len(reference_paths)

        # Step 2: Generate AI content (fewer AI image prompts if we have references)
        content = generate_moodboard_content(form)

        # Step 3: Generate AI images for remaining slots
        ai_slots = max(0, 6 - len(reference_paths))
        ai_paths = generate_images(content.get("image_prompts", [])[:ai_slots], form) if ai_slots > 0 else []

        # Step 4: Merge — client references first, AI fills remaining slots
        image_paths = []
        ai_index = 0
        for i in range(6):
            if i < len(reference_paths) and reference_paths[i]:
                image_paths.append(reference_paths[i])
            else:
                image_paths.append(ai_paths[ai_index] if ai_index < len(ai_paths) else None)
                ai_index += 1

        # Step 5: Build captions — reference captions for client images, standard for AI
        standard_captions = ["SPACE OVERVIEW", "KEY FURNITURE", "MATERIAL DETAIL", 
                            "LIGHTING MOOD", "ACCENT STYLING", "COLOUR IN SPACE"]
        final_captions = []
        ref_index = 0
        ai_cap_index = len(reference_paths)
        for i in range(6):
            if i < len(reference_paths):
                cap = reference_captions[i] if i < len(reference_captions) else f"CLIENT REFERENCE {i+1}"
                final_captions.append(cap)
            else:
                final_captions.append(standard_captions[i] if i < len(standard_captions) else f"DETAIL {i+1}")

        # Step 6: Build PDF
        filename = f"moodboard_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        build_moodboard_pdf(form, content, image_paths, output_path, captions=final_captions)

        base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        return jsonify({
            "success": True,
            "pdf_url": f"{base_url}/outputs/{filename}",
            "mood_title": content["mood_title"],
            "designer_email": form["designer_email"],
            "client_email": form["client_email"],
            "client_name": form["client_name"],
            "project_name": form["project_name"],
            "reference_images_used": len(reference_paths),
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
