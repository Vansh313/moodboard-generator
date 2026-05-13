import os, uuid, requests, json
from flask import Flask, request, jsonify, send_from_directory
from claude_handler import generate_moodboard_content
from image_generator import generate_images
from pdf_builder import build_moodboard_pdf
from product_scraper import scrape_all_products

app = Flask(__name__)
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_logo_url(raw):
    if not raw:
        return ""
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("http"):
            return raw
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                item = parsed[0]
                return item.get("url", "") if isinstance(item, dict) else ""
            if isinstance(parsed, dict):
                return parsed.get("url", "")
        except:
            pass
    if isinstance(raw, list) and raw:
        item = raw[0]
        if isinstance(item, dict):
            return item.get("url", "")
        if isinstance(item, str) and item.startswith("http"):
            return item
    if isinstance(raw, dict):
        return raw.get("url", "")
    return ""

@app.route("/generate-moodboard", methods=["POST"])
def generate_moodboard():
    try:
        data = request.get_json(force=True)
        if "client_name" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        logo_url = extract_logo_url(data.get("logo_url", ""))
        print(f"Logo URL extracted: '{logo_url}'")

        # Parse product names
        product_names_raw = data.get("product_names", "")
        product_names = [n.strip() for n in product_names_raw.split("\n") if n.strip()] if product_names_raw else []

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
            "logo_url":       logo_url,
            "product_links":  data.get("product_links", ""),
        }

        # Parse product image URLs
        product_urls = []
        if form["product_links"]:
            product_urls = [u.strip() for u in form["product_links"].replace(",", "\n").split("\n") if u.strip().startswith("http")]

        products = scrape_all_products(product_urls) if product_urls else []

        # Inject product names
        for i, product in enumerate(products):
            if product and i < len(product_names):
                product["title"] = product_names[i]

        content = generate_moodboard_content(form)

        filled = len([p for p in products if p])
        ai_slots = max(0, 6 - filled)
        ai_paths = generate_images(content["image_prompts"][:ai_slots], form) if ai_slots > 0 else []

        image_paths = []
        ai_index = 0
        for i in range(6):
            if i < len(products) and products[i]:
                image_paths.append(products[i]["image_path"])
            else:
                image_paths.append(ai_paths[ai_index] if ai_index < len(ai_paths) else None)
                ai_index += 1

        filename = f"moodboard_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(OUTPUT_DIR, filename)
        build_moodboard_pdf(form, content, image_paths, output_path, products=products)

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
