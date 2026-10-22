import os
import re
import time
import uuid
import shutil
import random
import math
import datetime
import subprocess
import imageio_ffmpeg
import json
import base64
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR, ASSETS_DIR, TEMP_DIR, GEMINI_API_KEY
from phonetic_helper import to_phonetic_turkish

FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
MASKS_DIR = os.path.join(ASSETS_DIR, "masks")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")

def get_font(font_name: str, size: int):
    candidates = [
        os.path.join(FONTS_DIR, f"{font_name}.ttf"),
        os.path.join(FONTS_DIR, "segoeuib.ttf"),
        f"C:/Windows/Fonts/{font_name}.ttf",
        f"C:/Windows/Fonts/{font_name.lower()}.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except:
                pass
    return ImageFont.load_default()

# -------------------------------------------------------------
# DİNAMİK KATEGORİ TEMALARI (Anti-Şablon Görsel Çeşitlilik)
# -------------------------------------------------------------
THEMES = {
    "sports": {
        "name": "sports",
        "badge_hdr": (14, 116, 144),        # buz/kobalt mavisi
        "card_border": (56, 189, 248, 120),  # gök mavisi kontur
        "card_bg": (11, 15, 25, 240),
        "cta_fill": (13, 148, 136, 245),     # teal CTA
        "cta_border": (45, 212, 191, 160)
    },
    "kitchen": {
        "name": "kitchen",
        "badge_hdr": (217, 119, 6),         # sıcak kehribar
        "card_border": (245, 158, 11, 130), # kehribar ışıltısı
        "card_bg": (20, 16, 12, 242),
        "cta_fill": (180, 83, 9, 245),      # bakır/amber CTA
        "cta_border": (251, 191, 36, 170)
    },
    "gaming": {
        "name": "gaming",
        "badge_hdr": (124, 58, 237),        # siber mor
        "card_border": (139, 92, 246, 135), # neon mor kontur
        "card_bg": (15, 12, 28, 242),
        "cta_fill": (109, 40, 217, 245),    # siber violet CTA
        "cta_border": (192, 132, 252, 170)
    },
    "care": {
        "name": "care",
        "badge_hdr": (13, 148, 136),        # zümrüt yeşili
        "card_border": (52, 211, 153, 130), # zümrüt kontur
        "card_bg": (10, 20, 18, 242),
        "cta_fill": (5, 150, 105, 245),     # lüks zümrüt CTA
        "cta_border": (110, 231, 183, 170)
    },
    "default": {
        "name": "default",
        "badge_hdr": (234, 88, 12),         # canlı turuncu
        "card_border": (56, 189, 248, 110), # koyu mavi kontur
        "card_bg": (11, 15, 25, 240),
        "cta_fill": (13, 148, 136, 245),
        "cta_border": (45, 212, 191, 160)
    }
}

def get_theme_for_deal(deal: dict) -> dict:
    """Ürün başlığı veya kategorisine göre en uygun renk temasını belirler."""
    text = (str(deal.get("title", "")) + " " + str(deal.get("category", ""))).lower()
    if any(k in text for k in ["ayakkabı", "sneaker", "spor", "koşu", "bot", "çizme", "adidas", "nike", "puma", "reebok"]):
        return THEMES["sports"]
    if any(k in text for k in ["kahve", "espresso", "airfryer", "tost", "ızgara", "termos", "mutfak", "karaca", "tefal", "philips latte", "blender", "tava"]):
        return THEMES["kitchen"]
    if any(k in text for k in ["mouse", "fare", "kulaklık", "klavye", "monitör", "gaming", "oyuncu", "razer", "logitech", "glorious", "steelseries", "gamepad", "dualsense"]):
        return THEMES["gaming"]
    if any(k in text for k in ["diş", "tıraş", "fön", "saç", "oral-b", "oneblade", "dyson", "braun", "epilasyon"]):
        return THEMES["care"]
    return THEMES["default"]

# -------------------------------------------------------------
# VEKTÖREL İKON ÇİZİMLERİ (Piksel Netliği & Sıfır Tofu/Kutu Hatası)
# -------------------------------------------------------------
def draw_vector_bolt(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 204, 0), scale=0.8):
    points = [
        (cx + int(3*scale), cy - int(17*scale)),
        (cx - int(9*scale), cy),
        (cx, cy),
        (cx - int(6*scale), cy + int(17*scale)),
        (cx + int(11*scale), cy - int(2*scale)),
        (cx + int(2*scale), cy - int(2*scale))
    ]
    draw.polygon(points, fill=color)

def draw_vector_shield_check(draw: ImageDraw.Draw, cx: int, cy: int, color=(16, 185, 129), scale=0.85):
    shield = [
        (cx, cy - int(11*scale)),
        (cx + int(10*scale), cy - int(7*scale)),
        (cx + int(10*scale), cy + int(3*scale)),
        (cx, cy + int(12*scale)),
        (cx - int(10*scale), cy + int(3*scale)),
        (cx - int(10*scale), cy - int(7*scale))
    ]
    draw.polygon(shield, fill=color)
    chk = [(cx - int(4*scale), cy), (cx - int(1*scale), cy + int(3*scale)), (cx + int(5*scale), cy - int(3*scale))]
    draw.line(chk, fill=(255, 255, 255), width=max(1, int(2*scale)))

