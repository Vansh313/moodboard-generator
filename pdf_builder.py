import os
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

W, H = A4  # 595 x 842 pts

# ── Colour constants ──────────────────────────────────────────────────────────
DARK_BG    = HexColor("#1A1A1A")
DARK_CARD  = HexColor("#242424")
OFF_WHITE  = HexColor("#F5F0EB")
MUTED_GOLD = HexColor("#C9A96E")
LIGHT_GREY = HexColor("#888888")


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


def wrap_text_lines(text: str, max_chars: int = 72) -> list:
    """Wrap text into lines of max_chars."""
    words = text.split()
    lines = []
    current = ""
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
    """Download logo image bytes. Returns BytesIO or None."""
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

    # Gold accent bar (left side)
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 6, H, fill=1, stroke=0)

    # Top label
    draw_text(c, "INTERIOR MOODBOARD", 30*mm, H - 28*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    # Mood title — large
    title = content.get("mood_title", "Design Vision").upper()
    # Split title into lines if long
    title_words = title.split()
    if len(title_words) <= 3:
        title_lines = [title]
    else:
        mid = len(title_words) // 2
        title_lines = [" ".join(title_words[:mid]), " ".join(title_words[mid:])]

    y = H - 80*mm
    for line in title_lines:
        draw_text(c, line, W / 2, y, font="Helvetica-Bold", size=38, color=OFF_WHITE, align="center")
        y -= 14*mm

    # Tagline
    tagline = content.get("tagline", "")
    tagline_lines = wrap_text_lines(tagline, max_chars=55)
    y -= 6*mm
    for line in tagline_lines:
        draw_text(c, line, W / 2, y, font="Helvetica-Oblique", size=11, color=LIGHT_GREY, align="center")
        y -= 7*mm

    # Divider
    y -= 8*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.5)
    c.line(50*mm, y, W - 50*mm, y)
    y -= 10*mm

    # Project info block
    info_items = [
        ("CLIENT",  form.get("client_name", "")),
        ("PROJECT", form.get("project_name", "")),
        ("STYLE",   form.get("design_style", "")),
        ("ROOMS",   form.get("room_types", "")),
    ]
    for label, value in info_items:
        if value:
            draw_text(c, label, W / 2 - 40*mm, y, font="Helvetica", size=7, color=MUTED_GOLD)
            draw_text(c, value, W / 2 - 40*mm, y - 5*mm, font="Helvetica-Bold", size=10, color=OFF_WHITE)
            y -= 16*mm

    # Logo (bottom area)
    logo_data = fetch_logo(form.get("logo_url", ""))
    if logo_data:
        try:
            c.drawImage(logo_data, W / 2 - 20*mm, 30*mm, width=40*mm, height=15*mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Designer credit (bottom)
    draw_text(c, f"PREPARED BY  {form.get('designer_name', '').upper()}", W / 2, 22*mm,
              font="Helvetica", size=8, color=LIGHT_GREY, align="center")

    c.showPage()


# ── PAGE 2: PALETTE & MOOD ────────────────────────────────────────────────────
def draw_palette_page(c, content):
    draw_background(c, DARK_BG)

    # Gold accent bar
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 6, H, fill=1, stroke=0)

    # Section label
    draw_text(c, "COLOUR PALETTE & MOOD", 30*mm, H - 28*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    # Color swatches
    palette = content.get("color_palette", [])
    swatch_w = 32*mm
    swatch_h = 22*mm
    total_w = len(palette) * swatch_w + (len(palette) - 1) * 4*mm
    start_x = (W - total_w) / 2
    swatch_y = H - 75*mm

    for i, color_item in enumerate(palette):
        x = start_x + i * (swatch_w + 4*mm)
        col = hex_to_color(color_item.get("hex", "#888888"))

        # Swatch rectangle
        c.setFillColor(col)
        c.roundRect(x, swatch_y, swatch_w, swatch_h, 2*mm, fill=1, stroke=0)

        # Hex code
        draw_text(c, color_item.get("hex", "").upper(), x + swatch_w / 2,
                  swatch_y - 5*mm, font="Helvetica", size=7, color=LIGHT_GREY, align="center")

        # Color name
        name = color_item.get("name", "")
        if len(name) > 12:
            name = name[:11] + "…"
        draw_text(c, name, x + swatch_w / 2, swatch_y - 10*mm,
                  font="Helvetica-Bold", size=8, color=OFF_WHITE, align="center")

        # Role badge
        role = color_item.get("role", "")
        draw_text(c, role.upper(), x + swatch_w / 2, swatch_y - 15*mm,
                  font="Helvetica", size=6, color=MUTED_GOLD, align="center")

    # Divider
    div_y = swatch_y - 22*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(30*mm, div_y, W - 30*mm, div_y)

    # Mood description
    draw_text(c, "THE VISION", 30*mm, div_y - 12*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    description = content.get("mood_description", "")
    lines = wrap_text_lines(description, max_chars=80)
    text_y = div_y - 22*mm
    for line in lines:
        draw_text(c, line, 30*mm, text_y, font="Helvetica", size=10, color=OFF_WHITE)
        text_y -= 6.5*mm

    # Style badge
    style_badge_y = text_y - 10*mm
    draw_text(c, "DESIGN DIRECTION", 30*mm, style_badge_y,
              font="Helvetica", size=7, color=MUTED_GOLD)
    style_text = content.get("mood_title", "").upper()
    draw_text(c, style_text, 30*mm, style_badge_y - 8*mm,
              font="Helvetica-Bold", size=14, color=OFF_WHITE)

    c.showPage()


# ── PAGE 3: IMAGE GRID ────────────────────────────────────────────────────────
def draw_image_grid(c, image_paths, content):
    draw_background(c, DARK_BG)

    # Gold accent bar
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 6, H, fill=1, stroke=0)

    draw_text(c, "MOODBOARD IMAGERY", 30*mm, H - 28*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    # 2x3 grid layout
    margin = 20*mm
    gap = 4*mm
    img_w = (W - 2 * margin - gap) / 2
    img_h = (H - 55*mm - 2 * gap) / 3

    captions = [
        "SPACE OVERVIEW", "KEY FURNITURE",
        "MATERIAL DETAIL", "LIGHTING MOOD",
        "ACCENT STYLING", "COLOUR IN SPACE"
    ]

    for i, img_path in enumerate(image_paths[:6]):
        col = i % 2
        row = i // 2

        x = margin + col * (img_w + gap)
        y = H - 45*mm - (row + 1) * img_h - row * gap

        # Background placeholder
        c.setFillColor(DARK_CARD)
        c.rect(x, y, img_w, img_h, fill=1, stroke=0)

        # Draw image if available
        if img_path and os.path.exists(img_path):
            try:
                c.drawImage(img_path, x, y, width=img_w, height=img_h,
                            preserveAspectRatio=False, mask="auto")
            except Exception as e:
                print(f"Could not draw image {img_path}: {e}")

        # Caption overlay (bottom of image)
        c.setFillColor(HexColor("#00000066"))
        c.rect(x, y, img_w, 8*mm, fill=1, stroke=0)

        if i < len(captions):
            draw_text(c, captions[i], x + 3*mm, y + 2.5*mm,
                      font="Helvetica", size=6, color=MUTED_GOLD)

    c.showPage()


# ── PAGE 4: MATERIALS & DESIGNER NOTE ─────────────────────────────────────────
def draw_materials_page(c, form, content):
    draw_background(c, DARK_BG)

    # Gold accent bar
    c.setFillColor(MUTED_GOLD)
    c.rect(0, 0, 6, H, fill=1, stroke=0)

    draw_text(c, "MATERIALS, FINISHES & DESIGNER NOTE", 30*mm, H - 28*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    # Materials section
    draw_text(c, "MATERIALS & FINISHES", 30*mm, H - 45*mm,
              font="Helvetica-Bold", size=13, color=OFF_WHITE)

    materials = content.get("materials_list", [])
    mat_y = H - 58*mm
    for item in materials:
        # Bullet dot
        c.setFillColor(MUTED_GOLD)
        c.circle(33*mm, mat_y + 1.5*mm, 1.2*mm, fill=1, stroke=0)

        lines = wrap_text_lines(item, max_chars=70)
        for j, line in enumerate(lines):
            draw_text(c, line, 37*mm, mat_y - j * 5.5*mm,
                      font="Helvetica", size=10, color=OFF_WHITE)
        mat_y -= (len(lines) * 5.5 + 5) * mm

    # Divider
    div_y = mat_y - 8*mm
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(30*mm, div_y, W - 30*mm, div_y)

    # Designer note
    draw_text(c, "A NOTE FROM YOUR DESIGNER", 30*mm, div_y - 14*mm,
              font="Helvetica", size=8, color=MUTED_GOLD)

    note = content.get("designer_note", "")
    note_lines = wrap_text_lines(note, max_chars=78)
    note_y = div_y - 26*mm
    for line in note_lines:
        draw_text(c, line, 30*mm, note_y, font="Helvetica-Oblique", size=10, color=OFF_WHITE)
        note_y -= 7*mm

    # Signature
    note_y -= 8*mm
    draw_text(c, f"— {form.get('designer_name', '')}",
              30*mm, note_y, font="Helvetica-Bold", size=11, color=MUTED_GOLD)

    # Footer
    c.setStrokeColor(MUTED_GOLD)
    c.setLineWidth(0.3)
    c.line(30*mm, 20*mm, W - 30*mm, 20*mm)

    footer_text = f"{form.get('project_name', '')}  ·  {form.get('client_name', '')}  ·  Prepared by {form.get('designer_name', '')}"
    draw_text(c, footer_text, W / 2, 13*mm,
              font="Helvetica", size=7, color=LIGHT_GREY, align="center")

    c.showPage()


# ── MAIN BUILD FUNCTION ────────────────────────────────────────────────────────
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
