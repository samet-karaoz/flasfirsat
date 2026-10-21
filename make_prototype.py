import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR

bg_path = os.path.join(TEMP_DIR, "karaca_fullscreen_bg.png")
base = Image.open(bg_path).convert("RGBA")
if base.size != (1080, 1920):
    base = base.resize((1080, 1920), Image.Resampling.LANCZOS)

# Create an overlay layer for glassmorphism and vignettes
overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# 1. Subtle top and bottom vignettes for high contrast
# Top vignette (Y=0 to 380)
for y in range(380):
    alpha = int(140 * (1 - y / 380) ** 1.5)
    draw.line([(0, y), (1080, y)], fill=(10, 15, 28, alpha))

# Bottom vignette (Y=1300 to 1920)
for y in range(1300, 1920):
    progress = (y - 1300) / 620
    alpha = int(180 * (progress ** 1.2))
    draw.line([(0, y), (1080, y)], fill=(10, 15, 28, alpha))

# Fonts
font_bold_path = "C:/Windows/Fonts/segoeuib.ttf"
if not os.path.exists(font_bold_path):
    font_bold_path = "C:/Windows/Fonts/arialbd.ttf"

font_hook = ImageFont.truetype(font_bold_path, 36)
font_title = ImageFont.truetype(font_bold_path, 34)
font_strike = ImageFont.truetype(font_bold_path, 36)
font_price = ImageFont.truetype(font_bold_path, 56)
font_pct = ImageFont.truetype(font_bold_path, 26)
font_cta = ImageFont.truetype(font_bold_path, 25)

# 2. TOP HOOK PILL (Y=210)
hook_text = "HEM TOST HEM IZGARA CANAVARI! 🥩🥪"
hook_bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
h_w = hook_bbox[2] - hook_bbox[0]
h_h = hook_bbox[3] - hook_bbox[1]

pill_w = h_w + 60
pill_h = h_h + 32
pill_x = (1080 - pill_w) // 2
pill_y = 210

# Draw rounded dark glass pill
draw.rounded_rectangle(
    [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
    radius=26,
    fill=(15, 23, 42, 210),
    outline=(255, 255, 255, 50),
    width=2
)
# Draw Hook Text
draw.text((pill_x + 30, pill_y + 14), hook_text, font=font_hook, fill=(255, 255, 255, 255))

# 3. BOTTOM FLOATING DEAL CARD (Glassmorphism)
card_x1 = 60
card_y1 = 1430
card_x2 = 1020
card_y2 = 1710
card_r = 32

# Outer subtle neon shadow/rim
draw.rounded_rectangle(
    [card_x1 - 3, card_y1 - 3, card_x2 + 3, card_y2 + 3],
    radius=card_r + 3,
    fill=(16, 185, 129, 30),
    outline=(16, 185, 129, 90),
    width=2
)

# Main Card Body (Dark Obsidian Glass)
draw.rounded_rectangle(
    [card_x1, card_y1, card_x2, card_y2],
    radius=card_r,
    fill=(10, 15, 29, 235),
    outline=(255, 255, 255, 45),
    width=1
)

# Row 1: Title & Badge
title_text = "Karaca Gastro Gourmet Inox • 6 Dilim"
draw.text((card_x1 + 32, card_y1 + 26), title_text, font=font_title, fill=(248, 250, 252, 255))

# Top-Right Badge: DEV İNDİRİM
badge_text = "⚡ DEV İNDİRİM"
b_bbox = draw.textbbox((0, 0), badge_text, font=font_pct)
bw = b_bbox[2] - b_bbox[0] + 24
bh = b_bbox[3] - b_bbox[1] + 14
bx2 = card_x2 - 32
bx1 = bx2 - bw
by1 = card_y1 + 24
draw.rounded_rectangle([bx1, by1, bx2, by1 + bh], radius=12, fill=(234, 88, 12, 220), outline=(251, 146, 60, 200), width=1)
draw.text((bx1 + 12, by1 + 6), badge_text, font=font_pct, fill=(255, 255, 255, 255))

# Separator Line
draw.line([(card_x1 + 32, card_y1 + 82), (card_x2 - 32, card_y1 + 82)], fill=(255, 255, 255, 25), width=1)

# Row 2: Price Comparison
# Strike price
old_price = "7.999 TL"
draw.text((card_x1 + 32, card_y1 + 105), old_price, font=font_strike, fill=(148, 163, 184, 255))
s_bbox = draw.textbbox((card_x1 + 32, card_y1 + 105), old_price, font=font_strike)
mid_y = (s_bbox[1] + s_bbox[3]) // 2
draw.line([(s_bbox[0] - 4, mid_y), (s_bbox[2] + 4, mid_y)], fill=(239, 68, 68, 255), width=3)

# Arrow
arrow_x = s_bbox[2] + 24
draw.text((arrow_x, card_y1 + 105), "➔", font=font_strike, fill=(100, 116, 139, 255))

# New Price (Glowing Emerald)
new_price = "3.999 TL"
price_x = arrow_x + 40
draw.text((price_x, card_y1 + 92), new_price, font=font_price, fill=(16, 185, 129, 255))

# Discount Tag Pill next to new price
p_bbox = draw.textbbox((price_x, card_y1 + 92), new_price, font=font_price)
pct_text = "-%50 İNDİRİM"
pct_bbox = draw.textbbox((0, 0), pct_text, font=font_pct)
pct_w = pct_bbox[2] - pct_bbox[0] + 20
pct_h = pct_bbox[3] - pct_bbox[1] + 14
pct_x1 = p_bbox[2] + 20
pct_y1 = card_y1 + 106
draw.rounded_rectangle([pct_x1, pct_y1, pct_x1 + pct_w, pct_y1 + pct_h], radius=10, fill=(225, 29, 72, 230), outline=(244, 63, 94, 200), width=1)
draw.text((pct_x1 + 10, pct_y1 + 6), pct_text, font=font_pct, fill=(255, 255, 255, 255))

# Separator Line 2
draw.line([(card_x1 + 32, card_y1 + 190), (card_x2 - 32, card_y1 + 190)], fill=(255, 255, 255, 25), width=1)

# Row 3: Call to action
cta_text = "💬 Yoruma 'LİNK' yaz ➔ Link DM'ne gelsin! • Kod: #141"
draw.text((card_x1 + 36, card_y1 + 215), cta_text, font=font_cta, fill=(253, 224, 71, 255))

# Merge layers
final_img = Image.alpha_composite(base, overlay)
out_path = os.path.join(TEMP_DIR, "prototype_fullscreen_v1.png")
final_img.convert("RGB").save(out_path, quality=95)
print("Saved prototype to:", out_path)
