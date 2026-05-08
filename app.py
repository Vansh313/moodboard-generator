import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf

app = Flask(__name__)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_tally_payload(data):
    """Extract fields from Tally webhook payload."""
    fields = {}

    # Tally sends fields as a list under data.fields
    raw_fields = data.get("data", {}).get("fields", [])

    for field in raw_fields:
        label = field.get("label", "").strip()
        value = field.get("value", "")

        # Handle checkboxes (Room Types come as list of dicts)
        if isinstance(value, list):
            # Filter checked options
            checked = []
            for item in value:
                if isinstance(item, dict) and item.get("value") is True:
                    checked.append(item.get("text", ""))
                elif isinstance(item, str):
                    checked.append(item)
            value = ", ".join(checked) if checked else ""

        fields[label] = value if value is not None else ""

    return {
        "client_name":    fields.get("Client Name", ""),
        "project_name":   fields.get("Project Name", ""),
        "designer_name":  fields.get("Designer Name", ""),
        "designer_email": fields.get("Designer Email", ""),
        "client_email":   fields.get("Client Email", ""),
        "room_types":     fields.get("Room Type(s)", ""),
        "design_style":   fields.get("Design Style", ""),
        "color_prefs":    fields.get("Color Preferences", ""),
        "materials":      fields.get("Materials/Textures", ""),
        "mood_feel":      fields.get("Mood/Feel", ""),
        "budget_range":   fields.get("Budget Range", ""),
        "logo_url":       fields.get("Designer Logo URL", ""),
    }


@app.route("/generate-moodboard", methods=["POST"])
def generate_moodboard():
    try:
        raw = request.get_data(as_text=True)
        import json
        data = json.loads(raw)

        form = parse_tally_payload(data)

        # Validate required fields
        if not form["designer_name"] or not form["design_style"]:
            return jsonify({"error": "Missing required fields"}), 400

        # Step 1: Claude generates copy + image prompts
        content = generate_moodboard_content(form)

        # Step 2: fal.ai generates images
        image_paths = generate_images(content["image_prompts"])

        # Step 3: Build PDF
        filename = f"moodboard_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        build_moodboard_pdf(form, content, image_paths, output_path)

        # Step 4: Return PDF URL
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
