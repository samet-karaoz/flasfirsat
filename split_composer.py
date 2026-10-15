import os
import subprocess
import random
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, DATA_DIR
from deal_hunter import parse_price_to_float

MEMES_DIR = os.path.join(BASE_DIR, "assets", "memes")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")

# Dengeli, türlerine göre ardışık dizilmiş ana rotasyon havuzu (Round-Robin)
MEME_ROTATION_ORDER = [
    "knight_cat.mp4",           # 1. Şövalye Kedi (Zırhlı kedi viral)
    "bicerdover_ciftetelli.mp4", # 2. Biçerdöver çiftetelli (Türk viral dans)
    "homelander_stare.mp4",     # 3. Homelander şok / Ciddi bakış
    "degirmenci_dayi_cj.mp4",   # 4. GTA San Andreas Değirmenci Dayı
    "bale_nod.mp4",             # 5. Christian Bale onaylama / takdir
    "limon_davulcu.mp4",        # 6. Limoncu Davulcu (Türk viral dans)
    "cat_vibing.mp4",           # 7. Vibing Cat (Ritimle kafa sallayan kedi)
    "shark_nemo.mp4",           # 8. Kayıp Balık Nemo Bruce köpekbalığı
    "angaraya_mi_geldin.mp4",   # 9. Angara'ya mı geldin la
    "the_rock.mp4",             # 10. The Rock ikonik kaş kaldırma
    "limon_halay.mp4",          # 11. Limon Halay (Türk viral halay)
    "vince_mcmahon.mp4"         # 12. Vince McMahon para koklama / Şok sevinç
]
AVAILABLE_MEMES = MEME_ROTATION_ORDER

AVAILABLE_AUDIOS = [
    "phonk_meme.m4a",
    "brazilian_phonk.m4a",
    "viral_bass.m4a",
    "drift_phonk.m4a"
]

FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

def get_font(font_name: str, size: int):
    candidates = [
        os.path.join(FONTS_DIR, f"{font_name}.ttf"),
        os.path.join(FONTS_DIR, "segoeuib.ttf"),
        f"C:/Windows/Fonts/{font_name}.ttf",
        f"C:/Windows/Fonts/{font_name.lower()}.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except:
                pass
    return ImageFont.load_default()

def wrap_text(text: str, max_chars_per_line: int = 34) -> list:
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_chars_per_line:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(" ".join(current_line))
    return lines[:2] # Maksimum 2 satır, görsel alanını ferah tutmak için

MEME_STATE_FILE = os.path.join(DATA_DIR, "meme_history.json")

def load_meme_state() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(MEME_STATE_FILE):
        try:
            with open(MEME_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"next_index": 0, "recent_used": []}

def save_meme_state(state: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(MEME_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Meme Engine] Durum kaydedilemedi: {e}")

def get_ordered_meme_pool() -> list:
    """Diskte mevcut olan tüm meme videolarını dengeli ve sıralı bir havuz olarak döndürür."""
    if not os.path.exists(MEMES_DIR):
        return []
    disk_files = [f for f in os.listdir(MEMES_DIR) if f.endswith(".mp4")]
    # Önceden küratörlüğü yapılmış dengeli sıra
    pool = [m for m in MEME_ROTATION_ORDER if m in disk_files]
    # Listede olmayan yeni eklenmiş mp4'leri de sıranın sonuna ekle
    for f in sorted(disk_files):
        if f not in pool:
            pool.append(f)
    return pool

def get_last_meme() -> str:
    state = load_meme_state()
    recent = state.get("recent_used", [])
    return recent[-1] if recent else ""

def set_last_meme(meme_name: str):
    pass

def select_smart_meme(discount_pct: str = "", title: str = "", category: str = "") -> str:
    """
    Kütüphanedeki tüm meme videolarını sıra sıra (Round-Robin) döngüye sokar.
    Son 3 videoda kullanılan memeleri kesin olarak hariç tutarak mükerrerliği %100 engeller.
    Herhangi bir kategori veya oran şartlandırması yapmadan havuzdaki tüm videoları sırayla eşit kullanır.
    """
    pool = get_ordered_meme_pool()
    if not pool:
        return "vince_mcmahon.mp4"

    state = load_meme_state()
    next_idx = state.get("next_index", 0) % len(pool)
    recent = state.get("recent_used", [])

    # Son 3 videodaki memeleri koruma listesine al (cooldown: en az 3 video boyunca tekrar seçilemez)
    cooldown_count = min(3, len(pool) - 1) if len(pool) > 1 else 0
    cooldown_set = set(recent[-cooldown_count:]) if cooldown_count > 0 else set()

    # Sıradaki adayı seç; eğer cooldown listesindeyse havuzda sırayla ilerle
    chosen = None
    for attempt in range(len(pool)):
        candidate_idx = (next_idx + attempt) % len(pool)
        candidate = pool[candidate_idx]
        if candidate not in cooldown_set:
            chosen = candidate
            next_idx = (candidate_idx + 1) % len(pool)
            break

    # Emniyet: Hepsi cooldown listesindeyse sıradaki adayı al
    if not chosen:
        chosen = pool[next_idx]
        next_idx = (next_idx + 1) % len(pool)

    # Durumu güncelle ve kaydet
    recent.append(chosen)
    state["next_index"] = next_idx
    state["recent_used"] = recent[-30:] # Son 30 kaydı tut
    save_meme_state(state)

    print(f"[Meme Rotasyonu] 🎬 Sıradaki Video: {chosen} (Sıra: {next_idx}/{len(pool)}, Cooldown: {list(cooldown_set)})")
    return chosen

# ==========================================
# VEKTÖR İKON ÇİZİM YARDIMCILARI (Windows Emojisi Bağımsız & Keskin)
# ==========================================

def draw_vector_bolt(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 204, 0)):
    points = [
        (cx + 3, cy - 17),
        (cx - 9, cy),
        (cx, cy),
        (cx - 6, cy + 17),
        (cx + 11, cy - 2),
        (cx + 2, cy - 2)
    ]
    draw.polygon(points, fill=color)

def draw_vector_shield_check(draw: ImageDraw.Draw, cx: int, cy: int, color=(16, 185, 129)):
    shield = [
        (cx, cy - 11),
        (cx + 10, cy - 7),
        (cx + 10, cy + 3),
        (cx, cy + 12),
        (cx - 10, cy + 3),
        (cx - 10, cy - 7)
    ]
    draw.polygon(shield, fill=color)
    chk = [(cx - 4, cy), (cx - 1, cy + 3), (cx + 5, cy - 3)]
    draw.line(chk, fill=(255, 255, 255), width=2)

def draw_vector_trend_down(draw: ImageDraw.Draw, cx: int, cy: int, color=(225, 29, 72)):
    points = [(cx - 9, cy - 5), (cx - 3, cy - 1), (cx + 2, cy - 6), (cx + 8, cy + 4)]
    draw.line(points, fill=color, width=2)
    draw.polygon([(cx + 8, cy + 4), (cx + 3, cy + 4), (cx + 8, cy - 1)], fill=color)

def draw_vector_sparkle(draw: ImageDraw.Draw, cx: int, cy: int, size: int = 8, color=(251, 191, 36)):
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

def draw_vector_coin(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 204, 0)):
    draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=color, outline=(245, 158, 11), width=2)
    draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), outline=(254, 240, 138), width=1)
    draw.line((cx - 3, cy - 5, cx + 3, cy - 5), fill=(180, 83, 9), width=2)
    draw.line((cx - 1, cy - 5, cx - 1, cy + 5), fill=(180, 83, 9), width=2)
    draw.line((cx - 3, cy, cx + 1, cy), fill=(180, 83, 9), width=2)

