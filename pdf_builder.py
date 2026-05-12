import os
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black

W, H = A4  # 595 x 842 pts

DARK_BG    = HexColor("#1A1A1A")
DARK_CARD  = HexColor("#242424")
OFF_WHITE  = HexColor("#F5F0EB")
MUTED_GOLD = HexColor("#C9A96E")
LIGHT_GREY = HexColor("#888888")

L_MARGIN = 25*mm   # left margin
R_MARGIN = 25*mm   # right margin
CONTENT_W = W - L_MARGIN - R_MARGIN


def hex_to_color(hex_str: str):
    try:
        h = hex_str.strip().lstrip("#")
        if len(h) == 6:
            return HexColor(f"#{h}")
    except Exception:
        pass
    return HexColor("#888888")


def draw_background(c, color=DARK_BG):
    c.setFillColor(color)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_text(c, text, x, y, font="Helvetica", size=12, color=white, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def wrap_text_lines(text: str, max_chars: int = 65) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fetch_logo(url: str):
    if not url or not url.startswith("http"):
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return BytesIO(r.content)
    except Exception:
        return None


# ── PAGE 1: COVER ─────────────────────────────────────────────────────────────
def draw_cover(c, form, content):
    draw_background(c, DARK_BG)

    # Gold accent bar left
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 4, H, fill=1, stroke=0)

    # Top label
    draw_text(c, "INTERIOR MOODBOARD", L_MARGIN, H - 25*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    # Mood title — split into lines, constrained width
    title = content.get("mood_title", "Design Vision").upper()
    title_words = title.split()
    if len(title_words) <= 2:
        title_lines = [title]
    elif len(title_words) <= 4:
        mid = len(title_words) // 2
        title_lines = [" ".join(title_words[:mid]), " ".join(title_words[mid:])]
    else:
        third = len(title_words) // 3
        title_lines = [
            " ".join(title_words[:third]),
            " ".join(title_words[third:2*third]),
            " ".join(title_words[2*third:])
        ]

    y = H - 70*mm
    for line in title_lines:
        draw_text(c, line, W / 2, y, font="Helvetica-Bold", size=32, color=OFF_WHITE, align="center")
        y -= 12*mm

    # Tagline — centered, constrained
    tagline = content.get("tagline", "")
    tagline_lines = wrap_text_lines(tagline, max_chars=50)
    y -= 4*mm
    for line in tagline_lines:
        draw_text(c, line, W / 2, y, font="Helvetica-Oblique", size=10, color=LIGHT_GREY, align="center")
        y -= 6.5*mm

    # Divider
    y -= 6*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.5)
    c.line(60*mm, y, W - 60*mm, y)
    y -= 10*mm

    # Project info — left aligned with margin
    info_items = [
        ("CLIENT",  form.get("client_name", "")),
        ("PROJECT", form.get("project_name", "")),
        ("STYLE",   form.get("design_style", "")),
        ("ROOMS",   form.get("room_types", "")),
    ]
    col_x = L_MARGIN + 10*mm
    for label, value in info_items:
        if value:
            draw_text(c, label, col_x, y, font="Helvetica", size=7, color=MUTED_GOLD)
            # Truncate long values
            val = value[:45] + "…" if len(value) > 45 else value
            draw_text(c, val, col_x, y - 5*mm, font="Helvetica-Bold", size=10, color=OFF_WHITE)
            y -= 15*mm

    # Logo
    logo_data = fetch_logo(form.get("logo_url", ""))
    if logo_data:
        try:
            c.drawImage(logo_data, W / 2 - 20*mm, 32*mm, width=40*mm, height=15*mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Designer credit
    draw_text(c, f"PREPARED BY  {form.get('designer_name', '').upper()}", W / 2, 22*mm,
              font="Helvetica", size=7, color=LIGHT_GREY, align="center")

    c.showPage()


# ── PAGE 2: PALETTE & MOOD ────────────────────────────────────────────────────
def draw_palette_page(c, content):
    draw_background(c, DARK_BG)
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 4, H, fill=1, stroke=0)

    draw_text(c, "COLOUR PALETTE & MOOD", L_MARGIN, H - 25*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    palette = content.get("color_palette", [])
    n = len(palette)
    gap = 3*mm
    swatch_w = (CONTENT_W - (n - 1) * gap) / n if n > 0 else 30*mm
    swatch_h = 20*mm
    start_x = L_MARGIN
    swatch_y = H - 70*mm

    for i, color_item in enumerate(palette):
        x = start_x + i * (swatch_w + gap)
        col = hex_to_color(color_item.get("hex", "#888888"))
        c.setFillColor(col)
        c.roundRect(x, swatch_y, swatch_w, swatch_h, 1.5*mm, fill=1, stroke=0)

        cx = x + swatch_w / 2
        draw_text(c, color_item.get("hex", "").upper(), cx,
                  swatch_y - 5*mm, font="Helvetica", size=6, color=LIGHT_GREY, align="center")
        name = color_item.get("name", "")
        if len(name) > 11:
            name = name[:10] + "…"
        draw_text(c, name, cx, swatch_y - 9.5*mm,
                  font="Helvetica-Bold", size=7, color=OFF_WHITE, align="center")
        draw_text(c, color_item.get("role", "").upper(), cx, swatch_y - 14*mm,
                  font="Helvetica", size=5.5, color=MUTED_GOLD, align="center")

    div_y = swatch_y - 20*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(L_MARGIN, div_y, W - R_MARGIN, div_y)

    draw_text(c, "THE VISION", L_MARGIN, div_y - 10*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    description = content.get("mood_description", "")
    lines = wrap_text_lines(description, max_chars=75)
    text_y = div_y - 20*mm
    for line in lines:
        draw_text(c, line, L_MARGIN, text_y, font="Helvetica", size=9.5, color=OFF_WHITE)
        text_y -= 6*mm

    text_y -= 8*mm
    draw_text(c, "DESIGN DIRECTION", L_MARGIN, text_y,
              font="Helvetica", size=7, color=MUTED_GOLD)
    draw_text(c, content.get("mood_title", "").upper(), L_MARGIN, text_y - 7*mm,
              font="Helvetica-Bold", size=13, color=OFF_WHITE)

    c.showPage()


# ── PAGE 3: IMAGE GRID ────────────────────────────────────────────────────────
def draw_image_grid(c, image_paths, content):
    draw_background(c, DARK_BG)
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 4, H, fill=1, stroke=0)

    draw_text(c, "MOODBOARD IMAGERY", L_MARGIN, H - 25*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    gap = 3*mm
    img_w = (CONTENT_W - gap) / 2
    img_h = (H - 50*mm - 2 * gap) / 3

    captions = ["SPACE OVERVIEW", "KEY FURNITURE",
                "MATERIAL DETAIL", "LIGHTING MOOD",
                "ACCENT STYLING", "COLOUR IN SPACE"]

    for i in range(6):
        col = i % 2
        row = i // 2
        x = L_MARGIN + col * (img_w + gap)
        y = H - 43*mm - (row + 1) * img_h - row * gap

        # Placeholder background
        c.setFillColor(DARK_CARD)
        c.rect(x, y, img_w, img_h, fill=1, stroke=0)

        img_path = image_paths[i] if i < len(image_paths) else None
        if img_path and os.path.exists(img_path):
            try:
                c.drawImage(img_path, x, y, width=img_w, height=img_h,
                            preserveAspectRatio=False, mask="auto")
            except Exception as e:
                print(f"Could not draw image {img_path}: {e}")
        else:
            # Show placeholder text
            draw_text(c, captions[i] if i < len(captions) else "", x + img_w/2, y + img_h/2,
                      font="Helvetica", size=7, color=LIGHT_GREY, align="center")

        # Caption bar
        c.setFillColor(HexColor("#111111"))
        c.rect(x, y, img_w, 7*mm, fill=1, stroke=0)
        if i < len(captions):
            draw_text(c, captions[i], x + 2*mm, y + 2*mm,
                      font="Helvetica", size=5.5, color=MUTED_GOLD)

    c.showPage()


# ── PAGE 4: MATERIALS & DESIGNER NOTE ─────────────────────────────────────────
def draw_materials_page(c, form, content):
    draw_background(c, DARK_BG)
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 4, H, fill=1, stroke=0)

    draw_text(c, "MATERIALS, FINISHES & DESIGNER NOTE", L_MARGIN, H - 25*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    draw_text(c, "MATERIALS & FINISHES", L_MARGIN, H - 40*mm,
              font="Helvetica-Bold", size=12, color=OFF_WHITE)

    materials = content.get("materials_list", [])
    mat_y = H - 53*mm
    for item in materials:
        c.setFillColor(MUTED_GOLD)
        c.circle(L_MARGIN + 3*mm, mat_y + 1.5*mm, 1*mm, fill=1, stroke=0)
        lines = wrap_text_lines(item, max_chars=72)
        for j, line in enumerate(lines):
            draw_text(c, line, L_MARGIN + 8*mm, mat_y - j * 5*mm,
                      font="Helvetica", size=9.5, color=OFF_WHITE)
        mat_y -= (len(lines) * 5 + 5) * mm

    div_y = mat_y - 6*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(L_MARGIN, div_y, W - R_MARGIN, div_y)

    draw_text(c, "A NOTE FROM YOUR DESIGNER", L_MARGIN, div_y - 12*mm,
              font="Helvetica", size=7, color=MUTED_GOLD)

    note = content.get("designer_note", "")
    note_lines = wrap_text_lines(note, max_chars=75)
    note_y = div_y - 23*mm
    for line in note_lines:
        draw_text(c, line, L_MARGIN, note_y, font="Helvetica-Oblique", size=9.5, color=OFF_WHITE)
        note_y -= 6.5*mm

    note_y -= 7*mm
    draw_text(c, f"— {form.get('designer_name', '')}",
              L_MARGIN, note_y, font="Helvetica-Bold", size=11, color=MUTED_GOLD)

    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(L_MARGIN, 18*mm, W - R_MARGIN, 18*mm)

    footer = f"{form.get('project_name', '')}  ·  {form.get('client_name', '')}  ·  Prepared by {form.get('designer_name', '')}"
    draw_text(c, footer, W / 2, 11*mm, font="Helvetica", size=6.5, color=LIGHT_GREY, align="center")

    c.showPage()


# ── MAIN ──────────────────────────────────────────────────────────────────────
def build_moodboard_pdf(form: dict, content: dict, image_paths: list, output_path: str):
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle(f"{form.get('project_name', 'Moodboard')} — {form.get('client_name', '')}")
    c.setAuthor(form.get("designer_name", ""))
    draw_cover(c, form, content)
    draw_palette_page(c, content)
    draw_image_grid(c, image_paths, content)
    draw_materials_page(c, form, content)
    c.save()
    print(f"PDF saved: {output_path}")
