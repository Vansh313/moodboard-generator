import re

with open("moodboard_page_builder.py", "r") as f:
    content = f.read()

old_layouts = '''    layouts = [
        {"top": "3%",  "left": "38%", "width": "58%",  "rotate": "1deg",   "z": 2},
        {"top": "2%",  "left": "2%",  "width": "34%",  "rotate": "-2deg",  "z": 3},
        {"top": "22%", "left": "2%",  "width": "30%",  "rotate": "1.5deg", "z": 2},
        {"top": "30%", "left": "55%", "width": "22%",  "rotate": "-1deg",  "z": 3},
        {"top": "30%", "left": "75%", "width": "24%",  "rotate": "2deg",   "z": 2},
        {"top": "42%", "left": "15%", "width": "32%",  "rotate": "-1.5deg","z": 3},
        {"top": "44%", "left": "48%", "width": "28%",  "rotate": "1deg",   "z": 2},
        {"top": "56%", "left": "5%",  "width": "88%",  "rotate": "0deg",   "z": 1},
    ]'''

new_layouts = '''    layouts = [
        {"top": "2%",  "left": "40%", "width": "56%",  "rotate": "1.5deg",  "z": 2},
        {"top": "3%",  "left": "2%",  "width": "36%",  "rotate": "-2deg",   "z": 3},
        {"top": "28%", "left": "3%",  "width": "28%",  "rotate": "1deg",    "z": 2},
        {"top": "32%", "left": "34%", "width": "30%",  "rotate": "-1.5deg", "z": 3},
        {"top": "28%", "left": "66%", "width": "32%",  "rotate": "2deg",    "z": 2},
        {"top": "54%", "left": "5%",  "width": "42%",  "rotate": "-1deg",   "z": 3},
        {"top": "52%", "left": "50%", "width": "46%",  "rotate": "1.5deg",  "z": 2},
        {"top": "72%", "left": "20%", "width": "60%",  "rotate": "-0.5deg", "z": 1},
    ]'''

new_layouts_height = '''  .collage {
    position: relative;
    width: 100%;
    height: 140vw;
    max-height: 950px;
    margin: 1rem 0;
  }'''

old_layouts_height = '''  .collage {
    position: relative;
    width: 100%;
    height: 75vw;
    max-height: 510px;
    margin: 1rem 0;
  }'''

content = content.replace(old_layouts, new_layouts)
content = content.replace(old_layouts_height, new_layouts_height)

with open("moodboard_page_builder.py", "w") as f:
    f.write(content)

print("Done")