def draw_vector_trend_down(draw: ImageDraw.Draw, cx: int, cy: int, color=(225, 29, 72), scale=0.85):
    points = [
        (cx - int(9*scale), cy - int(5*scale)),
        (cx - int(3*scale), cy - int(1*scale)),
        (cx + int(2*scale), cy - int(6*scale)),
        (cx + int(8*scale), cy + int(4*scale))
    ]
    draw.line(points, fill=color, width=max(1, int(2*scale)))
    draw.polygon([(cx + int(8*scale), cy + int(4*scale)), (cx + int(3*scale), cy + int(4*scale)), (cx + int(8*scale), cy - int(1*scale))], fill=color)

def draw_vector_sparkle(draw: ImageDraw.Draw, cx: int, cy: int, size: int = 7, color=(251, 191, 36)):
    s = size
    k = s * 0.3
    points = [
        (cx, cy - s),
        (cx + k, cy - k),
        (cx + s, cy),
        (cx + k, cy + k),
        (cx, cy + s),
        (cx - k, cy + k),
        (cx - s, cy),
        (cx - k, cy - k)
    ]
    draw.polygon(points, fill=color)

def draw_vector_link(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 255, 255)):
    draw.rounded_rectangle((cx - 10, cy - 6, cx - 1, cy + 6), radius=3, outline=color, width=2)
    draw.rounded_rectangle((cx - 2, cy - 6, cx + 8, cy + 6), radius=3, outline=color, width=2)

def draw_vector_dm_plane(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 255, 255)):
    pts = [(cx - 9, cy - 8), (cx + 9, cy), (cx - 9, cy + 8), (cx - 4, cy)]
    draw.polygon(pts, fill=color)

def draw_vector_hourglass(draw, cx, cy, color=(255, 215, 0), scale=0.8):
    w, h = int(6 * scale), int(8 * scale)
    top_tri = [(cx - w, cy - h), (cx + w, cy - h), (cx, cy)]
    bot_tri = [(cx, cy), (cx + w, cy + h), (cx - w, cy + h)]
    draw.polygon(top_tri, fill=color)
    draw.polygon(bot_tri, fill=color)
    draw.line([(cx - w - 2, cy - h), (cx + w + 2, cy - h)], fill=color, width=2)
    draw.line([(cx - w - 2, cy + h), (cx + w + 2, cy + h)], fill=color, width=2)