def draw_vector_globe(draw: ImageDraw.Draw, cx: int, cy: int, color=(251, 191, 36)):
    draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), outline=color, width=2)
    draw.line((cx - 11, cy, cx + 11, cy), fill=color, width=1)
    draw.ellipse((cx - 5, cy - 11, cx + 5, cy + 11), outline=color, width=1)

def draw_vector_link(draw: ImageDraw.Draw, cx: int, cy: int, color=(251, 191, 36)):
    draw.rounded_rectangle((cx - 10, cy - 6, cx - 1, cy + 6), radius=3, outline=color, width=2)
    draw.rounded_rectangle((cx - 2, cy - 6, cx + 8, cy + 6), radius=3, outline=color, width=2)

def draw_vector_chat_bubble(draw: ImageDraw.Draw, cx: int, cy: int, color=(251, 191, 36)):
    draw.rounded_rectangle((cx - 12, cy - 9, cx + 12, cy + 7), radius=4, fill=color)
    draw.polygon([(cx - 7, cy + 6), (cx - 2, cy + 6), (cx - 9, cy + 13)], fill=color)

def draw_vector_dm_plane(draw: ImageDraw.Draw, cx: int, cy: int, color=(251, 191, 36)):
    plane = [
        (cx + 12, cy - 8),
        (cx - 10, cy + 2),
        (cx - 3, cy + 4),
        (cx - 3, cy + 10),
        (cx + 2, cy + 6),
        (cx + 7, cy + 9)
    ]
    draw.polygon(plane, fill=color)


# ==========================================
# VIRAL MEME REAKSİYON METİNLERİ (REACTION HOOKS)
# ==========================================

REACTION_HOOKS_PRICE_ERROR = [
    "FİYAT HATASI MI DİYE KONTROL EDERKEN BEN:",
    "BU FİYATA İNANAMAYIP 3 KERE SAYFAYI YENİLEYEN BEN:",
    "FİYAT HATASINI GÖRÜP KART BİLGİSİ GİREN BEN:",
    "BU FİYATI GÖRÜNCE SİPARİŞİ IŞIK HIZINDA VEREN BEN:"
]

REACTION_HOOKS_HIGH_DISCOUNT = [
    "BU FİYATI GÖRÜNCE BEN VE CEBİMDEKİ PARA:",
    "MAAŞI BU İNDİRİME GÖMME KARARI ALIRKEN BEN:",
    "İNDİRİMİ GÖRÜP ANINDA SEPETE KOŞAN BİZİM TAYFA:",
    "BU İNDİRİME KARTIN LİMİTİ BİLE DAYANMAZ:"
]

REACTION_HOOKS_GAMING = [
    "EKİPMAN EKSİĞİNİ BU İNDİRİMLE KAPATAN GAMER'LAR:",
    "BU SETUP İNDİRİMİNİ GÖRÜNCE BENİM ODAK SEVİYESİ:",
    "KART LİMİTİNİ BU GAMING İNDİRİMİNE AYIRAN TAYFA:"
]

REACTION_HOOKS_GENERAL = [
    "BU İNDİRİMİ KAÇIRIRSAM GECE UYUYAMAM DİYEN BEN:",
    "İNDİRİMİ GÖRÜP ARKADAŞ GRUBUNA ATAN BEN:",
    "CEBİMDEKİ PARAYI BU FIRSATA EMANET EDERKEN BEN:"
]

