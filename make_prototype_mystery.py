import os
from PIL import Image, ImageDraw, ImageFont
from config import TEMP_DIR

bg_path = os.path.join(TEMP_DIR, "karaca_fullscreen_bg.png")
base = Image.open(bg_path).convert("RGBA")
if base.size != (1080, 1920):
    base = base.resize((1080, 1920), Image.Resampling.LANCZOS)

overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# Top and bottom vignettes
for y in range(400):
    alpha = int(140 * (1 - y / 400) ** 1.4)
    draw.line([(0, y), (1080, y)], fill=(10, 15, 28, alpha))

for y in range(1250, 1920):
    progress = (y - 1250) / 670
    alpha = int(200 * (progress ** 1.2))
    draw.line([(0, y), (1080, y)], fill=(10, 15, 28, alpha))

# Fonts
font_bold_path = "C:/Windows/Fonts/segoeuib.ttf"
if not os.path.exists(font_bold_path):
    font_bold_path = "C:/Windows/Fonts/arialbd.ttf"

font_hook = ImageFont.truetype(font_bold_path, 34)
font_title = ImageFont.truetype(font_bold_path, 32)
font_strike = ImageFont.truetype(font_bold_path, 34)
font_price = ImageFont.truetype(font_bold_path, 54)
font_pct = ImageFont.truetype(font_bold_path, 24)
font_cta = ImageFont.truetype(font_bold_path, 25)

# 2. TOP HOOK PILL
hook_text = "HEM TOST HEM IZGARA CANAVARI"
hook_bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
h_w = hook_bbox[2] - hook_bbox[0]
h_h = hook_bbox[3] - hook_bbox[1]
pill_w = h_w + 64
pill_h = h_h + 30
pill_x = (1080 - pill_w) // 2
pill_y = 210

draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=24, fill=(15, 23, 42, 215), outline=(255, 255, 255, 60), width=2)
draw.text((pill_x + 32, pill_y + 13), hook_text, font=font_hook, fill=(255, 255, 255, 255))

# 3. BOTTOM FLOATING CARD (Mystery State at 0s-2.5s)
card_x1 = 60
card_y1 = 1430
card_x2 = 1020
card_y2 = 1710
card_r = 32

draw.rounded_rectangle([card_x1 - 3, card_y1 - 3, card_x2 + 3, card_y2 + 3], radius=card_r + 3, fill=(245, 158, 11, 25), outline=(245, 158, 11, 120), width=2)
draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=card_r, fill=(10, 15, 29, 238), outline=(255, 255, 255, 45), width=1)

# Row 1: Title & Badge
title_text = "Karaca Gastro Gourmet Inox • 6 Dilim"
draw.text((card_x1 + 32, card_y1 + 25), title_text, font=font_title, fill=(248, 250, 252, 255))

badge_text = "FIRSAT HESAPLANIYOR"
b_bbox = draw.textbbox((0, 0), badge_text, font=font_pct)
bw = b_bbox[2] - b_bbox[0] + 28
bh = b_bbox[3] - b_bbox[1] + 16
bx2 = card_x2 - 32
bx1 = bx2 - bw
by1 = card_y1 + 22
draw.rounded_rectangle([bx1, by1, bx2, by1 + bh], radius=12, fill=(217, 119, 6, 230), outline=(245, 158, 11, 220), width=1)
draw.text((bx1 + 14, by1 + 7), badge_text, font=font_pct, fill=(255, 255, 255, 255))

draw.line([(card_x1 + 32, card_y1 + 82), (card_x2 - 32, card_y1 + 82)], fill=(255, 255, 255, 25), width=1)

# Row 2: Mystery State
old_price = "7.999 TL"
draw.text((card_x1 + 32, card_y1 + 105), old_price, font=font_strike, fill=(148, 163, 184, 255))
s_bbox = draw.textbbox((card_x1 + 32, card_y1 + 105), old_price, font=font_strike)
mid_y = (s_bbox[1] + s_bbox[3]) // 2
draw.line([(s_bbox[0] - 4, mid_y), (s_bbox[2] + 4, mid_y)], fill=(239, 68, 68, 255), width=3)

arrow_x = s_bbox[2] + 24
draw.text((arrow_x, card_y1 + 105), "->", font=font_strike, fill=(148, 163, 184, 255))

mystery_price = "??? TL"
price_x = arrow_x + 48
draw.text((price_x, card_y1 + 92), mystery_price, font=font_price, fill=(245, 158, 11, 255))

m_bbox = draw.textbbox((price_x, card_y1 + 92), mystery_price, font=font_price)
lock_text = "KİLİTLİ FİYAT"
lock_bbox = draw.textbbox((0, 0), lock_text, font=font_pct)
lw = lock_bbox[2] - lock_bbox[0] + 22
lh = lock_bbox[3] - lock_bbox[1] + 16
lx1 = m_bbox[2] + 24
ly1 = card_y1 + 104
draw.rounded_rectangle([lx1, ly1, lx1 + lw, ly1 + lh], radius=10, fill=(79, 70, 229, 235), outline=(99, 102, 241, 220), width=1)
draw.text((lx1 + 11, ly1 + 7), lock_text, font=font_pct, fill=(255, 255, 255, 255))

draw.line([(card_x1 + 32, card_y1 + 188), (card_x2 - 32, card_y1 + 188)], fill=(255, 255, 255, 25), width=1)

# Row 3: Call to action
cta_text = 'Yoruma "LİNK" yaz -> Satın alma linki DM kutuna gelsin! • Kod: #141'
draw.text((card_x1 + 32, card_y1 + 215), cta_text, font=font_cta, fill=(253, 224, 71, 255))

final_img = Image.alpha_composite(base, overlay)
out_path = os.path.join(TEMP_DIR, "prototype_fullscreen_mystery.png")
final_img.convert("RGB").save(out_path, quality=95)
print("Saved mystery prototype to:", out_path)
