import os
import base64
import uuid

def image_to_base64(path):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = path.lower().split(".")[-1]
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/jpeg")
        return f"data:{mime};base64,{data}"
    except:
        return ""

def build_moodboard_page(form, content, image_paths, captions, output_path):
    color_palette = content.get("color_palette", [])
    mood_title = content.get("mood_title", "Design Vision")
    tagline = content.get("tagline", "")
    mood_description = content.get("mood_description", "")
    designer_note = content.get("designer_note", "")
    materials = content.get("materials_list", [])

    # Convert images to base64
    images_b64 = []
    for i, path in enumerate(image_paths[:8]):
        if path and os.path.exists(path):
            b64 = image_to_base64(path)
            cap = captions[i] if i < len(captions) else ""
            images_b64.append({"b64": b64, "caption": cap})

    # Build color palette CSS
    palette_html = ""
    for c in color_palette:
        hex_val = c.get("hex", "#ccc")
        name = c.get("name", "")
        role = c.get("role", "")
        palette_html += f'''
        <div class="swatch-item">
            <div class="swatch-color" style="background:{hex_val};"></div>
            <div class="swatch-name">{name}</div>
            <div class="swatch-role">{role}</div>
            <div class="swatch-hex">{hex_val}</div>
        </div>'''

    # Build materials
    materials_html = "".join(f'<span class="material-tag">{m}</span>' for m in materials[:6])

    # Layout positions for collage — each image gets fixed position/size/rotation
    layouts = [
        {"top": "2%",   "left": "38%", "width": "58%",  "rotate": "1.5deg",  "z": 2},
        {"top": "3%",   "left": "1%",  "width": "35%",  "rotate": "-2deg",   "z": 3},
        {"top": "30%",  "left": "2%",  "width": "27%",  "rotate": "1deg",    "z": 2},
        {"top": "34%",  "left": "31%", "width": "29%",  "rotate": "-1.5deg", "z": 4},
        {"top": "30%",  "left": "62%", "width": "36%",  "rotate": "2deg",    "z": 2},
        {"top": "56%",  "left": "3%",  "width": "40%",  "rotate": "-1deg",   "z": 3},
        {"top": "55%",  "left": "45%", "width": "52%",  "rotate": "1deg",    "z": 2},
        {"top": "76%",  "left": "15%", "width": "65%",  "rotate": "-0.5deg", "z": 1},
    ]

    images_html = ""
    for i, img in enumerate(images_b64):
        if not img["b64"]:
            continue
        lay = layouts[i % len(layouts)]
        images_html += f'''
        <div class="collage-item" style="top:{lay['top']};left:{lay['left']};width:{lay['width']};transform:rotate({lay['rotate']});z-index:{lay['z']};">
            <img src="{img['b64']}" alt="{img['caption']}">
            <div class="img-caption">{img['caption']}</div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{mood_title} — {form.get("project_name","")}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #B8AA96;
    font-family: 'Jost', sans-serif;
    color: #2C2416;
    min-height: 100vh;
  }}

  .page {{
    max-width: 680px;
    margin: 0 auto;
    background: #C8B89A;
    position: relative;
    overflow: hidden;
  }}

  /* Grainy texture overlay */
  .page::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.08'/%3E%3C/svg%3E");
    opacity: 0.4;
    pointer-events: none;
    z-index: 100;
  }}

  /* Header */
  .header {{
    padding: 2.5rem 2rem 1rem;
    position: relative;
    z-index: 10;
  }}

  .studio-name {{
    font-family: 'Jost', sans-serif;
    font-weight: 200;
    font-size: 10px;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #6B5A42;
    margin-bottom: 0.5rem;
  }}

  .mood-title {{
    font-family: 'Cormorant Garamond', serif;
    font-weight: 300;
    font-size: 42px;
    line-height: 1.1;
    color: #2C2416;
    margin-bottom: 0.4rem;
  }}

  .tagline {{
    font-family: 'Jost', sans-serif;
    font-weight: 200;
    font-size: 12px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #6B5A42;
  }}

  /* Collage area */
  .collage {{
    position: relative;
    width: 100%;
    height: 75vw;
    max-height: 510px;
    margin: 1rem 0;
  }}

  .collage-item {{
    position: absolute;
    box-shadow: 4px 6px 20px rgba(0,0,0,0.18);
  }}

  .collage-item img {
    mix-blend-mode: multiply;{
    width: 100%;
    display: block;
  }}

  .img-caption {{
    font-family: 'Jost', sans-serif;
    font-size: 7px;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #6B5A42;
    margin-top: 4px;
    text-align: center;
  }}

  /* Color palette strip */
  .palette-section {{
    padding: 2rem 2rem 0;
    position: relative;
    z-index: 10;
  }}

  .section-label {{
    font-family: 'Jost', sans-serif;
    font-size: 8px;
    font-weight: 300;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #6B5A42;
    margin-bottom: 1rem;
  }}

  .palette-strip {{
    display: flex;
    gap: 0;
    height: 56px;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 0.75rem;
  }}

  .palette-strip-color {{
    flex: 1;
  }}

  .swatches {{
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }}

  .swatch-item {{
    text-align: center;
  }}

  .swatch-color {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    margin: 0 auto 4px;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
  }}

  .swatch-name {{
    font-size: 8px;
    font-weight: 400;
    letter-spacing: 0.5px;
    color: #2C2416;
  }}

  .swatch-role {{
    font-size: 7px;
    color: #8B7355;
    letter-spacing: 0.5px;
  }}

  .swatch-hex {{
    font-size: 7px;
    color: #A08060;
    font-family: monospace;
  }}

  /* Description */
  .description-section {{
    padding: 1.5rem 2rem;
    position: relative;
    z-index: 10;
  }}

  .mood-description {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 16px;
    font-weight: 300;
    line-height: 1.8;
    color: #3C2E1E;
    font-style: italic;
    margin-bottom: 1.5rem;
  }}

  /* Materials */
  .materials-section {{
    padding: 0 2rem 1.5rem;
    position: relative;
    z-index: 10;
  }}

  .materials-list {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}

  .material-tag {{
    font-family: 'Jost', sans-serif;
    font-size: 8px;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #6B5A42;
    border: 0.5px solid #A08060;
    padding: 4px 10px;
    border-radius: 20px;
  }}

  /* Designer note */
  .note-section {{
    padding: 1.5rem 2rem;
    border-top: 0.5px solid rgba(107,90,66,0.3);
    position: relative;
    z-index: 10;
  }}

  .designer-note {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 14px;
    font-weight: 300;
    line-height: 1.9;
    color: #4A3B28;
    font-style: italic;
  }}

  .designer-sig {{
    font-family: 'Jost', sans-serif;
    font-size: 9px;
    font-weight: 300;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #8B7355;
    margin-top: 1rem;
  }}

  /* Footer */
  .footer {{
    padding: 1rem 2rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    z-index: 10;
  }}

  .footer-project {{
    font-size: 8px;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #8B7355;
  }}

  .download-btn {{
    font-family: 'Jost', sans-serif;
    font-size: 9px;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2C2416;
    border: 0.5px solid #6B5A42;
    padding: 8px 16px;
    text-decoration: none;
    cursor: pointer;
    background: transparent;
    transition: background 0.2s;
  }}

  .download-btn:hover {{
    background: rgba(44,36,22,0.08);
  }}

  @media print {
    html, body { background: #C8B89A !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }{
    .download-btn {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <div class="studio-name">{form.get("designer_name","Studio")} &nbsp;·&nbsp; {form.get("project_name","")}</div>
    <h1 class="mood-title">{mood_title}</h1>
    <div class="tagline">{tagline}</div>
  </div>

  <div class="collage">
    {images_html}
  </div>

  <div class="palette-section">
    <div class="section-label">Colour Story</div>
    <div class="palette-strip">
      {"".join(f'<div class="palette-strip-color" style="background:{c.get("hex","#ccc")};"></div>' for c in color_palette)}
    </div>
    <div class="swatches">
      {palette_html}
    </div>
  </div>

  <div class="description-section">
    <div class="section-label">The Vision</div>
    <p class="mood-description">{mood_description}</p>
  </div>

  <div class="materials-section">
    <div class="section-label">Materials &amp; Finishes</div>
    <div class="materials-list">{materials_html}</div>
  </div>

  <div class="note-section">
    <div class="section-label">A Note From Your Designer</div>
    <p class="designer-note">{designer_note}</p>
    <div class="designer-sig">{form.get("designer_name","")}</div>
  </div>

  <div class="footer">
    <div class="footer-project">{form.get("client_name","")} &nbsp;·&nbsp; {form.get("room_types","")}</div>
    <button class="download-btn" onclick="window.print()">Save as PDF</button>
  </div>

</div>
</body>
</html>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Moodboard page saved: {output_path}")
    return output_path
