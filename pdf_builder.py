import os, requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white

W, H = A4
DARK_BG=HexColor("#1A1A1A"); DARK_CARD=HexColor("#242424"); OFF_WHITE=HexColor("#F5F0EB"); MUTED_GOLD=HexColor("#C9A96E"); LIGHT_GREY=HexColor("#888888")
L_MARGIN=25*mm; R_MARGIN=25*mm; CONTENT_W=W-L_MARGIN-R_MARGIN

def hex_to_color(h):
    try: return HexColor(f"#{h.strip().lstrip('#')}")
    except: return HexColor("#888888")

def draw_background(c, color=None):
    c.setFillColor(color or DARK_BG); c.rect(0,0,W,H,fill=1,stroke=0)

def draw_text(c, text, x, y, font="Helvetica", size=12, color=white, align="left"):
    c.setFont(font,size); c.setFillColor(color)
    if align=="center": c.drawCentredString(x,y,text)
    elif align=="right": c.drawRightString(x,y,text)
    else: c.drawString(x,y,text)

def wrap_text_lines(text, max_chars=65):
    words=text.split(); lines,current=[],""
    for w in words:
        if len(current)+len(w)+1<=max_chars: current=(current+" "+w).strip()
        else:
            if current: lines.append(current)
            current=w
    if current: lines.append(current)
    return lines

def fetch_logo(url):
    if not url or not url.startswith("http"): return None
    try: r=requests.get(url,timeout=10); r.raise_for_status(); return BytesIO(r.content)
    except: return None

