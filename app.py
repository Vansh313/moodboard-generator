import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf

app = Flask(__name__)
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/generate-moodboard", methods=["POST"])
def generate_moodboard():
    try:
        data = request.get_json(force=True)

        # Accept direct flat JSON from Make.com
        if "client_name" in data:
            form = {
                "client_name":    data.get("client_name", ""),
                "project_name":   data.get("project_name", ""),
                "designer_name":  data.get("designer_name", ""),
                "designer_email": data.get("designer_email", ""),
                "client_email":   data.get("client_email", ""),
                "room_types":     data.get("room_types", ""),
                "design_style":   data.get("design_style", ""),
                "color_prefs":    data.get("color_prefs", ""),
                "materials":      data.get("materials", ""),
                "mood_feel":      data.get("mood_feel", ""),
                "budget_range":   data.get("budget_range", ""),
                "logo_url":       data.get("logo_url", ""),
            }
        else:
            return jsonify({"error": "Missing required fields"}), 400

        if not form["designer_name"] or not form["design_style"]:
            return jsonify({"error": "Missing designer_name or design_style"}), 400

        content = generate_moodboard_content(form)
        image_paths = generate_images(content["image_prompts"], form)
        filename = f"moodboard_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        build_moodboard_pdf(form, content, image_paths, output_path)

        base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        pdf_url = f"{base_url}/outputs/{filename}"

        return jsonify({
            "success": True,
            "pdf_url": pdf_url,
            "mood_title": content["mood_title"],
            "designer_email": form["designer_email"],
            "client_email": form["client_email"],
            "client_name": form["client_name"],
            "project_name": form["project_name"],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/outputs/<filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