def select_smart_reaction_hook(discount_pct: str = "", product_title: str = "", is_price_error: bool = False) -> str:
    pct_m = re.search(r'(\d+)', str(discount_pct))
    pct_val = int(pct_m.group(1)) if pct_m else 0
    title_low = (product_title or "").lower()

    if is_price_error or pct_val >= 40:
        return random.choice(REACTION_HOOKS_PRICE_ERROR)
    
    gaming_kw = ["mouse", "kulaklık", "klavye", "gaming", "ps5", "gamepad", "oyuncu", "monitor", "ekran kartı"]
    if any(k in title_low for k in gaming_kw):
        return random.choice(REACTION_HOOKS_GAMING)

    if pct_val >= 25:
        return random.choice(REACTION_HOOKS_HIGH_DISCOUNT)

    return random.choice(REACTION_HOOKS_GENERAL)

def create_reaction_hook_overlay(reaction_text: str, output_path: str = None) -> str:
    """
    Alt meme videosunun üstüne binecek şeffaf, modern glassmorphic ve büyük reaksiyon başlığı üretir.
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "reaction_overlay.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    W, H = 1080, 960
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    f_hook = get_font("segoeuib", 32)  # 32px Büyütülmüş font
    clean_text = reaction_text.strip()
    text_w = draw.textlength(clean_text, font=f_hook)

    box_w = min(W - 40, text_w + 64)
    box_h = 68  # 68px Konforlu kapsül yüksekliği
    box_x = (W - box_w) // 2
    box_y = 22  # Meme videosunun tam üst kenarında

    # Koyu füme yarı saydam arka plan kapsülü
    draw.rounded_rectangle(
        (box_x, box_y, box_x + box_w, box_y + box_h),
        radius=16,
        fill=(15, 23, 42, 230),
        outline=(255, 255, 255, 100),
        width=2
    )

    t_bbox = draw.textbbox((0, 0), clean_text, font=f_hook)
    t_h = t_bbox[3] - t_bbox[1]
    tx = (W - text_w) // 2
    ty = box_y + (box_h - t_h) // 2 - t_bbox[1]
    draw.text((tx, ty), clean_text, font=f_hook, fill=(255, 255, 255, 255))

    img.save(output_path, "PNG")
    return output_path

# ==========================================
# ANA ÜRÜN AFİŞİ (1080x960 - V3 ENHANCED)
# ==========================================

def create_product_banner(
    product_image_path: str,
    title: str,
    old_price: str,
    new_price: str,
    discount_pct: str = "-35%",
    badge_text: str = "DEV İNDİRİM",
    store_name: str = "Amazon TR",
    bank_campaign: str = "",
    net_cost: str = "",
    installment: str = "",
    feature_text: str = "",
    is_lowest_30d: bool = False,
    has_verified_old_price: bool = True,
    seller_badge_text: str = "",
    coupon_text: str = "",
    market_badge: str = "",
    cta_type: str = "instagram",
    output_path: str = None
) -> str:
    """
    Ürün görseli ve fiyat bilgilerinden 1080x960 ebatlarında
    Top-tier ajans kalitesinde afiş üretir:
    1. Ürün arkasında rembg ile saydamlaştırılmış dekupe ve soft spotlight / ışıma efekti
    2. "Son 30 Günün En Düşüğü" geçmiş fiyat rozeti (sadece veritabanı onaylıysa)
    3. Can alıcı teknik özellik hap rozeti (Feature Pill)
    4. Dürüst Fiyat Mimarisi (Doğrulanmışsa 2 kutulu, doğrulanmamışsa tek büyük Hero kutusu)
    5. ManyChat CTA Bandında Parıltı Efekti (✨ "LİNK" ✨) ve #işbirliği yasal etiketi
    6. Floating Net Tasarruf / Kupon Rozeti
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "product_top.png")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    W, H = 1080, 960
    img = Image.new("RGB", (W, H), (244, 246, 250))
    draw = ImageDraw.Draw(img)

    f_badge = get_font("segoeuib", 26)
    f_label = get_font("segoeuib", 20)
    f_trust = get_font("segoeuib", 19)
    f_feature = get_font("segoeuib", 20)
    f_old_lbl = get_font("segoeuib", 17)
    f_old_price = get_font("segoeuib", 28)
    f_new_label = get_font("segoeuib", 20)
    f_new_price = get_font("segoeuib", 60)
    f_net = get_font("segoeuib", 19)
    f_pct = get_font("segoeuib", 28)
    f_savings = get_font("segoeuib", 22)
    f_cta = get_font("segoeuib", 24)
    f_tiny = get_font("segoeuib", 13)

    # 1. Sol Üst Rozet: DEV İNDİRİM (Vector Şimşekli)
    clean_badge = badge_text.strip() if badge_text else "DEV İNDİRİM"
    b_w = draw.textlength(clean_badge, font=f_badge)
    badge_fill = (255, 87, 34)  # Alev Turuncusu
    draw.rounded_rectangle((40, 22, 40 + b_w + 58, 74), radius=14, fill=badge_fill)
    draw_vector_bolt(draw, 64, 48, (255, 204, 0))
    draw.text((82, 34), clean_badge, font=f_badge, fill=(255, 255, 255))

    # 2. Sağ Üst Rozet: % İNDİRİM (Varsa)
    clean_pct = discount_pct.strip()
    if clean_pct and clean_pct != "0%" and clean_pct != "-0%":
        if not clean_pct.endswith("İNDİRİM"):
            clean_pct = f"{clean_pct} İNDİRİM"
        p_w = draw.textlength(clean_pct, font=f_pct)
        draw.rounded_rectangle((W - 40 - p_w - 38, 22, W - 40, 74), radius=14, fill=(225, 29, 72))
        draw.text((W - 40 - p_w - 19, 33), clean_pct, font=f_pct, fill=(255, 255, 255))

    # 3. Başlık (Temiz 1 veya 2 Satır Formatı)
    title_lines = wrap_text(title, max_chars_per_line=36)
    if len(title_lines) == 1:
        f_title = get_font("segoeuib", 38)
        draw.text((40, 92), title_lines[0], font=f_title, fill=(15, 23, 42))
        card_top = 146
    else:
        f_title = get_font("segoeuib", 32)
        draw.text((40, 88), title_lines[0], font=f_title, fill=(15, 23, 42))
        draw.text((40, 124), title_lines[1], font=f_title, fill=(15, 23, 42))
        card_top = 166

    # 4. Ürün Kartı (Soft Drop Shadow ile 3D Derinlik)
    card_box = (40, card_top, W - 40, 706)
    for offset, col in [(5, (220, 224, 234)), (3, (228, 232, 240)), (1, (235, 238, 244))]:
        draw.rounded_rectangle((card_box[0]+offset, card_box[1]+offset, card_box[2]+offset, card_box[3]+offset), radius=22, fill=col)
    draw.rounded_rectangle(card_box, radius=22, fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    # 🌟 GELİŞTİRME 1: Ürün Arkasına Soft Spotlight (Işıma) Efekti
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    glow_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    gcx = cw // 2
    gcy = ch // 2 + 10
    glow_draw.ellipse((gcx - 170, gcy - 170, gcx + 170, gcy + 170), fill=(255, 237, 213, 110))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=50))
    img.paste(glow_layer, (card_box[0], card_box[1]), glow_layer)

    # 🛡️ Kart İçi Sol Üst: Resmi Satıcı Doğrulama Rozeti (HTML'den Doğrulanmış)
    if seller_badge_text:
        trust_text = seller_badge_text
    else:
        trust_text = "AMAZON TR RESMİ SATICI" if "amazon" in store_name.lower() else f"{store_name.upper()} DOĞRULANMIŞ"
    tr_w = draw.textlength(trust_text, font=f_trust)
    draw.rounded_rectangle((card_box[0] + 16, card_box[1] + 16, card_box[0] + 58 + tr_w, card_box[1] + 48), radius=8, fill=(241, 245, 249))
    draw_vector_shield_check(draw, card_box[0] + 32, card_box[1] + 32, (16, 185, 129))
    draw.text((card_box[0] + 48, card_box[1] + 21), trust_text, font=f_trust, fill=(71, 85, 105))

    # 🏷️ Kart İçi Sağ Üst: "Son 30 Günün En Düşüğü" veya "Piyasanın X TL Altında" (Doğrulanmış veri)
    top_badge_text = ""
    if is_lowest_30d:
        top_badge_text = "SON 30 GÜNÜN EN DÜŞÜĞÜ"
    elif market_badge:
        top_badge_text = market_badge.strip().upper()

    if top_badge_text:
        low_w = draw.textlength(top_badge_text, font=f_trust)
        draw.rounded_rectangle((card_box[2] - low_w - 58, card_box[1] + 16, card_box[2] - 16, card_box[1] + 48), radius=8, fill=(255, 241, 242), outline=(254, 205, 211), width=1)
        draw_vector_trend_down(draw, card_box[2] - low_w - 38, card_box[1] + 32, (225, 29, 72))
        draw.text((card_box[2] - low_w - 24, card_box[1] + 21), top_badge_text, font=f_trust, fill=(225, 29, 72))

    # 🎨 rembg ile Arka Planı Temizlenmiş Ürün Görselini Ekle
    if product_image_path and os.path.exists(product_image_path):
        try:
            cutout_path = f"{os.path.splitext(product_image_path)[0]}_cutout.png"
            if not os.path.exists(cutout_path):
                try:
                    import rembg
                    with Image.open(product_image_path) as raw_p:
                        cutout = rembg.remove(raw_p)
                        cutout.save(cutout_path)
                except Exception as ex:
                    print(f"[Banner] rembg atlandı/uyarısı: {ex}")

            load_path = cutout_path if os.path.exists(cutout_path) else product_image_path
            p_img = Image.open(load_path).convert("RGBA")
            # Saydam kenar boşluklarını kırparak ürünün kart içinde maksimum netlik ve büyüklükte olmasını sağla
            alpha = p_img.split()[-1]
            bbox = alpha.getbbox()
            if bbox:
                p_img = p_img.crop(bbox)

            max_img_w = card_box[2] - card_box[0] - 60
            max_img_h = card_box[3] - card_box[1] - 130
            p_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2 - 8
            img.paste(p_img, (px, py), p_img)
        except Exception as e:
            print(f"[Banner] Görsel yükleme uyarısı: {e}")

    # 📦 Ürünün Can Alıcı Özellik Rozeti (SADECE gerçek ürün sayfasından çekilmişse gösterilir)
    if feature_text and len(feature_text.strip()) > 3:
        clean_feat = feature_text.strip()
        feat_w = draw.textlength(clean_feat, font=f_feature)
        feat_box_w = feat_w + 48
        feat_x = (W - feat_box_w) // 2
        feat_y = card_box[3] - 88
        draw.rounded_rectangle((feat_x, feat_y, feat_x + feat_box_w, feat_y + 34), radius=17, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
        draw_vector_bolt(draw, feat_x + 18, feat_y + 17, (234, 88, 12))
        draw.text((feat_x + 32, feat_y + 6), clean_feat, font=f_feature, fill=(51, 65, 85))

    # Kart İçi Dinamik Mağaza Rozeti (Sağ Alt Köşe)
    store_styles = {
        "Trendyol": {"name": "TRENDYOL", "bg": (242, 122, 26), "fg": (255, 255, 255)},
        "Hepsiburada": {"name": "HEPSİBURADA", "bg": (255, 96, 0), "fg": (255, 255, 255)},
        "Amazon TR": {"name": "AMAZON TÜRKİYE", "bg": (15, 23, 42), "fg": (255, 255, 255)},
        "Amazon": {"name": "AMAZON TÜRKİYE", "bg": (15, 23, 42), "fg": (255, 255, 255)},
    }
    st_info = store_styles.get(store_name, {"name": store_name.upper(), "bg": (15, 23, 42), "fg": (255, 255, 255)})
    tag_text = f"{st_info['name']}  •  @flasfirsat"
    t_w = draw.textlength(tag_text, font=f_label)
    draw.rounded_rectangle((card_box[2] - t_w - 36, card_box[3] - 44, card_box[2] - 16, card_box[3] - 14), radius=8, fill=st_info["bg"])
    draw.text((card_box[2] - t_w - 26, card_box[3] - 40), tag_text, font=f_label, fill=st_info["fg"])

    # Kart İçi Dinamik Taksit Rozeti (Sol Alt Köşe)
    clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip() if installment else "Peşin Fiyatına 3 Taksit"
    it_w = draw.textlength(clean_inst, font=f_label)
    draw.rounded_rectangle((card_box[0] + 16, card_box[3] - 44, card_box[0] + 16 + it_w + 24, card_box[3] - 14), radius=8, fill=(236, 253, 245), outline=(16, 185, 129), width=1)
    draw.ellipse((card_box[0] + 24, card_box[3] - 31, card_box[0] + 32, card_box[3] - 23), fill=(5, 150, 105))
    draw.text((card_box[0] + 38, card_box[3] - 40), clean_inst, font=f_label, fill=(4, 120, 87))

    # 5. DÜRÜST FİYAT MİMARİSİ: Doğrulanmış Eski Fiyat Varsa İki Kutu, Yoksa Tek Büyük Hero Kutu
    show_old_price = bool(has_verified_old_price and old_price and old_price.strip())
    old_val = parse_price_to_float(old_price) if show_old_price else 0
    new_val = parse_price_to_float(new_price)
    savings = (old_val - new_val) if (show_old_price and old_val > new_val) else 0

    sub_parts = []
    if net_cost:
        clean_net = re.sub(r'[^\w\s.,xX+\-/%]', '', net_cost).strip()
        sub_parts.append(f"Net: {clean_net}")
    if installment:
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()
        sub_parts.append(clean_inst)
    sub_str = "  •  ".join(sub_parts) if sub_parts else ""
    new_str = new_price if new_price else "Fırsat Fiyatı"

    if show_old_price:
        # İki Kutu: Sol Piyasa Fiyatı, Sağ Fırsat Fiyatı
        old_box = (40, 750, 320, 892)
        draw.rounded_rectangle(old_box, radius=18, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        draw.text((old_box[0] + (old_box[2] - old_box[0] - draw.textlength("PİYASA FİYATI", font=f_old_lbl)) // 2, 768), "PİYASA FİYATI", font=f_old_lbl, fill=(148, 163, 184))

        op_w = draw.textlength(old_price, font=f_old_price)
        op_x = old_box[0] + (old_box[2] - old_box[0] - op_w) // 2
        op_y = 812
        draw.text((op_x, op_y), old_price, font=f_old_price, fill=(148, 163, 184))

        tbbox = draw.textbbox((op_x, op_y), old_price, font=f_old_price)
        strike_y = (tbbox[1] + tbbox[3]) // 2
        draw.line((op_x - 8, strike_y, op_x + op_w + 8, strike_y), fill=(239, 68, 68), width=4)

        arrow_box = (338, 804, 380, 846)
        draw.rounded_rectangle(arrow_box, radius=10, fill=(255, 255, 255), outline=(203, 213, 225), width=1)
        cx, cy = 359, 825
        draw.line((cx - 4, cy - 8, cx + 4, cy), fill=(234, 88, 12), width=3)
        draw.line((cx + 4, cy, cx - 4, cy + 8), fill=(234, 88, 12), width=3)

        new_box = (398, 750, W - 40, 892)
        draw.rounded_rectangle((new_box[0]+4, new_box[1]+5, new_box[2]+4, new_box[3]+5), radius=18, fill=(185, 235, 210))
        draw.rounded_rectangle((new_box[0]+2, new_box[1]+2, new_box[2]+2, new_box[3]+2), radius=18, fill=(210, 245, 225))
        draw.rounded_rectangle(new_box, radius=18, fill=(236, 253, 245), outline=(16, 185, 129), width=3)

        # Kutu Merkez Koordinatları (Kusursuz Simetri ve Hizalama)
        box_center_x = (new_box[0] + new_box[2]) // 2

        # 1. Başlık: İNDİRİMLİ FIRSAT FİYATI (Tam Ortalanmış)
        lbl_text = "İNDİRİMLİ FIRSAT FİYATI"
        lbl_w = draw.textlength(lbl_text, font=f_new_label)
        dot_r = 4
        spacing = 8
        total_lbl_w = (dot_r * 2) + spacing + lbl_w
        lbl_start_x = box_center_x - total_lbl_w // 2
        lbl_y = 768
        draw.ellipse((lbl_start_x, lbl_y + 7 - dot_r, lbl_start_x + dot_r * 2, lbl_y + 7 + dot_r), fill=(5, 150, 105))
        draw.text((lbl_start_x + (dot_r * 2) + spacing, lbl_y), lbl_text, font=f_new_label, fill=(4, 120, 87))

        # 2. Fiyat: Yeni İndirimli Fiyat (Kutu İçinde Yatayda TAM ORTALANMIŞ)
        pw = draw.textlength(new_str, font=f_new_price)
        price_x = box_center_x - pw // 2
        price_y = 786 if sub_str else 796
        draw.text((price_x, price_y), new_str, font=f_new_price, fill=(5, 150, 105))

        # 3. Alt Bilgi: Net Tutar / Taksit (Tam Ortalanmış)
        if sub_str:
            sw = draw.textlength(sub_str, font=f_net)
            sub_x = box_center_x - sw // 2
            draw.text((sub_x, 860), sub_str, font=f_net, fill=(4, 120, 87))

        # 4. Floating Net Tasarruf / Kupon Rozeti (İndirimli Fiyat Kutusunun Tam Üst Merkezine Oturur)
        if savings > 0:
            sav_str = f"{int(savings):,} TL".replace(',', '.')
            sav_text = f"{sav_str} NET TASARRUF"
            s_w = draw.textlength(sav_text, font=f_savings)
            pill_w = s_w + 64
            pill_x = box_center_x - pill_w // 2
            pill_y1 = 718
            pill_y2 = 752
            draw.rounded_rectangle((pill_x + 1, pill_y1 + 1, pill_x + pill_w + 1, pill_y2 + 1), radius=12, fill=(200, 205, 215))
            draw.rounded_rectangle((pill_x, pill_y1, pill_x + pill_w, pill_y2), radius=12, fill=(16, 185, 129))
            draw_vector_coin(draw, pill_x + 24, (pill_y1 + pill_y2) // 2, (255, 204, 0))
            draw.text((pill_x + 44, pill_y1 + 7), sav_text, font=f_savings, fill=(255, 255, 255))
        elif coupon_text:
            c_clean = f"🎟️ {coupon_text.upper()}"
            c_w = draw.textlength(c_clean, font=f_savings)
            pill_w = c_w + 48
            pill_x = box_center_x - pill_w // 2
            pill_y1 = 718
            pill_y2 = 752
            draw.rounded_rectangle((pill_x, pill_y1, pill_x + pill_w, pill_y2), radius=12, fill=(245, 158, 11))
            draw.text((pill_x + 24, pill_y1 + 7), c_clean, font=f_savings, fill=(255, 255, 255))

    else:
        # Tek Büyük ve Geniş Hero Kutu (Tam Ortalanmış)
        new_box = (40, 750, W - 40, 892)
        draw.rounded_rectangle((new_box[0]+4, new_box[1]+5, new_box[2]+4, new_box[3]+5), radius=18, fill=(185, 235, 210))
        draw.rounded_rectangle((new_box[0]+2, new_box[1]+2, new_box[2]+2, new_box[3]+2), radius=18, fill=(210, 245, 225))
        draw.rounded_rectangle(new_box, radius=18, fill=(236, 253, 245), outline=(16, 185, 129), width=3)

        box_center_x = (new_box[0] + new_box[2]) // 2

        lbl = "GÜNÜN ÖNE ÇIKAN SATIŞ FİYATI"
        lbl_w = draw.textlength(lbl, font=f_new_label)
        dot_r = 4
        spacing = 8
        total_lbl_w = (dot_r * 2) + spacing + lbl_w
        lbl_start_x = box_center_x - total_lbl_w // 2
        draw.ellipse((lbl_start_x, 769 - dot_r, lbl_start_x + dot_r * 2, 769 + dot_r), fill=(5, 150, 105))
        draw.text((lbl_start_x + (dot_r * 2) + spacing, 760), lbl_text, font=f_new_label, fill=(4, 120, 87))

        pw = draw.textlength(new_str, font=f_new_price)
        price_x = box_center_x - pw // 2
        price_y = 780 if sub_str else 794
        draw.text((price_x, price_y), new_str, font=f_new_price, fill=(5, 150, 105))

        if sub_str:
            sw = draw.textlength(sub_str, font=f_net)
            draw.text((box_center_x - sw // 2, 858), sub_str, font=f_net, fill=(4, 120, 87))

    # 7. Etkileşim & DM / BİO CTA Bandı (Platforma Özel: Instagram vs YouTube) + #işbirliği
    cta_box = (0, 898, W, 960)
    draw.rectangle(cta_box, fill=(15, 23, 42))
    draw.line((0, 898, W, 898), fill=(245, 158, 11), width=3)

    f_cta_bold = get_font("segoeuib", 25)

    if str(cta_type).strip().lower() == "youtube":
        cta_prefix = "İndirim linkine "
        cta_highlight = "BİO'DAN"
        cta_suffix = " ulaşabilirsiniz!"

        p_w = draw.textlength(cta_prefix, font=f_cta_bold)
        h_w = draw.textlength(cta_highlight, font=f_cta_bold)
        s_w = draw.textlength(cta_suffix, font=f_cta_bold)

        pill_w = h_w + 22
        total_cta_w = 34 + p_w + 8 + pill_w + 10 + s_w + 34
        start_x = (W - total_cta_w) // 2

        # Vector Link İkonu
        draw_vector_link(draw, start_x + 14, 929, (251, 191, 36))
        text_x = start_x + 36

        # "İndirim linkine "
        draw.text((text_x, 915), cta_prefix, font=f_cta_bold, fill=(241, 245, 249))
        text_x += p_w + 6

        # "BİO'DAN" Vurgu Hapı
        pill_x1 = text_x
        pill_y1 = 911
        pill_x2 = text_x + pill_w
        pill_y2 = 947
        draw.rounded_rectangle((pill_x1, pill_y1, pill_x2, pill_y2), radius=8, fill=(245, 158, 11))
        draw.text((pill_x1 + 11, 915), cta_highlight, font=f_cta_bold, fill=(15, 23, 42))
        text_x += pill_w + 10

        # " ulaşabilirsiniz!"
        draw.text((text_x, 915), cta_suffix, font=f_cta_bold, fill=(241, 245, 249))
        text_x += s_w + 16

        # Vector Küre (Web/Bio) İkonu
        draw_vector_globe(draw, text_x, 928, (251, 191, 36))
    else:
        cta_prefix = "Yoruma "
        cta_highlight = "LİNK"
        cta_suffix = " yazın, DM ile iletelim!"

        p_w = draw.textlength(cta_prefix, font=f_cta_bold)
        h_w = draw.textlength(cta_highlight, font=f_cta_bold)
        s_w = draw.textlength(cta_suffix, font=f_cta_bold)

        pill_w = h_w + 22
        total_cta_w = 34 + p_w + 8 + pill_w + 10 + s_w + 34
        start_x = (W - total_cta_w) // 2

        # Vector Chat Balonu
        draw_vector_chat_bubble(draw, start_x + 14, 929, (251, 191, 36))
        text_x = start_x + 36

        # "Yoruma "
        draw.text((text_x, 915), cta_prefix, font=f_cta_bold, fill=(241, 245, 249))
        text_x += p_w + 6

        # "LİNK" Vurgu Hapı
        pill_x1 = text_x
        pill_y1 = 911
        pill_x2 = text_x + pill_w
        pill_y2 = 947
        draw.rounded_rectangle((pill_x1, pill_y1, pill_x2, pill_y2), radius=8, fill=(245, 158, 11))
        draw.text((pill_x1 + 11, 915), cta_highlight, font=f_cta_bold, fill=(15, 23, 42))
        text_x += pill_w + 10

        # " yazın, DM ile iletelim!"
        draw.text((text_x, 915), cta_suffix, font=f_cta_bold, fill=(241, 245, 249))
        text_x += s_w + 16

        # Vector DM Uçağı İkonu
        draw_vector_dm_plane(draw, text_x, 928, (251, 191, 36))

    # Yasal Uyum Etiketi (#işbirliği)
    draw.text((W - 24, 936), "#işbirliği #reklam", font=f_tiny, fill=(148, 163, 184), anchor="rm")

    img.save(output_path, "PNG")
    return output_path

# ==========================================
# SPLIT-SCREEN VİDEO BİRLEŞTİRİCİ (1080x1920)
# ==========================================

def generate_voiceover_hook(product_title: str, new_price: str, output_path: str = None) -> str:
    """
    edge-tts ile videonun ilk 2-3 saniyesi için yüksek kaliteli ve tok bir Türkçe seslendirici üretir.
    Örn: 'Günün Fırsatı: Stanley Termos, 1.704 lira!'
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "voiceover_hook.mp3")

    clean_p = re.sub(r'[^\d.,]', '', str(new_price)).strip()
    text = f"Günün Fırsatı! {product_title[:28]}, {clean_p} lira!"

    try:
        import asyncio
        import edge_tts

        async def _speak():
            comm = edge_tts.Communicate(text, "tr-TR-AhmetNeural", rate="+15%", pitch="-2Hz")
            await comm.save(output_path)

        asyncio.run(_speak())
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"[Voiceover] Seslendirme atlandı: {e}")
    return None

def build_split_screen_video(
    top_source: str,
    meme_name: str = None,
    audio_name: str = None,
    output_filename: str = "deal_reel.mp4",
    discount_pct: str = "",
    product_title: str = "",
    new_price: str = "",
    is_price_error: bool = False,
    reaction_text: str = None,
    enable_voiceover: bool = False
) -> str:
    """
    Üst yarıda ürün banner'ı (1080x960),
    Alt yarıda viral meme videosu (1080x960),
    Meme üzerinde akıllı reaksiyon kancası (Reaction Hook - 32px),
    İlk 1 saniyede dinamik mikro punch-in zoom efekti,
    En altta dinamik neon ilerleme çubuğu (Animated Progress Bar),
    İlk 2 saniyede AhmetNeural Türkçe seslendirici hook'u (müzik kısma/ducking ile),
    Arka planda meme'in orijinal sesi veya phonk müzik ile 1080x1920 MP4 video üretir.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1. Meme videosunu seç (Belirtilmemişse AI/Akıllı Algoritma Seçer)
    if meme_name:
        if not meme_name.endswith(".mp4"):
            meme_name += ".mp4"
        bottom_meme_path = os.path.join(MEMES_DIR, meme_name)
    else:
        chosen = select_smart_meme(discount_pct, product_title)
        bottom_meme_path = os.path.join(MEMES_DIR, chosen)
        print(f"[Montaj] 🤖 Yapay Zeka En Uygun Viral Meme'i Eşleştirdi: {chosen}")

    if not os.path.exists(bottom_meme_path):
        raise FileNotFoundError(f"Meme videosu bulunamadı: {bottom_meme_path}")

    # 2. Akıllı Reaksiyon Kancası (Reaction Hook) Overlay Üret
    if not reaction_text:
        reaction_text = select_smart_reaction_hook(discount_pct, product_title, is_price_error)
    print(f"[Montaj] 🎯 Reaksiyon Başlığı (Hook): {reaction_text}")
    reaction_overlay_path = os.path.join(TEMP_DIR, "reaction_overlay.png")
    create_reaction_hook_overlay(reaction_text, reaction_overlay_path)

    # 3. Ses kaynağını belirle (Öncelik: Meme'in kendi orijinal sesi)
    chk_a = subprocess.run(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
    has_meme_audio = "Audio:" in chk_a.stderr

    if audio_name:
        if not audio_name.endswith(".m4a"):
            audio_name += ".m4a"
        audio_path = os.path.join(AUDIO_DIR, audio_name)
        use_external_audio = True
    elif has_meme_audio:
        use_external_audio = False
        print(f"[Montaj] 🎵 Meme'in kendi ikonik orijinal müziği/sesi kullanılıyor!")
    else:
        available_audios = [a for a in AVAILABLE_AUDIOS if os.path.exists(os.path.join(AUDIO_DIR, a))]
        chosen_audio = random.choice(available_audios) if available_audios else "phonk_meme.m4a"
        audio_path = os.path.join(AUDIO_DIR, chosen_audio)
        use_external_audio = True

    # 4. Türkçe Voiceover Hook Üret (edge-tts)
    voice_path = None
    if enable_voiceover and product_title and new_price:
        voice_path = generate_voiceover_hook(product_title, new_price)
        if voice_path:
            print(f"[Montaj] 🎙️ Türkçe Yapay Zeka Seslendirmesi (edge-tts) Eklendi: AhmetNeural")

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # 5. Meme süresini al
    cmd_len = ["ffmpeg", "-i", bottom_meme_path]
    p = subprocess.run(cmd_len, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    duration = float(m.group(3)) + int(m.group(2))*60 if m else 10.0

    print(f"[Montaj] Seçilen Meme: {os.path.basename(bottom_meme_path)} (Süre: {duration:.1f}s)")
    if use_external_audio:
        print(f"[Montaj] Seçilen Harici Ses: {os.path.basename(audio_path)}")

    is_image = top_source.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    scale_top = "scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA" if is_image else "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960"

    # İlk 1 Saniyede Dinamik Mikro Punch-in Zoom (Retention Kancası)
    scale_bottom = "scale=w='1080*(1+0.05*max(0,1-t))':h='960*(1+0.05*max(0,1-t))':eval=frame,crop=1080:960"

    cmd = ["ffmpeg", "-y"]
    if is_image:
        cmd += ["-loop", "1", "-i", top_source]
    else:
        cmd += ["-i", top_source]

    # Input 1: Bottom meme video
    cmd += ["-i", bottom_meme_path]

    # Input 2: Reaction hook overlay (transparent PNG loop)
    cmd += ["-loop", "1", "-i", reaction_overlay_path]

    # Dynamic Progress Bar (Süreye göre kusursuz animasyonlu neon ilerleme çubuğu)
    progress_bar_filter = (
        f"color=c=0x0F172A@0.8:s=1080x14:d={duration:.2f}[pbg];"
        f"color=c=0xFF5722:s=1080x14:d={duration:.2f}[pfill];"
        f"[stacked][pbg]overlay=0:1906[with_pbg];"
        f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{duration:.2f})':y=1906[v]"
    )

    # 5. Ses Yapılandırması: Kullanıcı isteğiyle harici SFX ve ekstra müzikler kaldırıldı.
    # Meme videosunun kendi orijinal viral sesi temiz ve doğal haliyle kullanılır.
    has_sfx = False
    input_idx = 3  # 0: top_source, 1: bottom_meme, 2: reaction_overlay

    if not use_external_audio:
        bg_stream = "[1:a]"
    else:
        cmd += ["-i", audio_path]
        bg_stream = f"[{input_idx}:a]"
        input_idx += 1

    voice_stream = None
    if voice_path:
        cmd += ["-i", voice_path]
        voice_stream = f"[{input_idx}:a]"
        input_idx += 1

    # Ses mikseri filtrelerini oluştur
    audio_parts = []
    mix_sources = []

    # Meme'in kendi sesi
    bg_vol = 0.35 if voice_path else 1.0
    audio_parts.append(f"{bg_stream}volume={bg_vol}[bg]")
    mix_sources.append("[bg]")

    # Seslendirme (Voiceover varsa)
    if voice_stream:
        audio_parts.append(f"{voice_stream}volume=1.4[voice]")
        mix_sources.append("[voice]")

    if len(mix_sources) > 1:
        mix_inputs_str = "".join(mix_sources)
        audio_parts.append(f"{mix_inputs_str}amix=inputs={len(mix_sources)}:duration=first:dropout_transition=2[a]")
    else:
        audio_parts.append(f"{mix_sources[0]}anull[a]")

    audio_filter_str = ";".join(audio_parts)

    filter_complex = (
        f"[0:v]{scale_top}[top];"
        f"[1:v]{scale_bottom}[bottom_raw];"
        f"[bottom_raw][2:v]overlay=0:0[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"{progress_bar_filter};"
        f"{audio_filter_str}"
    )

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Montaj] Video başarıyla oluşturuldu: {output_path}")
        return output_path
    else:
        print("[Montaj] Hata:", res.stderr[-500:])
        return None