def draw_cover(c, form, content):
    draw_background(c)
    c.setFillColor(MUTED_GOLD); c.rect(0,0,4,H,fill=1,stroke=0)
    draw_text(c,"INTERIOR MOODBOARD",L_MARGIN,H-25*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    title=content.get("mood_title","Design Vision").upper()
    words=title.split()
    if len(words)<=2: lines=[title]
    elif len(words)<=4: m=len(words)//2; lines=[" ".join(words[:m])," ".join(words[m:])]
    else: t=len(words)//3; lines=[" ".join(words[:t])," ".join(words[t:2*t])," ".join(words[2*t:])]
    y=H-70*mm
    for line in lines: draw_text(c,line,W/2,y,font="Helvetica-Bold",size=32,color=OFF_WHITE,align="center"); y-=12*mm
    y-=4*mm
    for line in wrap_text_lines(content.get("tagline",""),50): draw_text(c,line,W/2,y,font="Helvetica-Oblique",size=10,color=LIGHT_GREY,align="center"); y-=6.5*mm
    y-=6*mm; c.setStrokeColor(MUTED_GOLD); c.setLineWidth(0.5); c.line(60*mm,y,W-60*mm,y); y-=10*mm
    for label,value in [("CLIENT",form.get("client_name","")),("PROJECT",form.get("project_name","")),("STYLE",form.get("design_style","")),("ROOMS",form.get("room_types",""))]:
        if value:
            draw_text(c,label,L_MARGIN+10*mm,y,font="Helvetica",size=7,color=MUTED_GOLD)
            draw_text(c,(value[:45]+"…" if len(value)>45 else value),L_MARGIN+10*mm,y-5*mm,font="Helvetica-Bold",size=10,color=OFF_WHITE); y-=15*mm
    logo=fetch_logo(form.get("logo_url",""))
    if logo:
        try: c.drawImage(logo,W/2-20*mm,32*mm,width=40*mm,height=15*mm,preserveAspectRatio=True,mask="auto")
        except: pass
    draw_text(c,f"PREPARED BY  {form.get('designer_name','').upper()}",W/2,22*mm,font="Helvetica",size=7,color=LIGHT_GREY,align="center")
    c.showPage()

def draw_palette_page(c, content):
    draw_background(c)
    c.setFillColor(MUTED_GOLD); c.rect(0,0,4,H,fill=1,stroke=0)
    draw_text(c,"COLOUR PALETTE & MOOD",L_MARGIN,H-25*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    palette=content.get("color_palette",[]); n=len(palette)
    gap=3*mm; sw=(CONTENT_W-(n-1)*gap)/n if n>0 else 30*mm; sh=20*mm; sy=H-70*mm
    for i,ci in enumerate(palette):
        x=L_MARGIN+i*(sw+gap); c.setFillColor(hex_to_color(ci.get("hex","#888888"))); c.roundRect(x,sy,sw,sh,1.5*mm,fill=1,stroke=0)
        cx=x+sw/2
        draw_text(c,ci.get("hex","").upper(),cx,sy-5*mm,font="Helvetica",size=6,color=LIGHT_GREY,align="center")
        name=ci.get("name",""); name=name[:10]+"…" if len(name)>11 else name
        draw_text(c,name,cx,sy-9.5*mm,font="Helvetica-Bold",size=7,color=OFF_WHITE,align="center")
        draw_text(c,ci.get("role","").upper(),cx,sy-14*mm,font="Helvetica",size=5.5,color=MUTED_GOLD,align="center")
    div_y=sy-20*mm; c.setStrokeColor(MUTED_GOLD); c.setLineWidth(0.3); c.line(L_MARGIN,div_y,W-R_MARGIN,div_y)
    draw_text(c,"THE VISION",L_MARGIN,div_y-10*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    ty=div_y-20*mm
    for line in wrap_text_lines(content.get("mood_description",""),75): draw_text(c,line,L_MARGIN,ty,font="Helvetica",size=9.5,color=OFF_WHITE); ty-=6*mm
    ty-=8*mm; draw_text(c,"DESIGN DIRECTION",L_MARGIN,ty,font="Helvetica",size=7,color=MUTED_GOLD)
    draw_text(c,content.get("mood_title","").upper(),L_MARGIN,ty-7*mm,font="Helvetica-Bold",size=13,color=OFF_WHITE)
    c.showPage()

def draw_image_grid(c, image_paths, content, products=None, captions=None):
    draw_background(c)
    c.setFillColor(MUTED_GOLD); c.rect(0,0,4,H,fill=1,stroke=0)
    draw_text(c,"MOODBOARD IMAGERY",L_MARGIN,H-25*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    gap=3*mm; iw=(CONTENT_W-gap)/2; ih=(H-50*mm-2*gap)/3
    captions=["SPACE OVERVIEW","KEY FURNITURE","MATERIAL DETAIL","LIGHTING MOOD","ACCENT STYLING","COLOUR IN SPACE"]
    if not products: products=[]

    for i in range(6):
        col=i%2; row=i//2
        x=L_MARGIN+col*(iw+gap); y=H-43*mm-(row+1)*ih-row*gap
        c.setFillColor(DARK_CARD); c.rect(x,y,iw,ih,fill=1,stroke=0)

        img_path=image_paths[i] if i<len(image_paths) else None
        product=products[i] if i<len(products) else None

        if img_path and os.path.exists(img_path):
            try: c.drawImage(img_path,x,y,width=iw,height=ih,preserveAspectRatio=False,mask="auto")
            except Exception as e: print(f"Image draw error {i}: {e}")

        # Caption bar — taller for products
        bar_h=10*mm if product else 7*mm
        c.setFillColor(HexColor("#111111")); c.rect(x,y,iw,bar_h,fill=1,stroke=0)

        if product:
            title=product.get("title","Product")[:38]
            price=product.get("price","")
            draw_text(c,title,x+2*mm,y+6.5*mm,font="Helvetica-Bold",size=5,color=OFF_WHITE)
            draw_text(c,price,x+2*mm,y+2*mm,font="Helvetica",size=5,color=MUTED_GOLD)
            draw_text(c,"↗ SHOP",x+iw-14*mm,y+4*mm,font="Helvetica-Bold",size=5.5,color=MUTED_GOLD)
        else:
            draw_text(c,captions[i] if i<len(captions) else "",x+2*mm,y+2.5*mm,font="Helvetica",size=5.5,color=MUTED_GOLD)

    c.showPage()

def draw_materials_page(c, form, content):
    draw_background(c)
    c.setFillColor(MUTED_GOLD); c.rect(0,0,4,H,fill=1,stroke=0)
    draw_text(c,"MATERIALS, FINISHES & DESIGNER NOTE",L_MARGIN,H-25*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    draw_text(c,"MATERIALS & FINISHES",L_MARGIN,H-40*mm,font="Helvetica-Bold",size=12,color=OFF_WHITE)
    my=H-53*mm
    for item in content.get("materials_list",[]):
        c.setFillColor(MUTED_GOLD); c.circle(L_MARGIN+3*mm,my+1.5*mm,1*mm,fill=1,stroke=0)
        lines=wrap_text_lines(item,72)
        for j,line in enumerate(lines): draw_text(c,line,L_MARGIN+8*mm,my-j*5*mm,font="Helvetica",size=9.5,color=OFF_WHITE)
        my-=(len(lines)*5+5)*mm
    div_y=my-6*mm; c.setStrokeColor(MUTED_GOLD); c.setLineWidth(0.3); c.line(L_MARGIN,div_y,W-R_MARGIN,div_y)
    draw_text(c,"A NOTE FROM YOUR DESIGNER",L_MARGIN,div_y-12*mm,font="Helvetica",size=7,color=MUTED_GOLD)
    ny=div_y-23*mm
    for line in wrap_text_lines(content.get("designer_note",""),75): draw_text(c,line,L_MARGIN,ny,font="Helvetica-Oblique",size=9.5,color=OFF_WHITE); ny-=6.5*mm
    ny-=7*mm; draw_text(c,f"— {form.get('designer_name','')}",L_MARGIN,ny,font="Helvetica-Bold",size=11,color=MUTED_GOLD)
    c.setStrokeColor(MUTED_GOLD); c.setLineWidth(0.3); c.line(L_MARGIN,18*mm,W-R_MARGIN,18*mm)
    draw_text(c,f"{form.get('project_name','')}  ·  {form.get('client_name','')}  ·  Prepared by {form.get('designer_name','')}",W/2,11*mm,font="Helvetica",size=6.5,color=LIGHT_GREY,align="center")
    c.showPage()

def build_moodboard_pdf(form, content, image_paths, output_path, products=None, captions=None):
    c=canvas.Canvas(output_path,pagesize=A4)
    c.setTitle(f"{form.get('project_name','Moodboard')} — {form.get('client_name','')}")
    c.setAuthor(form.get("designer_name",""))
    draw_cover(c,form,content)
    draw_palette_page(c,content)
    draw_image_grid(c,image_paths,content,products=products,captions=captions)
    draw_materials_page(c,form,content)
    c.save()
    print(f"PDF saved: {output_path}")
