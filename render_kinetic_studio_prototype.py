import os
import math
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, safe_run_subprocess

def ease_out_back(x: float, c1: float = 1.70158) -> float:
    c3 = c1 + 1
    return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2)

def ease_out_cubic(x: float) -> float:
    return 1 - pow(1 - x, 3)

def clamp(val, min_v, max_v):
    return max(min_v, min(val, max_v))

# Paths
cutout_path = os.path.join(TEMP_DIR, "karaca_gourmet_prod_cutout.png")
if not os.path.exists(cutout_path):
    raise FileNotFoundError(f"Cutout image not found: {cutout_path}")

prod_img = Image.open(cutout_path).convert("RGBA")
# Target hero size: width ~ 920px
aspect = prod_img.height / prod_img.width
hero_w = 900
hero_h = int(hero_w * aspect)
prod_hero = prod_img.resize((hero_w, hero_h), Image.Resampling.LANCZOS)

# Create shadow under product
shadow_canvas = Image.new("RGBA", (hero_w + 100, 120), (0, 0, 0, 0))
s_draw = ImageDraw.Draw(shadow_canvas)
s_draw.ellipse([30, 20, hero_w + 70, 95], fill=(0, 0, 0, 160))
shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(22))

# Ambient Background (Luxury Obsidian Studio)
bg_base = Image.new("RGBA", (1080, 1920), (11, 15, 25, 255))
bg_draw = ImageDraw.Draw(bg_base)

# Radial warm glow behind product (center: 540, 860)
glow_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
g_draw = ImageDraw.Draw(glow_overlay)
for r in range(480, 40, -10):
    alpha = int(45 * (1 - r / 480) ** 1.8)
    g_draw.ellipse([540 - r, 860 - int(r*0.8), 540 + r, 860 + int(r*0.8)], fill=(245, 158, 11, alpha))
glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(30))
bg_base = Image.alpha_composite(bg_base, glow_overlay)

# Add subtle vignette lines
for y in range(350):
    a = int(120 * (1 - y / 350) ** 1.5)
    bg_draw.line([(0, y), (1080, y)], fill=(5, 8, 15, a))
for y in range(1300, 1920):
    p = (y - 1300) / 620
    a = int(160 * (p ** 1.3))
    bg_draw.line([(0, y), (1080, y)], fill=(5, 8, 15, a))

# Fonts
font_bold_path = "C:/Windows/Fonts/segoeuib.ttf"
if not os.path.exists(font_bold_path):
    font_bold_path = "C:/Windows/Fonts/arialbd.ttf"

font_hook = ImageFont.truetype(font_bold_path, 34)
font_badge = ImageFont.truetype(font_bold_path, 26)
font_title = ImageFont.truetype(font_bold_path, 32)
font_strike = ImageFont.truetype(font_bold_path, 34)
font_price = ImageFont.truetype(font_bold_path, 54)
font_pct = ImageFont.truetype(font_bold_path, 24)
font_cta = ImageFont.truetype(font_bold_path, 25)

# Render frames directory
frames_dir = os.path.join(TEMP_DIR, "kinetic_frames")
if os.path.exists(frames_dir):
    shutil.rmtree(frames_dir, ignore_errors=True)
os.makedirs(frames_dir, exist_ok=True)

fps = 30
duration = 6.8
total_frames = int(fps * duration) # 204 frames

print(f"🎬 [Kinetic Studio] Generating {total_frames} frames for 100% Original Motion Video...")