def clean_money(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    if not t.upper().endswith("TL"):
        t = f"{t} TL"
    return t

def parse_price(val: str) -> float:
    try:
        c = re.sub(r'[^\d,\.]', '', str(val)).replace('.', '').replace(',', '.')
        return float(c)
    except:
        return 0.0

def ease_out_back(x: float) -> float:
    """Yumuşak yaylanma/sekme eğrisi (Apple / iOS spring physics)"""
    c1 = 1.25
    c3 = c1 + 1
    return 1 + c3 * math.pow(x - 1, 3) + c1 * math.pow(x - 1, 2)

# -------------------------------------------------------------
# DİNAMİK KANCA ROZETİ VE DOĞAL SES KANCASI (Hook Engine)
# -------------------------------------------------------------
def render_kinetic_hook_badge(t: float, store_name: str = "Amazon", title: str = "") -> Image.Image:
    """
    0.0 - 2.0 sn aralığında ekrana yaylanarak giren, dikkat çekici Kanca Rozeti (Hook Banner).
    İzleyiciyi videoda tutar ve sesli kancayla birebir senkronize çalışır.
    """
    if t >= 2.05:
        return None

    # Alpha fade-in & fade-out
    if t < 0.22:
        alpha = min(1.0, t / 0.22)
    elif t < 1.60:
        alpha = 1.0
    else:
        alpha = max(0.0, 1.0 - (t - 1.60) / 0.40)

    # Elastic Pop-In Scale
    if t < 0.28:
        p = t / 0.28
        scale = 0.70 + 0.38 * math.sin(p * math.pi * 0.6)
    elif t < 1.60:
        scale = 1.0 + 0.015 * math.sin(t * 6.0)
    else:
        scale = max(0.75, 1.0 - 0.25 * ((t - 1.60) / 0.40))

    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx, cy = 540, 395
    bw, bh = int(840 * scale), int(144 * scale)
    x1, y1 = cx - bw // 2, cy - bh // 2
    x2, y2 = cx + bw // 2, cy + bh // 2

    a_int = int(245 * alpha)
    glow_a = int(105 * alpha)

    # Dış neon ışıltı halkası (Amazon Amber Glow)
    d.rounded_rectangle([x1 - 4, y1 - 4, x2 + 4, y2 + 4], radius=26, outline=(255, 153, 0, glow_a), width=3)
    # Obsidyen koyu cam gövde
    d.rounded_rectangle([x1, y1, x2, y2], radius=22, fill=(15, 23, 42, a_int), outline=(255, 153, 0, a_int), width=2)

    # Başlık Metinleri
    f_l1 = get_font("segoeuib", max(14, int(29 * scale)))
    f_l2 = get_font("segoeuib", max(11, int(21 * scale)))

    store_clean = "AMAZON" if "amazon" in store_name.lower() else store_name.upper()
    l1_text = f"{store_clean}'DA DEV İNDİRİM!"
    
    t_low = title.lower()
    if "ayakkabı" in t_low or "spor" in t_low or "runner" in t_low or "sneaker" in t_low:
        l2_text = "Orijinal adidas İndirimini Gördünüz mü?"
    elif "kahve" in t_low or "makine" in t_low:
        l2_text = "Orijinal Ürün İndirimini Gördünüz mü?"
    else:
        l2_text = "Orijinal Ürün İndirimini Gördünüz mü?"

    draw_vector_bolt(d, cx - int(210 * scale), cy - int(24 * scale), (255, 215, 0), scale=scale * 1.1)
    d.text((cx + int(15 * scale), cy - int(24 * scale)), l1_text, font=f_l1, fill=(255, 255, 255, a_int), anchor="mm")
    d.text((cx, cy + int(24 * scale)), l2_text, font=f_l2, fill=(255, 180, 50, a_int), anchor="mm")

    return img

def generate_hook_voiceover(deal: dict, temp_prefix: str) -> str:
    """
    Gemini Neural TTS ile ultra doğal, enerjik Türkçe soru kancası seslendirmesi üretir.
    Önbelleğe kaydeder ve kota aşımlarını engeller.
    """
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', deal.get("title", "firsat").lower())[:35]
    voice_cache_dir = os.path.join(ASSETS_DIR, "voice_cache")
    os.makedirs(voice_cache_dir, exist_ok=True)
    cached_file = os.path.join(voice_cache_dir, f"{slug}.wav")
    
    if os.path.exists(cached_file) and os.path.getsize(cached_file) > 10000:
        print(f"[CommercialComposer] 🎯 Önbellekten hazır ses alındı: {cached_file} ({os.path.getsize(cached_file)} bayt)")
        return cached_file

    store = deal.get("store_name", "Amazon")
    title_low = deal.get("title", "").lower()
    
    if "ayakkabı" in title_low or "spor" in title_low or "runner" in title_low or "adidas" in title_low:
        hook_text = "Amazon'daki orijinal adidas indirimini gördünüz mü? İki bin beş yüz liradan bin dört yüz liraya düştü, link profilde!"
    elif "kahve" in title_low or "makine" in title_low:
        hook_text = "Amazon'daki bu orijinal ürün indirimini gördünüz mü? İki bin beş yüz liradan bin dört yüz liraya düştü, link profilde!"
    else:
        hook_text = "Amazon'daki bu orijinal fırsatı gördünüz mü? İki bin beş yüz liradan bin dört yüz liraya düştü, link profilde!"

    hook_text = to_phonetic_turkish(hook_text)

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": hook_text,
                "speech_metadata": {
                    "style": "energetic, friendly, conversational Turkish speaking tone"
                }
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "voice": "Puck"
                }
            }
        }
    }
    
    req_path = os.path.join(TEMP_DIR, f"{temp_prefix}_tts_req.json")
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        
    TTS_MODELS = [
        "gemini-3.8-flash-lite-tts",
        "gemini-3.8-flash-tts"
    ]
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    for model in TTS_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        cmd = ["curl.exe", "-4", "-s", "-H", "Content-Type: application/json", "-X", "POST", "--data-binary", f"@{req_path}", url]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            audio_bytes = base64.b64decode(part["inlineData"]["data"])
                            raw_wav = os.path.join(TEMP_DIR, f"{temp_prefix}_raw_voice.wav")
                            with open(raw_wav, "wb") as f_raw:
                                f_raw.write(audio_bytes)
                            
                            # FFmpeg ile doğal tempo (0.92x) ve sıcak EQ filtresi
                            flt = "atempo=0.92,equalizer=f=1000:width_type=h:width=200:g=2,volume=1.25"
                            cmd_p = [ffmpeg_exe, "-y", "-i", raw_wav, "-filter:a", flt, cached_file]
                            subprocess.run(cmd_p, capture_output=True, text=True, timeout=8)
                            if os.path.exists(cached_file) and os.path.getsize(cached_file) > 10000:
                                print(f"[CommercialComposer] 🎙️ Gemini ({model}) doğal ses kancası üretildi ({os.path.getsize(cached_file)} bayt)")
                                return cached_file
        except Exception as e:
            print(f"[CommercialComposer] ⚠️ Ses kancası üretim uyarısı ({model}): {e}")
            
    return ""

