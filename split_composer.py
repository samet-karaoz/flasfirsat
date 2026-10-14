import os
import subprocess
import random
import re
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR
from deal_hunter import parse_price_to_float

MEMES_DIR = os.path.join(BASE_DIR, "assets", "memes")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")

AVAILABLE_MEMES = [
    "knight_cat.mp4",
    "dicaprio_cheers.mp4",
    "bateman_walk.mp4",
    "bale_nod.mp4",
    "homelander_stare.mp4",
    "walter_white.mp4",
    "the_rock.mp4",
    "ryan_gosling.mp4",
    "mcconaughey_chest.mp4",
    "the_weeknd_lost.mp4",
    "bully_maguire.mp4",
    "kanye_stare.mp4",
    "vince_mcmahon.mp4",
    "cat_vibing.mp4",
    "shark_nemo.mp4",
    # Yeni Eklenen Türk Kültürü & Viral Instagram Memeleri
    "limon_davulcu.mp4",
    "angaraya_mi_geldin.mp4",
    "degirmenci_dayi_cj.mp4",
    "bicerdover_ciftetelli.mp4",
    "limon_halay.mp4"
]

AVAILABLE_AUDIOS = [
    "phonk_meme.m4a",
    "brazilian_phonk.m4a"
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

LAST_MEME_FILE = os.path.join(TEMP_DIR, "last_meme.txt")

def get_last_meme() -> str:
    try:
        if os.path.exists(LAST_MEME_FILE):
            with open(LAST_MEME_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def set_last_meme(meme_name: str):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(LAST_MEME_FILE, "w", encoding="utf-8") as f:
            f.write(meme_name)
    except Exception:
        pass

def select_smart_meme(discount_pct: str = "", title: str = "", category: str = "") -> str:
    """
    İndirim oranına, ürün kategorisine ve başlığına göre en yüksek viral potansiyele sahip
    meme videosunu kütüphaneden akıllıca seçer.
    Aynı videonun üst üste iki kez seçilmesini otomatik olarak engeller.
    """
    available = [m for m in AVAILABLE_MEMES if os.path.exists(os.path.join(MEMES_DIR, m))]
    if not available:
        available = [f for f in os.listdir(MEMES_DIR) if f.endswith(".mp4")]
    if not available:
        return "knight_cat.mp4"

    last_used = get_last_meme()

    def pick_without_repeat(candidates_list: list) -> str:
        valid = [c for c in candidates_list if c in available]
        if not valid:
            valid = available
        pool = [c for c in valid if c != last_used] if len(valid) > 1 else valid
        chosen = random.choice(pool)
        set_last_meme(chosen)
        return chosen

    pct_match = re.search(r'(\d+)', str(discount_pct))
    pct_val = int(pct_match.group(1)) if pct_match else 30
    title_low = (title or "").lower()

    # 1. Dev Çöküş İndirimleri (%40 ve üzeri) - Şok, Para & Çılgın Kutlama
    if pct_val >= 40:
        return pick_without_repeat([
            "limon_davulcu.mp4", "bicerdover_ciftetelli.mp4", "limon_halay.mp4",
            "vince_mcmahon.mp4", "walter_white.mp4", "knight_cat.mp4", "the_rock.mp4"
        ])

    # 2. Gaming, Espor ve Donanım Ürünleri - GTA CJ, ETS2 Tır & Sigma/Kedi Tepkileri
    gaming_kw = ["mouse", "kulaklık", "klavye", "gaming", "ps5", "gamepad", "espor", "oyuncu", "monitor", "ekran kartı"]
    if any(k in title_low for k in gaming_kw):
        return pick_without_repeat([
            "degirmenci_dayi_cj.mp4", "angaraya_mi_geldin.mp4", "knight_cat.mp4",
            "bateman_walk.mp4", "bale_nod.mp4", "cat_vibing.mp4", "ryan_gosling.mp4"
        ])

    # 3. Yüksek Fırsat / Viral Hit (%25 - %39) - Halay, Çiftetelli & Zafer
    if pct_val >= 25:
        return pick_without_repeat([
            "limon_halay.mp4", "bicerdover_ciftetelli.mp4", "angaraya_mi_geldin.mp4",
            "dicaprio_cheers.mp4", "knight_cat.mp4", "cat_vibing.mp4", "bully_maguire.mp4"
        ])

    # 4. Genel Ürünler
    return pick_without_repeat([
        "limon_davulcu.mp4", "bicerdover_ciftetelli.mp4", "knight_cat.mp4",
        "cat_vibing.mp4", "the_weeknd_lost.mp4", "the_rock.mp4", "dicaprio_cheers.mp4"
    ])

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

def draw_vector_coin(draw: ImageDraw.Draw, cx: int, cy: int, color=(255, 204, 0)):
    draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=color, outline=(245, 158, 11), width=2)
    draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), outline=(254, 240, 138), width=1)
    draw.line((cx - 3, cy - 5, cx + 3, cy - 5), fill=(180, 83, 9), width=2)
    draw.line((cx - 1, cy - 5, cx - 1, cy + 5), fill=(180, 83, 9), width=2)
    draw.line((cx - 3, cy, cx + 1, cy), fill=(180, 83, 9), width=2)

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

    f_hook = get_font("segoeuib", 32)  # Büyütüldü: 32px
    clean_text = reaction_text.strip()
    text_w = draw.textlength(clean_text, font=f_hook)

    box_w = min(W - 40, text_w + 64)
    box_h = 68  # Büyütüldü: 68px
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
# ANA ÜRÜN AFİŞİ (1080x960 - V2 ENHANCED)
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
    output_path: str = None
) -> str:
    """
    Ürün görseli ve fiyat bilgilerinden 1080x960 ebatlarında
    5 Temel İyileştirme içeren premium e-ticaret afişi üretir:
    1. Net Tasarruf Rozeti (💰 X TL NET TASARRUF)
    2. ManyChat CTA Bandı (💬 Satın alma linki için yoruma "LİNK" yaz)
    3. Soft 3D Drop Shadow & Derinlik
    4. Doğrulanmış Güven Rozeti (🛡️ %100 Orijinal • Doğrulanmış)
    5. Çift Fiyat & Net Maliyet Karşılaştırma Kartı (Baskın İndirim Fiyatı & Ortalanmış Üstü Çizili Eski Fiyat)
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
    f_label = get_font("segoeuib", 21)
    f_trust = get_font("segoeuib", 19)
    f_old_price = get_font("segoeuib", 30)  # Piyasa fiyatı daha kibar ve küçük: 30px
    f_new_label = get_font("segoeuib", 21)
    f_new_price = get_font("segoeuib", 62)  # İndirimli fiyat son derece baskın: 62px
    f_net = get_font("segoeuib", 20)
    f_pct = get_font("segoeuib", 28)
    f_savings = get_font("segoeuib", 22)
    f_cta = get_font("segoeuib", 24)

    # 1. Sol Üst Rozet: DEV İNDİRİM (Vector Şimşekli)
    clean_badge = badge_text.strip() if badge_text else "DEV İNDİRİM"
    b_w = draw.textlength(clean_badge, font=f_badge)
    badge_fill = (255, 87, 34)  # Alev Turuncusu (#FF5722)
    draw.rounded_rectangle((40, 22, 40 + b_w + 58, 74), radius=14, fill=badge_fill)
    draw_vector_bolt(draw, 64, 48, (255, 204, 0))
    draw.text((82, 34), clean_badge, font=f_badge, fill=(255, 255, 255))

    # 2. Sağ Üst Rozet: % İNDİRİM
    clean_pct = discount_pct.strip()
    if clean_pct and not clean_pct.endswith("İNDİRİM"):
        clean_pct = f"{clean_pct} İNDİRİM"
    p_w = draw.textlength(clean_pct, font=f_pct)
    draw.rounded_rectangle((W - 40 - p_w - 38, 22, W - 40, 74), radius=14, fill=(225, 29, 72))  # Canlı Kırmızı
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

    # Güven Rozeti (Kart İçi Sol Üst - Vector Shield & Checkmark)
    trust_text = "ORİJİNAL ÜRÜN • DOĞRULANMIŞ"
    tr_w = draw.textlength(trust_text, font=f_trust)
    draw.rounded_rectangle((card_box[0] + 16, card_box[1] + 16, card_box[0] + 58 + tr_w, card_box[1] + 48), radius=8, fill=(241, 245, 249))
    draw_vector_shield_check(draw, card_box[0] + 32, card_box[1] + 32, (16, 185, 129))
    draw.text((card_box[0] + 48, card_box[1] + 21), trust_text, font=f_trust, fill=(71, 85, 105))

    # Ürün Görselini Kart İçine Ekle
    if product_image_path and os.path.exists(product_image_path):
        try:
            p_img = Image.open(product_image_path).convert("RGBA")
            max_img_w = card_box[2] - card_box[0] - 60
            max_img_h = card_box[3] - card_box[1] - 70
            p_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2 + 10
            img.paste(p_img, (px, py), p_img)
        except Exception as e:
            print(f"[Banner] Görsel yükleme uyarısı: {e}")

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
    draw.rounded_rectangle((card_box[2] - t_w - 36, card_box[3] - 46, card_box[2] - 16, card_box[3] - 14), radius=8, fill=st_info["bg"])
    draw.text((card_box[2] - t_w - 26, card_box[3] - 42), tag_text, font=f_label, fill=st_info["fg"])

    # Kart İçi Dinamik Taksit Rozeti (Sol Alt Köşe)
    if installment:
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()
        inst_label = f"Taksit: {clean_inst}" if "taksit" not in clean_inst.lower() else clean_inst
        it_w = draw.textlength(inst_label, font=f_label)
        draw.rounded_rectangle((card_box[0] + 16, card_box[3] - 46, card_box[0] + 16 + it_w + 24, card_box[3] - 14), radius=8, fill=(236, 253, 245), outline=(16, 185, 129), width=1)
        draw.ellipse((card_box[0] + 24, card_box[3] - 33, card_box[0] + 32, card_box[3] - 25), fill=(5, 150, 105))
        draw.text((card_box[0] + 38, card_box[3] - 42), inst_label, font=f_label, fill=(4, 120, 87))

    # 5. Net Tasarruf Rozeti (Floating Savings Pill)
    old_val = parse_price_to_float(old_price)
    new_val = parse_price_to_float(new_price)
    savings = old_val - new_val if (old_val and new_val and old_val > new_val) else 0

    if savings > 0:
        sav_str = f"{int(savings):,} TL".replace(',', '.')
        sav_text = f"{sav_str} NET TASARRUF"
    else:
        sav_text = "KAÇIRILMAYACAK FIRSAT"

    s_w = draw.textlength(sav_text, font=f_savings)
    pill_w = s_w + 64
    pill_x = (W - pill_w) // 2
    # Pill drop shadow
    draw.rounded_rectangle((pill_x + 1, 716, pill_x + pill_w + 1, 752), radius=12, fill=(200, 205, 215))
    draw.rounded_rectangle((pill_x, 715, pill_x + pill_w, 751), radius=12, fill=(16, 185, 129))
    draw_vector_coin(draw, pill_x + 24, 733, (255, 204, 0))
    draw.text((pill_x + 44, 722), sav_text, font=f_savings, fill=(255, 255, 255))

    # 6. Fiyat Kartları: Çift Kartlı Premium Tasarım
    # Sol Kart: Piyasa Fiyatı (Daha kibar, üstü tam ortadan çizili)
    old_box = (40, 758, 420, 888)
    draw.rounded_rectangle(old_box, radius=16, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
    draw.text((old_box[0] + 20, 770), "PİYASA FİYATI", font=f_label, fill=(148, 163, 184))
    old_str = old_price if old_price else "Piyasa Fiyatı"
    op_w = draw.textlength(old_str, font=f_old_price)
    op_x = old_box[0] + (old_box[2] - old_box[0] - op_w) // 2
    op_y = 814
    draw.text((op_x, op_y), old_str, font=f_old_price, fill=(148, 163, 184))
    
    # Tam merkezden geçen kırmızı çizgi (textbbox ile tam ortalanır)
    tbbox = draw.textbbox((op_x, op_y), old_str, font=f_old_price)
    strike_y = (tbbox[1] + tbbox[3]) // 2
    draw.line((op_x - 8, strike_y, op_x + op_w + 8, strike_y), fill=(239, 68, 68), width=3)

    # Orta Geçiş İkonu (Chevron >)
    arrow_box = (436, 800, 484, 846)
    draw.rounded_rectangle(arrow_box, radius=10, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    cx, cy = 460, 823
    draw.line((cx - 4, cy - 8, cx + 4, cy), fill=(234, 88, 12), width=3)
    draw.line((cx + 4, cy, cx - 4, cy + 8), fill=(234, 88, 12), width=3)

    # Sağ Kart: İndirimli Yeni Fiyat (Baskın Zümrüt Yeşili 62px)
    new_box = (500, 758, W - 40, 888)
    draw.rounded_rectangle(new_box, radius=16, fill=(236, 253, 245), outline=(16, 185, 129), width=2)
    draw.ellipse((new_box[0] + 20, 776, new_box[0] + 28, 784), fill=(5, 150, 105))
    draw.text((new_box[0] + 34, 767), "İNDİRİMLİ FIRSAT FİYATI", font=f_new_label, fill=(4, 120, 87))

    new_str = new_price if new_price else "Fırsat Fiyatı"
    draw.text((new_box[0] + 20, 792), new_str, font=f_new_price, fill=(5, 150, 105))

    # Net / Taksit / Kampanya alt satırı
    sub_parts = []
    if net_cost:
        clean_net = re.sub(r'[^\w\s.,xX+\-/%]', '', net_cost).strip()
        sub_parts.append(f"Net: {clean_net}")
    if installment:
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()
        sub_parts.append(clean_inst)
    if sub_parts:
        sub_str = "  •  ".join(sub_parts)
        draw.text((new_box[0] + 20, 858), sub_str, font=f_net, fill=(4, 120, 87))

    # 7. ManyChat CTA Bandı (Alt Şerit 1080x62)
    cta_box = (0, 898, W, 960)
    draw.rectangle(cta_box, fill=(15, 23, 42))
    draw.line((0, 898, W, 898), fill=(245, 158, 11), width=3)

    cta_prefix = "Satın alma linki için yoruma "
    cta_highlight = '"LİNK"'
    cta_suffix = " yaz (Anında DM)"

    p_w = draw.textlength(cta_prefix, font=f_cta)
    h_w = draw.textlength(cta_highlight, font=f_cta)
    s_w = draw.textlength(cta_suffix, font=f_cta)
    total_cta_w = 32 + 10 + p_w + h_w + s_w + 10 + 26
    start_x = (W - total_cta_w) // 2

    draw_vector_chat_bubble(draw, start_x + 14, 929, (251, 191, 36))
    text_x = start_x + 36
    draw.text((text_x, 916), cta_prefix, font=f_cta, fill=(241, 245, 249))
    text_x += p_w
    draw.text((text_x, 916), cta_highlight, font=f_cta, fill=(251, 191, 36))
    text_x += h_w
    draw.text((text_x, 916), cta_suffix, font=f_cta, fill=(241, 245, 249))
    text_x += s_w + 14
    draw_vector_dm_plane(draw, text_x, 929, (251, 191, 36))

    img.save(output_path, "PNG")
    return output_path

# ==========================================
# SPLIT-SCREEN VİDEO BİRLEŞTİRİCİ (1080x1920)
# ==========================================

def build_split_screen_video(
    top_source: str,
    meme_name: str = None,
    audio_name: str = None,
    output_filename: str = "deal_reel.mp4",
    discount_pct: str = "",
    product_title: str = "",
    is_price_error: bool = False,
    reaction_text: str = None
) -> str:
    """
    Üst yarıda ürün banner'ı (1080x960),
    Alt yarıda viral meme videosu (1080x960),
    Meme üzerinde akıllı reaksiyon kancası (Reaction Hook - 32px),
    En altta dinamik neon ilerleme çubuğu (Animated Progress Bar),
    Arka planda meme'in orijinal sesi veya phonk müzik ile 1080x1920 MP4 video üretir.
    (Alarm sesi tamamen kaldırılmıştır).
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

    # 2. Akıllı Reaksiyon Kancası (Reaction Hook) Overlay Üret (Büyük ve Okunaklı)
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

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # 4. Meme süresini al
    cmd_len = ["ffmpeg", "-i", bottom_meme_path]
    p = subprocess.run(cmd_len, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    duration = float(m.group(3)) + int(m.group(2))*60 if m else 10.0

    print(f"[Montaj] Seçilen Meme: {os.path.basename(bottom_meme_path)} (Süre: {duration:.1f}s)")
    if use_external_audio:
        print(f"[Montaj] Seçilen Harici Ses: {os.path.basename(audio_path)}")

    is_image = top_source.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    scale_top = "scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA" if is_image else "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960"
    scale_bottom = "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960"

    cmd = ["ffmpeg", "-y"]
    if is_image:
        cmd += ["-loop", "1", "-i", top_source]
    else:
        cmd += ["-i", top_source]

    # Input 1: Bottom meme video
    cmd += ["-i", bottom_meme_path]

    # Input 2: Reaction hook overlay (transparent PNG loop)
    cmd += ["-loop", "1", "-i", reaction_overlay_path]

    # Dynamic Progress Bar Filter
    # 0x0F172A@0.6 (Dark track) + 0xEA580C (Neon orange progress bar at y=1908, height=12)
    progress_bar_filter = (
        f"drawbox=x=0:y=1908:w=1080:h=12:color=0x0F172A@0.6:t=fill,"
        f"drawbox=x=0:y=1908:w='1080*t/{duration:.2f}':h=12:color=0xEA580C:t=fill"
    )

    if not use_external_audio:
        # Meme'in kendi sesi (alarm olmadan temiz ses miksi)
        filter_complex = (
            f"[0:v]{scale_top}[top];"
            f"[1:v]{scale_bottom}[bottom_raw];"
            f"[bottom_raw][2:v]overlay=0:0[bottom];"
            f"[top][bottom]vstack=inputs=2[stacked];"
            f"[stacked]{progress_bar_filter}[v];"
            f"[1:a]volume=1.0[a]"
        )
    else:
        # Harici fon müziği
        cmd += ["-i", audio_path]
        filter_complex = (
            f"[0:v]{scale_top}[top];"
            f"[1:v]{scale_bottom}[bottom_raw];"
            f"[bottom_raw][2:v]overlay=0:0[bottom];"
            f"[top][bottom]vstack=inputs=2[stacked];"
            f"[stacked]{progress_bar_filter}[v];"
            f"[3:a]volume=1.0[a]"
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