for i in range(total_frames):
    t = i / fps
    frame = bg_base.copy()
    f_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(f_overlay)

    # 1. Product Floating & Zoom Physics
    bob = math.sin(t * 2.2) * 12.0
    cur_zoom = 1.0 + 0.045 * (t / duration)
    cur_w = int(hero_w * cur_zoom)
    cur_h = int(hero_h * cur_zoom)
    cur_hero = prod_hero.resize((cur_w, cur_h), Image.Resampling.BILINEAR) if abs(cur_zoom - 1.0) > 0.005 else prod_hero

    px = (1080 - cur_w) // 2
    py = int(580 + bob)

    # Paste floor shadow
    sx = (1080 - shadow_canvas.width) // 2
    sy = py + cur_h - 75
    frame.paste(shadow_canvas, (sx, sy), shadow_canvas)

    # Paste hero product
    frame.paste(cur_hero, (px, py), cur_hero)

    # 2. Top Hook Pill (Y=200, enters at 0s-0.5s)
    hook_prog = clamp(t / 0.5, 0.0, 1.0)
    hook_y_target = 200
    hook_cur_y = int(-100 + (hook_y_target + 100) * ease_out_back(hook_prog))
    
    hook_text = "HEM TOST HEM IZGARA CANAVARI"
    h_bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
    hw = h_bbox[2] - h_bbox[0] + 64
    hh = h_bbox[3] - h_bbox[1] + 28
    hx = (1080 - hw) // 2
    
    draw.rounded_rectangle([hx, hook_cur_y, hx + hw, hook_cur_y + hh], radius=24, fill=(15, 23, 42, 220), outline=(255, 255, 255, 55), width=2)
    draw.text((hx + 32, hook_cur_y + 12), hook_text, font=font_hook, fill=(255, 255, 255, 255))

    # 3. Dynamic Spec Badge 1 (Left: "6 DİLİM DEV KAPASİTE", enters at t=0.7s)
    if t >= 0.7:
        b1_prog = clamp((t - 0.7) / 0.45, 0.0, 1.0)
        b1_x_target = 70
        b1_cur_x = int(-350 + (b1_x_target + 350) * ease_out_back(b1_prog))
        b1_y = 520
        b1_text = "⚡ 6 DİLİM DEV KAPASİTE"
        b1_bb = draw.textbbox((0, 0), b1_text, font=font_badge)
        b1_w = b1_bb[2] - b1_bb[0] + 36
        b1_h = b1_bb[3] - b1_bb[1] + 20
        draw.rounded_rectangle([b1_cur_x, b1_y, b1_cur_x + b1_w, b1_y + b1_h], radius=16, fill=(15, 23, 42, 230), outline=(245, 158, 11, 180), width=1)
        draw.text((b1_cur_x + 18, b1_y + 9), b1_text, font=font_badge, fill=(254, 240, 138, 255))

    # 4. Dynamic Spec Badge 2 (Right: "DÖKÜM ÇIKARILABİLİR PLAKA", enters at t=1.4s)
    if t >= 1.4:
        b2_prog = clamp((t - 1.4) / 0.45, 0.0, 1.0)
        b2_w_box = 440
        b2_x_target = 1080 - 70 - b2_w_box
        b2_cur_x = int(1150 - (1150 - b2_x_target) * ease_out_back(b2_prog))
        b2_y = 1180
        b2_text = "🥩 DÖKÜM ÇIKARILABİLİR PLAKA"
        b2_bb = draw.textbbox((0, 0), b2_text, font=font_badge)
        b2_w = b2_bb[2] - b2_bb[0] + 36
        b2_h = b2_bb[3] - b2_bb[1] + 20
        draw.rounded_rectangle([b2_cur_x, b2_y, b2_cur_x + b2_w, b2_y + b2_h], radius=16, fill=(15, 23, 42, 230), outline=(239, 68, 68, 180), width=1)
        draw.text((b2_cur_x + 18, b2_y + 9), b2_text, font=font_badge, fill=(254, 202, 202, 255))

    # 5. Bottom Floating Deal Card (Y=1430, enters at 0.2s - 0.7s)
    card_prog = clamp((t - 0.2) / 0.5, 0.0, 1.0)
    card_y_target = 1430
    card_cur_y = int(2000 - (2000 - card_y_target) * ease_out_back(card_prog))
    card_x1 = 60
    card_x2 = 1020
    card_h = 280
    card_cur_y2 = card_cur_y + card_h
    card_r = 32

    # Card border glow
    glow_col = (16, 185, 129, 130) if t >= 2.5 else (245, 158, 11, 100)
    draw.rounded_rectangle([card_x1 - 3, card_cur_y - 3, card_x2 + 3, card_cur_y2 + 3], radius=card_r + 3, fill=(15, 23, 42, 25), outline=glow_col, width=2)
    draw.rounded_rectangle([card_x1, card_cur_y, card_x2, card_cur_y2], radius=card_r, fill=(10, 15, 29, 240), outline=(255, 255, 255, 45), width=1)

    # Row 1: Title & Badge
    title_text = "Karaca Gastro Gourmet Inox • 6 Dilim"
    draw.text((card_x1 + 32, card_cur_y + 25), title_text, font=font_title, fill=(248, 250, 252, 255))

    # Badge Top-Right
    if t < 2.5:
        badge_text = "FIRSAT HESAPLANIYOR"
        b_bg = (217, 119, 6, 230)
        b_border = (245, 158, 11, 220)
    else:
        badge_text = "DEV İNDİRİM"
        b_bg = (234, 88, 12, 230)
        b_border = (251, 146, 60, 220)

    bb_box = draw.textbbox((0, 0), badge_text, font=font_pct)
    bw = bb_box[2] - bb_box[0] + 28
    bh = bb_box[3] - bb_box[1] + 16
    bx2 = card_x2 - 32
    bx1 = bx2 - bw
    by1 = card_cur_y + 22
    draw.rounded_rectangle([bx1, by1, bx2, by1 + bh], radius=12, fill=b_bg, outline=b_border, width=1)
    draw.text((bx1 + 14, by1 + 7), badge_text, font=font_pct, fill=(255, 255, 255, 255))

    draw.line([(card_x1 + 32, card_cur_y + 82), (card_x2 - 32, card_cur_y + 82)], fill=(255, 255, 255, 25), width=1)

    # Row 2: Price Comparison
    old_p_str = "7.999 TL"
    draw.text((card_x1 + 32, card_cur_y + 105), old_p_str, font=font_strike, fill=(148, 163, 184, 255))
    s_bb = draw.textbbox((card_x1 + 32, card_cur_y + 105), old_p_str, font=font_strike)
    mid_y = (s_bb[1] + s_bb[3]) // 2
    draw.line([(s_bb[0] - 4, mid_y), (s_bb[2] + 4, mid_y)], fill=(239, 68, 68, 255), width=3)

    arrow_x = s_bb[2] + 24
    draw.text((arrow_x, card_cur_y + 105), "->", font=font_strike, fill=(148, 163, 184, 255))

    # Mystery vs Revealed Price
    if t < 2.5:
        p_text = "??? TL"
        p_col = (245, 158, 11, 255)
        tag_text = "KİLİTLİ FİYAT"
        tag_bg = (79, 70, 229, 235)
        tag_bd = (99, 102, 241, 220)
    else:
        p_text = "3.999 TL"
        p_col = (16, 185, 129, 255)
        tag_text = "-%50 NET İNDİRİM"
        tag_bg = (225, 29, 72, 235)
        tag_bd = (244, 63, 94, 220)

    p_x = arrow_x + 48
    draw.text((p_x, card_cur_y + 92), p_text, font=font_price, fill=p_col)

    p_bb = draw.textbbox((p_x, card_cur_y + 92), p_text, font=font_price)
    t_bb = draw.textbbox((0, 0), tag_text, font=font_pct)
    tw = t_bb[2] - t_bb[0] + 22
    th = t_bb[3] - t_bb[1] + 16
    tx1 = p_bb[2] + 24
    ty1 = card_cur_y + 104
    draw.rounded_rectangle([tx1, ty1, tx1 + tw, ty1 + th], radius=10, fill=tag_bg, outline=tag_bd, width=1)
    draw.text((tx1 + 11, ty1 + 7), tag_text, font=font_pct, fill=(255, 255, 255, 255))

    draw.line([(card_x1 + 32, card_cur_y + 188), (card_x2 - 32, card_cur_y + 188)], fill=(255, 255, 255, 25), width=1)

    # Row 3: Call to action
    cta_text = 'Yoruma "LİNK" yaz -> Satın alma linki DM kutuna gelsin! • Kod: #141'
    draw.text((card_x1 + 32, card_cur_y + 215), cta_text, font=font_cta, fill=(253, 224, 71, 255))

    final_frame = Image.alpha_composite(frame, f_overlay)
    frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
    final_frame.convert("RGB").save(frame_path, "PNG")

print("✅ All 204 frames rendered! Now encoding to 1080x1920 MP4 video...")

# Encode to MP4 with FFmpeg
out_video = os.path.join(OUTPUT_DIR, "prototype_kinetic_studio_karaca.mp4")
audio_track = os.path.join(BASE_DIR, "assets", "audio", "viral_bass.m4a")

cmd_ffmpeg = [
    "ffmpeg", "-y",
    "-r", "30",
    "-i", os.path.join(frames_dir, "frame_%04d.png"),
    "-i", audio_track,
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    "-movflags", "+faststart",
    out_video
]

res = safe_run_subprocess(cmd_ffmpeg, capture_output=True, text=True)
if os.path.exists(out_video) and os.path.getsize(out_video) > 100000:
    print(f"🎉 [SUCCESS] Kinetic Studio Prototype Video Ready: {out_video} (Size: {os.path.getsize(out_video)} bytes)")
else:
    print(f"❌ Failed: {res.stderr}")
