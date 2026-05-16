import os, uuid
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content, analyze_reference_images, generate_room_composite_prompt
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf
from drive_handler import download_reference_images
from composite_generator import generate_composite_room

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
            "drive_url":      data.get("drive_url", ""),
        }

        # Step 1: Download reference images from Drive
        reference_paths = []
        reference_captions = []

        if form["drive_url"]:
            print("Downloading reference images from Drive...")
            reference_paths = download_reference_images(form["drive_url"])
            if reference_paths:
                print(f"Analyzing {len(reference_paths)} images with Claude Vision...")
                reference_captions = analyze_reference_images(reference_paths)

        form["has_reference_images"] = len(reference_paths) > 0
        form["reference_image_count"] = len(reference_paths)

        # Step 2: Generate composite room if we have references
        composite_path = None
        if len(reference_paths) >= 2:
            print("Generating composite room with Flux Kontext...")
            room_prompt = generate_room_composite_prompt(form, reference_captions)
            print(f"Room prompt: {room_prompt}")
            composite_path = generate_composite_room(reference_paths, room_prompt)

        # Step 3: Generate moodboard content
        content = generate_moodboard_content(form)

        # Step 4: Build final image grid
        # Slot 0: composite room (hero)
        # Slots 1-N: individual client reference photos
        # Remaining: AI generated
        image_paths = []
        captions = []

        if composite_path:
            image_paths.append(composite_path)
            captions.append("YOUR ROOM VISION")

        for i, path in enumerate(reference_paths[:5]):  # up to 5 refs after composite
            image_paths.append(path)
            cap = reference_captions[i] if i < len(reference_captions) else f"CLIENT REFERENCE {i+1}"
            captions.append(cap)

        # Fill remaining slots with AI images
        ai_slots = max(0, 6 - len(image_paths))
        standard_captions = ["SPACE OVERVIEW", "KEY FURNITURE", "MATERIAL DETAIL", "LIGHTING MOOD", "ACCENT STYLING", "COLOUR IN SPACE"]
        if ai_slots > 0:
            ai_paths = generate_images(content.get("image_prompts", [])[:ai_slots], form)
            for i, path in enumerate(ai_paths):
                image_paths.append(path)
                captions.append(standard_captions[len(image_paths) - (6 - ai_slots) - 1] if len(image_paths) <= 6 else "DETAIL")

        # Trim to 6
        image_paths = image_paths[:6]
        captions = captions[:6]

        # Step 5: Build PDF
        filename = f"moodboard_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        build_moodboard_pdf(form, content, image_paths, output_path, captions=captions)

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
            "composite_generated": composite_path is not None,
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