# -------------------------------------------------------------
# KİNETİK ANİMASYON MOTORU (Canlı Giriş, Yaylanma, Nefes & Fiyat Patlaması)
# -------------------------------------------------------------
def build_kinetic_overlays(
    deal: dict,
    temp_prefix: str,
    duration: float = 8.2,
    cta_type: str = "instagram",
    layout_type: str = "hero",
    theme: dict = None
) -> str:
    """
    Tüm video boyunca (25 fps) üst başlık ve alt kartları canlı animasyonla çizer:
    1. 0.0 - 0.50 sn: Kartların yukarıdan ve aşağıdan yaylanarak ekrana girişi (Slide-In Spring)
    2. 0.50 - 3.0 sn: Çok hafif organik nefes alma süzülmesi (Harmonic Floating) & Canlı Geri Sayım Barı
    3. 3.0 - 3.45 sn: Fiyat açıldığı anda patlayan yaylanma ve neon ışıltı (Price Reveal Pop & Flash)
    4. 3.45 - 8.2 sn: Lüks zümrüt fiyat, kazanç rozeti ve CTA butonunda dikkat çekici yönlendirici ok titreşimi
    """
    if not theme:
        theme = get_theme_for_deal(deal)
        
    frames_dir = os.path.join(TEMP_DIR, f"{temp_prefix}_dyn_frames")
    os.makedirs(frames_dir, exist_ok=True)
    fps = 25
    total_frames = int(round(duration * fps))

    title = deal.get("title", "Günün Fırsatı")
    old_p_str = clean_money(deal.get("old_price", ""))
    new_p_str = clean_money(deal.get("new_price", ""))
    discount_pct = deal.get("discount_pct", "-40%")
    seller_badge = deal.get("seller_badge") or "Amazon Resmi Satıcı"
    deal_code = str(deal.get("deal_code") or "").strip()
    
    old_val = parse_price(old_p_str)
    new_val = parse_price(new_p_str)
    savings = int(old_val - new_val) if (old_val > new_val > 0) else 0

    pct_clean = discount_pct.replace("-", "").strip()
    pct_text = f"%{pct_clean} DEV İNDİRİM" if not pct_clean.startswith("%") else f"{pct_clean} DEV İNDİRİM"

    # 1. Üst Başlık Şablonu (1080 x 260)
    hdr_canvas = Image.new("RGBA", (1080, 260), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hdr_canvas)
    
    # Rozetler
    b1_x1, b1_y1, b1_x2, b1_y2 = 60, 10, 360, 60
    hd.rounded_rectangle([b1_x1, b1_y1, b1_x2, b1_y2], radius=16, fill=(*theme["badge_hdr"], 240), outline=theme["card_border"], width=1)
    draw_vector_shield_check(hd, b1_x1 + 24, (b1_y1 + b1_y2) // 2, (16, 185, 129), scale=0.9)
    hd.text((b1_x1 + 46, (b1_y1 + b1_y2) // 2), "%100 ORİJİNAL ÜRÜN", font=get_font("segoeuib", 20), fill=(255, 255, 255), anchor="lm")

    # Safe Zone: x <= 945 (Instagram/TikTok sağ butonları çakışmasını %100 önler)
    b2_x1, b2_y1, b2_x2, b2_y2 = 945 - 265, 10, 945, 60
    hd.rounded_rectangle([b2_x1, b2_y1, b2_x2, b2_y2], radius=16, fill=(225, 29, 72, 240), outline=(253, 164, 175, 140), width=1)
    draw_vector_trend_down(hd, b2_x1 + 24, (b2_y1 + b2_y2) // 2, (255, 255, 255), scale=0.9)
    hd.text((b2_x1 + 46, (b2_y1 + b2_y2) // 2), pct_text, font=get_font("segoeuib", 20), fill=(255, 255, 255), anchor="lm")

    # Başlık Kapsülü
    h_box = [60, 74, 945, 182]
    hd.rounded_rectangle(h_box, radius=22, fill=(15, 23, 42, 215), outline=theme["card_border"], width=2)
    clean_t = re.sub(r'\s+', ' ', title).strip()
    words = clean_t.split()
    line1 = " ".join(words[:5]) if len(words) >= 5 else clean_t
    line2 = " ".join(words[5:11]) if len(words) > 5 else "Orijinal Ürün  •  Türkiye Garantili"
    hd.text((60 + 28, 104), line1[:40], font=get_font("segoeuib", 31), fill=(248, 250, 252), anchor="lm")
    hd.text((60 + 28, 146), line2[:48], font=get_font("segoeui", 20), fill=(160, 180, 205), anchor="lm")

    # 2. Alt Kart Tabanı (1080 x 490 - Safe Zone Layout)
    card_h = 490
    card_base = Image.new("RGBA", (1080, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_base)
    
    c_x1, c_y1, c_x2, c_y2 = 60, 10, 945, 480
    cd.rounded_rectangle([c_x1, c_y1, c_x2, c_y2], radius=30, fill=(15, 23, 42, 225), outline=theme["card_border"], width=2)

    # Güven Rozetleri (Sağ Buton Güvenli Alanı)
    py1, py2 = 30, 67
    badge_avail = c_x2 - c_x1 - 44 - 20
    bw = badge_avail // 3
    t1_x1, t1_x2 = c_x1 + 22, c_x1 + 22 + bw
    cd.rounded_rectangle([t1_x1, py1, t1_x2, py2], radius=10, fill=(30, 41, 59, 210), outline=(71, 85, 105, 150), width=1)
    draw_vector_shield_check(cd, t1_x1 + 18, (py1 + py2) // 2, (16, 185, 129), scale=0.85)
    cd.text((t1_x1 + 34, (py1 + py2) // 2), "Amazon TR • Orijinal", font=get_font("segoeuib", 17), fill=(226, 232, 240), anchor="lm")

    t2_x1, t2_x2 = t1_x2 + 10, t1_x2 + 10 + bw
    cd.rounded_rectangle([t2_x1, py1, t2_x2, py2], radius=10, fill=(30, 41, 59, 210), outline=(71, 85, 105, 150), width=1)
    draw_vector_bolt(cd, t2_x1 + 18, (py1 + py2) // 2, (250, 204, 21), scale=0.75)
    cd.text((t2_x1 + 34, (py1 + py2) // 2), "Prime Hızlı Kargo", font=get_font("segoeuib", 17), fill=(226, 232, 240), anchor="lm")

    t3_x1, t3_x2 = t2_x2 + 10, c_x2 - 22
    cd.rounded_rectangle([t3_x1, py1, t3_x2, py2], radius=10, fill=(30, 41, 59, 210), outline=(71, 85, 105, 150), width=1)
    draw_vector_sparkle(cd, t3_x1 + 18, (py1 + py2) // 2, size=7, color=(251, 191, 36))
    cd.text((t3_x1 + 34, (py1 + py2) // 2), "4.6 / 5 Puan", font=get_font("segoeuib", 17), fill=(250, 204, 21), anchor="lm")

    # Özellikler Satırı
    fy1, fy2 = 260, 302
    feats = [("Orijinal Ürün", "shield"), ("Hızlı Kargo", "bolt"), ("Fırsat Stoku", "sparkle")]
    fw = (c_x2 - c_x1 - 44 - 24) // 3
    for i, (ft, icon_type) in enumerate(feats):
        fx1 = c_x1 + 22 + i * (fw + 12)
        fx2 = fx1 + fw
        cd.rounded_rectangle([fx1, fy1, fx2, fy2], radius=10, fill=(20, 28, 44, 190), outline=theme["card_border"], width=1)
        icx = fx1 + 22
        icy = (fy1 + fy2) // 2
        if icon_type == "shield":
            draw_vector_shield_check(cd, icx, icy, (56, 189, 248), scale=0.65)
        elif icon_type == "bolt":
            draw_vector_bolt(cd, icx, icy, (250, 204, 21), scale=0.65)
        else:
            draw_vector_sparkle(cd, icx, icy, size=6, color=(251, 191, 36))
        cd.text((fx1 + 34 + (fx2 - fx1 - 34) // 2, icy), ft, font=get_font("segoeuib", 17), fill=(210, 228, 250), anchor="mm")

    # Açıklama
    cd.text(((c_x1 + c_x2) // 2, 416), "* Fiyatlar anlık değişebilir. Stoklarla sınırlıdır. Doğrudan Amazon TR yetkili satıcısıdır.", font=get_font("segoeui", 15), fill=(148, 163, 184, 210), anchor="mm")

    # Fiyat kutuları koordinatları
    box_y1, box_y2 = 82, 246
    old_x1 = c_x1 + 22
    old_x2 = old_x1 + 300
    ocx = (old_x1 + old_x2) // 2
    arr_x1, arr_y1, arr_x2, arr_y2 = old_x2 + 10, box_y1 + 54, old_x2 + 50, box_y1 + 98
    acx, acy = (arr_x1 + arr_x2) // 2, (arr_y1 + arr_y2) // 2
    new_x1 = arr_x2 + 10
    new_x2 = c_x2 - 22
    ncx = (new_x1 + new_x2) // 2

    print(f"[CommercialComposer] 🎬 {total_frames} adet kinetik canlı katman karesi üretiliyor...")
    for frame_idx in range(total_frames):
        t = frame_idx / float(fps)
        
        # 1. Canlı Giriş Hareketi (0.0 - 0.45 sn)
        if t < 0.45:
            p_enter = t / 0.45
            e = ease_out_back(p_enter)
            hdr_offset_y = int(-320 * (1.0 - e))
            card_offset_y = int(450 * (1.0 - e))
        else:
            # 2. Organik süzülme ve nefes alma (Harmonic Floating)
            float_p = (t - 0.45) * 2.2
            hdr_offset_y = int(math.sin(float_p) * 2.8)
            card_offset_y = int(math.sin(float_p + math.pi * 0.5) * 3.2)

        frame_canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))

        # Üst Başlığı Yapıştır
        target_hdr_y = 70 + hdr_offset_y
        frame_canvas.alpha_composite(hdr_canvas, (0, target_hdr_y))

        # Alt Kartı Oluştur
        card_img = card_base.copy()
        c_draw = ImageDraw.Draw(card_img)

        # Sol Kutu: Piyasa Fiyatı
        c_draw.rounded_rectangle([old_x1, box_y1, old_x2, box_y2], radius=18, fill=(30, 41, 59, 220), outline=(71, 85, 105, 180), width=2)
        c_draw.text((ocx, box_y1 + 34), "PİYASA FİYATI", font=get_font("segoeuib", 19), fill=(148, 163, 184), anchor="mm")
        
        if t < 3.0:
            # Henüz açılmamış gizemli aşama (0.0 - 3.0 sn)
            c_draw.text((ocx, box_y1 + 95), old_p_str, font=get_font("segoeuib", 44), fill=(148, 163, 184), anchor="mm")
            
            c_draw.rounded_rectangle([arr_x1, arr_y1, arr_x2, arr_y2], radius=12, fill=(30, 41, 59, 220), outline=(56, 189, 248, 160), width=1)
            c_draw.line([(acx - 6, acy - 9), (acx + 5, acy)], fill=(56, 189, 248), width=3)
            c_draw.line([(acx + 5, acy), (acx - 6, acy + 9)], fill=(56, 189, 248), width=3)
            
            # Gizemli Kutu
            c_draw.rounded_rectangle([new_x1, box_y1, new_x2, box_y2], radius=18, fill=(45, 34, 18, 230), outline=(245, 158, 11, 230), width=2)
            c_draw.text((ncx, box_y1 + 30), "GÜNÜN FLAŞ FIRSATI", font=get_font("segoeuib", 19), fill=(253, 224, 71), anchor="mm")
            
            # ??? TL Nabız Titremesi (Pulse)
            pulse_alpha = int(214 + 40 * math.sin(t * 6.5))
            c_draw.text((ncx, box_y1 + 82), "??? TL", font=get_font("segoeuib", 64), fill=(255, pulse_alpha, 0), anchor="mm")
            
            # Canlı İlerleme Çubuğu
            bar_w = 340
            bar_h = 32
            bar_x1 = ncx - bar_w // 2
            bar_y1 = box_y1 + 116
            bar_x2 = ncx + bar_w // 2
            bar_y2 = bar_y1 + bar_h
            progress = min(1.0, max(0.0, t / 3.0))
            rem_sec = max(1, int(3.0 - t + 0.99))
            
            c_draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=16, fill=(25, 20, 12, 235), outline=(245, 158, 11, 180), width=1)
            fill_w = max(24, int(bar_w * progress))
            c_draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + fill_w, bar_y2], radius=16, fill=(245, 158, 11, 255))
            draw_vector_hourglass(c_draw, bar_x1 + 22, (bar_y1 + bar_y2) // 2, (15, 23, 42) if progress > 0.15 else (255, 215, 0), scale=0.75)
            cd_text = f"FİYAT AÇILIYOR: {rem_sec} SN"
            c_draw.text((ncx + 8, (bar_y1 + bar_y2) // 2), cd_text, font=get_font("segoeuib", 16), fill=(255, 255, 255), stroke_width=2, stroke_fill=(15, 23, 42), anchor="mm")
        else:
            # Fiyat Açılmış Aşama (3.0 - 8.2 sn)
            # Sol Kutu: Kırmızı üstü çizili fiyat
            f_old = get_font("segoeuib", 44)
            c_draw.text((ocx, box_y1 + 95), old_p_str, font=f_old, fill=(239, 68, 68), anchor="mm")
            pw = f_old.getbbox(old_p_str)[2] - f_old.getbbox(old_p_str)[0]
            c_draw.line([(ocx - pw // 2 - 10, box_y1 + 95), (ocx + pw // 2 + 10, box_y1 + 95)], fill=(239, 68, 68), width=3)
            
            # Orta ok zümrüt yeşiline döner
            c_draw.rounded_rectangle([arr_x1, arr_y1, arr_x2, arr_y2], radius=12, fill=(30, 41, 59, 220), outline=(52, 211, 153, 200), width=1)
            c_draw.line([(acx - 6, acy - 9), (acx + 5, acy)], fill=(52, 211, 153), width=3)
            c_draw.line([(acx + 5, acy), (acx - 6, acy + 9)], fill=(52, 211, 153), width=3)

            # 3. Saniyede Fiyat Patlama Efekti (Price Reveal Pop Punch)
            p_pop = min(1.0, (t - 3.0) / 0.40)
            pop_scale = 1.0 + (0.07 * math.sin(p_pop * math.pi) if p_pop < 1.0 else 0.0)
            
            pw_half = int(((new_x2 - new_x1) // 2) * pop_scale)
            ph_half = int(((box_y2 - box_y1) // 2) * pop_scale)
            b_mid_x = (new_x1 + new_x2) // 2
            b_mid_y = (box_y1 + box_y2) // 2
            
            pop_x1 = b_mid_x - pw_half
            pop_x2 = b_mid_x + pw_half
            pop_y1 = b_mid_y - ph_half
            pop_y2 = b_mid_y + ph_half

            # Patlama anında yeşil neon ışıltı halkası
            if pop_scale > 1.01:
                c_draw.rounded_rectangle([pop_x1 - 4, pop_y1 - 4, pop_x2 + 4, pop_y2 + 4], radius=22, outline=(52, 211, 153, 200), width=3)

            c_draw.rounded_rectangle([pop_x1, pop_y1, pop_x2, pop_y2], radius=18, fill=(6, 78, 59, 245), outline=(16, 185, 129, 255), width=3)
            c_draw.text((ncx, b_mid_y - 48), "İNDİRİMLİ FIRSAT FİYATI", font=get_font("segoeuib", 19), fill=(167, 243, 208), anchor="mm")
            
            f_price_sz = int(64 * pop_scale)
            c_draw.text((ncx, b_mid_y + 2), new_p_str, font=get_font("segoeuib", f_price_sz), fill=(52, 211, 153), anchor="mm")
            
            sav_text = f"{savings:,} TL KAZANÇ ({discount_pct})".replace(",", ".") if savings > 0 else f"NET DEV İNDİRİM ({discount_pct})"
            sp_x1, sp_y1, sp_x2, sp_y2 = ncx - 185, b_mid_y + 35, ncx + 185, b_mid_y + 75
            c_draw.rounded_rectangle([sp_x1, sp_y1, sp_x2, sp_y2], radius=10, fill=(245, 158, 11, 245))
            draw_vector_bolt(c_draw, sp_x1 + 18, (sp_y1 + sp_y2) // 2, (15, 23, 42), scale=0.85)
            c_draw.text((ncx + 8, (sp_y1 + sp_y2) // 2), sav_text, font=get_font("segoeuib", 22), fill=(15, 23, 42), anchor="mm")

        # 4. Satır: Modern CTA Barı ve Dikkat Çekici İtme Hareketi
        cta_x1, cta_y1, cta_x2, cta_y2 = c_x1 + 22, 316, c_x2 - 22, 388
        c_draw.rounded_rectangle([cta_x1, cta_y1, cta_x2, cta_y2], radius=18, fill=theme["cta_fill"], outline=theme["cta_border"], width=1)
        cta_cx = (cta_x1 + cta_x2) // 2

        if cta_type == "youtube":
            cta_text = f"FIRSAT KODU: {deal_code} • LİNK AÇIKLAMADA" if deal_code else "ÜRÜN LİNKİ AÇIKLAMA VE BİO'DA"
        else:
            cta_text = f"FIRSAT KODU: {deal_code} • LİNK PROFİLDE" if deal_code else "ÜRÜN LİNKİ PROFİLDE VE HİKAYEDE"

        f_cta = get_font("segoeuib", 21 if len(cta_text) > 30 else 23)
        tw = f_cta.getbbox(cta_text)[2] - f_cta.getbbox(cta_text)[0]
        
        # 5.0 ve 7.0 sn'de CTA butonundaki uçak ikonunu hafifçe ileri itip bırakma (Nudge animasyonu)
        plane_nudge = 0
        if (4.8 <= t <= 5.4) or (6.8 <= t <= 7.4):
            plane_nudge = int(math.sin((t % 2.0) * 10.0) * 6.0)

        draw_vector_link(c_draw, cta_cx - tw // 2 - 26, (cta_y1 + cta_y2) // 2, (255, 255, 255))
        c_draw.text((cta_cx, (cta_y1 + cta_y2) // 2), cta_text, font=f_cta, fill=(255, 255, 255), anchor="mm")
        draw_vector_dm_plane(c_draw, cta_cx + tw // 2 + 26 + plane_nudge, (cta_y1 + cta_y2) // 2, (255, 255, 255))

        # Alt Kartı Yapıştır (y = 1370)
        target_card_y = 1370 + card_offset_y
        frame_canvas.alpha_composite(card_img, (0, target_card_y))

        # 5. Kinetik Kanca Rozeti (0.0 - 2.05 sn): Ekrana yaylanarak giren "AMAZON'DA İNDİRİM" kancası
        if t < 2.05:
            hook_img = render_kinetic_hook_badge(t, store_name=deal.get("store_name", "Amazon"), title=deal.get("title", ""))
            if hook_img:
                frame_canvas.alpha_composite(hook_img, (0, 0))

        frame_canvas.save(os.path.join(frames_dir, f"dyn_{frame_idx:03d}.png"))

    return frames_dir

# -------------------------------------------------------------
# MASTER COMPOSER (Kinetik Animasyonlu Resmi Marka Reklamı)
# -------------------------------------------------------------
def build_commercial_video(
    video_source_path: str,
    deal: dict,
    output_path: str,
    duration: float = 8.0,
    cta_type: str = "instagram",
    layout_type: str = "hero"
) -> bool:
    """
    1080x1920 dikey kanvas üzerinde:
    - Akıcı stüdyo arka planı
    - 3D 360 dönen resmi B-Roll ürün çekimi
    - Canlı kinetik kartlar (Slide-In, Breathing Float, Fiyat Patlaması, CTA Nudge)
    - 0-3 sn canlı ilerleme çubuğu & geri sayım
    - 3-8 sn net nizami fiyat ve kazanç kutusu
    - Dinlendirici stüdyo fon müziği (sıfır yapay efekt)
    - Anti-Hash Kalkanı (Xiaomi Redmi Note 11 Pro üstverisi & jittered süre)
    ile videoyu derler.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    temp_prefix = f"comm_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    theme = get_theme_for_deal(deal)

    # 0. Doğal Ses Kancası Üret (Gemini 3.8 Flash TTS)
    voice_file = generate_hook_voiceover(deal, temp_prefix)
    
    # 1. Anti-Hash Kalkanı: Rastgele Milisaniye Süre Jitter'ı
    rnd_trim = round(random.uniform(-0.25, 0.25), 3)
    actual_duration = round(duration + rnd_trim, 2)
    
    # 2. Anti-Hash Kalkanı: Mikro Renk & Doygunluk Oynaması
    rnd_b = round(random.uniform(-0.012, 0.012), 3)
    rnd_c = round(random.uniform(0.988, 1.012), 3)
    rnd_s = round(random.uniform(0.985, 1.015), 3)
    
    print(f"[CommercialComposer] 🎬 Canlı kinetik animasyon katmanları üretiliyor (Süre: {actual_duration}s)...")
    dyn_frames_dir = build_kinetic_overlays(
        deal=deal,
        temp_prefix=temp_prefix,
        duration=actual_duration,
        cta_type=cta_type,
        layout_type=layout_type,
        theme=theme
    )
    
    music_file = os.path.join(MUSIC_DIR, "warm_pad.mp3")
    if not os.path.exists(music_file):
        music_file = os.path.join(MUSIC_DIR, "dark_ambient.mp3")

    fade_out_start = max(1.0, actual_duration - 1.0)

    # Dinamik Girdi Listesi (B-Roll, Canlı Katmanlar, Maske ve Sesler)
    inputs = [
        "-i", video_source_path,
        "-framerate", "25",
        "-i", os.path.join(dyn_frames_dir, "dyn_%03d.png")
    ]
    # Input 0: video_source_path
    # Input 1: dyn_frames
    next_idx = 2

    feather_mask_path = os.path.join(MASKS_DIR, "feather_mask_1080.png")
    use_feather = os.path.exists(feather_mask_path)
    if use_feather:
        mask_idx = next_idx
        next_idx += 1
        inputs.extend(["-i", feather_mask_path])

    music_idx = next_idx
    next_idx += 1
    inputs.extend(["-i", music_file])

    chime_file = os.path.join(AUDIO_DIR, "price_chime.wav")
    use_chime = os.path.exists(chime_file)
    if use_chime:
        chime_idx = next_idx
        next_idx += 1
        inputs.extend(["-i", chime_file])

    has_voice = bool(voice_file and os.path.exists(voice_file))
    if has_voice:
        voice_idx = next_idx
        next_idx += 1
        inputs.extend(["-i", voice_file])

    # 1. Video Filtre Grafiği (Sinematik Kenar Yumuşatma / Feathered Alphamerge)
    if use_feather:
        v_filter = (
            f"[0:v]split=2[bg_src][fg_src];"
            f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=45:6,eq=brightness=-0.04:contrast=1.02[bg];"
            f"[fg_src]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,fade=t=in:st=0.04:d=0.36,eq=brightness={rnd_b}:contrast={rnd_c}:saturation={rnd_s}[fg_raw];"
            f"[fg_raw][{mask_idx}:v]alphamerge[fg];"
            f"[bg][fg]overlay=0:280[base];"
            f"[base][1:v]overlay=0:0[v_out];"
        )
    else:
        v_filter = (
            f"[0:v]split=2[bg_src][fg_src];"
            f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=45:6,eq=brightness=-0.04:contrast=1.02[bg];"
            f"[fg_src]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,fade=t=in:st=0.04:d=0.36,eq=brightness={rnd_b}:contrast={rnd_c}:saturation={rnd_s}[fg];"
            f"[bg][fg]overlay=0:280[base];"
            f"[base][1:v]overlay=0:0[v_out];"
        )

    # 2. Ses Filtre Grafiği (Mikro Fiyat Efekti + Ses Kancası + Fon Müziği + -15 LUFS Normalizasyon)
    m_vol = 0.28 if has_voice else 0.35
    a_filters = [
        f"[{music_idx}:a]atrim=0:{actual_duration},volume={m_vol},afade=t=out:st={fade_out_start}:d=1.0[music]"
    ]
    mix_labels = ["[music]"]

    if use_chime:
        a_filters.append(f"[{chime_idx}:a]adelay=3000|3000,volume=0.45[chime]")
        mix_labels.append("[chime]")

    if has_voice:
        a_filters.append(f"[{voice_idx}:a]adelay=120|120,volume=1.25[voice]")
        mix_labels.insert(0, "[voice]")

    num_inputs = len(mix_labels)
    joined_labels = "".join(mix_labels)
    a_filters.append(f"{joined_labels}amix=inputs={num_inputs}:duration=first:dropout_transition=2[mixed_a]")
    a_filters.append("[mixed_a]loudnorm=I=-15:TP=-1.5:LRA=11[a_out]")

    filter_complex = v_filter + ";".join(a_filters)

    # 3. Anti-Hash Kalkanı: Mobil Cihaz Üstveri Maskelemesi
    iso_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-map_metadata", "-1",
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        "-brand", "mp42",
        "-metadata", "com.android.version=13",
        "-metadata", "com.android.manufacturer=Xiaomi",
        "-metadata", "com.android.model=Redmi Note 11 Pro",
        "-metadata:s:v:0", "handler_name=VideoHandle",
        "-metadata:s:a:0", "handler_name=SoundHandle",
        "-metadata", f"creation_time={iso_now}",
        "-movflags", "+faststart+use_metadata_tags",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(actual_duration),
        output_path
    ]

    print(f"[CommercialComposer] 🎬 FFmpeg ile kinetik reklam videosu derleniyor -> {output_path}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    
    # Geçici dosyaları temizle
    try:
        shutil.rmtree(dyn_frames_dir, ignore_errors=True)
        if voice_file and os.path.exists(voice_file) and "voice_cache" not in voice_file:
            os.remove(voice_file)
    except:
        pass
        
    if res.returncode != 0:
        print(f"[CommercialComposer] ❌ FFmpeg derleme hatası: {res.stderr[-600:]}")
        return False
        
    success = os.path.exists(output_path) and os.path.getsize(output_path) > 100000
    if success:
        print(f"[CommercialComposer] ✅ Kinetik video başarıyla derlendi ({os.path.getsize(output_path)} bayt, süre: {actual_duration}s)")
    return success
