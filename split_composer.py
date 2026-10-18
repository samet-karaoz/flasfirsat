import os
import subprocess
import random
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, DATA_DIR, safe_run_subprocess
from deal_hunter import parse_price_to_float

MEMES_DIR = os.path.join(BASE_DIR, "assets", "memes")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")

# Dengeli, türlerine göre ardışık dizilmiş ana rotasyon havuzu (Round-Robin)
MEME_ROTATION_ORDER = [
    "degirmenci_dayi_cj.mp4",    # 1. Değirmenci Dayı (CJ)
    "knight_cat.mp4",            # 2. Zırhlı Şövalye Kedi
    "limon_halay.mp4",           # 3. Limon Halay
    "bicerdover_ciftetelli.mp4",  # 4. Biçerdöver Çiftetelli
    "homelander_stare.mp4",      # 5. Homelander (Şok / Ciddi Bakış)
    "the_rock.mp4",              # 6. The Rock (Tek Kaş Kaldırma)
    "vince_mcmahon.mp4",         # 7. Vince McMahon (Para / Şok Sevinç)
    "bale_nod.mp4",              # 8. Christian Bale (Onaylama / Takdir)
    "angaraya_mi_geldin.mp4",    # 9. Angara'ya mı geldin la
    "cat_vibing.mp4",            # 10. Vibing Cat (Ritimle Kafa Sallayan Kedi)
    "limon_davulcu.mp4"          # 11. Limoncu Davulcu
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
    Pilmoji ile gerçek renkli emojileri destekler, font uyumsuzluğunda tofu (▢) kutuları engeller.
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "reaction_overlay.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    W, H = 1080, 960
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    f_hook = get_font("segoeuib", 32)  # 32px Büyütülmüş font
    clean_text = reaction_text.strip()

    try:
        from pilmoji import Pilmoji
        has_pilmoji = True
    except ImportError:
        has_pilmoji = False

    if has_pilmoji:
        with Pilmoji(img) as p:
            text_w, text_h = p.getsize(clean_text, font=f_hook)
            box_w = min(W - 120, text_w + 64)
            box_h = 68
            box_x = (W - box_w) // 2
            box_y = 26

            draw.rounded_rectangle(
                (box_x, box_y, box_x + box_w, box_y + box_h),
                radius=18,
                fill=(15, 23, 42, 230),
                outline=(255, 255, 255, 110),
                width=2
            )
            tx = (W - text_w) // 2
            ty = box_y + (box_h - text_h) // 2
            p.text((tx, ty), clean_text, font=f_hook, fill=(255, 255, 255))
    else:
        # Pilmoji yoksa emoji kaynaklı tofu (▢) kutucukları temizle
        try:
            import emoji
            safe_text = emoji.replace_emoji(clean_text, replace="").strip()
        except ImportError:
            import re
            safe_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text).strip()

        text_w = draw.textlength(safe_text, font=f_hook)
        box_w = min(W - 120, text_w + 64)
        box_h = 68
        box_x = (W - box_w) // 2
        box_y = 26

        draw.rounded_rectangle(
            (box_x, box_y, box_x + box_w, box_y + box_h),
            radius=18,
            fill=(15, 23, 42, 230),
            outline=(255, 255, 255, 110),
            width=2
        )
        t_bbox = draw.textbbox((0, 0), safe_text, font=f_hook)
        t_h = t_bbox[3] - t_bbox[1]
        tx = (W - text_w) // 2
        ty = box_y + (box_h - t_h) // 2 - t_bbox[1]
        draw.text((tx, ty), safe_text, font=f_hook, fill=(255, 255, 255, 255))

    img.save(output_path, "PNG")
    return output_path

# ==========================================
# AKILLI DİNAMİK RENK SKALASI & TEMA MOTORU (4 STÜDYO ŞABLONU)
# ==========================================

BANNER_THEMES = {
    "obsidian_dark": {
        "name": "Obsidian Cyber-Luxury (Koyu Sinematik & Neon Zümrüt)",
        "bg_top": (11, 15, 25),
        "bg_bottom": (20, 28, 46),
        "title_color": (248, 250, 252),
        "card_border": (56, 189, 248),
        "glow_color": (56, 189, 248, 95),
        "badge_left_bg": (234, 88, 12),
        "badge_right_bg": (225, 29, 72),
        "old_box_bg": (30, 41, 59),
        "old_box_border": (71, 85, 105),
        "old_text_col": (148, 163, 184),
        "arrow_bg": (30, 41, 59),
        "arrow_fg": (56, 189, 248),
        "new_box_bg": (6, 78, 59),
        "new_box_border": (16, 185, 129),
        "new_label_col": (167, 243, 208),
        "new_price_col": (52, 211, 153),
        "savings_pill_bg": (245, 158, 11),
        "savings_pill_fg": (15, 23, 42),
        "cta_bg": (9, 13, 22),
        "cta_line": (56, 189, 248),
        "cta_pill_bg": (56, 189, 248),
        "cta_pill_fg": (9, 13, 22),
        "trust_bg": (241, 245, 249),
        "trust_fg": (30, 41, 59),
        "inst_bg": (236, 253, 245),
        "inst_fg": (4, 120, 87),
    },
    "studio_warm": {
        "name": "Apple Studio Warm-Luxury (Sıcak Krem & Koyu Lacivert Kontrast)",
        "bg_top": (250, 247, 242),
        "bg_bottom": (238, 232, 222),
        "title_color": (15, 23, 42),
        "card_border": (214, 206, 194),
        "glow_color": (251, 191, 36, 95),
        "badge_left_bg": (15, 23, 42),
        "badge_right_bg": (220, 38, 38),
        "old_box_bg": (255, 255, 255),
        "old_box_border": (203, 213, 225),
        "old_text_col": (100, 116, 139),
        "arrow_bg": (255, 255, 255),
        "arrow_fg": (234, 88, 12),
        "new_box_bg": (15, 23, 42),
        "new_box_border": (245, 158, 11),
        "new_label_col": (253, 224, 71),
        "new_price_col": (74, 222, 128),
        "savings_pill_bg": (16, 185, 129),
        "savings_pill_fg": (255, 255, 255),
        "cta_bg": (15, 23, 42),
        "cta_line": (245, 158, 11),
        "cta_pill_bg": (245, 158, 11),
        "cta_pill_fg": (15, 23, 42),
        "trust_bg": (241, 245, 249),
        "trust_fg": (51, 65, 85),
        "inst_bg": (236, 253, 245),
        "inst_fg": (4, 120, 87),
    },
    "fiyat_hatasi_alarm": {
        "name": "Kırmızı Alarm / Fiyat Hatası Modu (Crimson & Gold)",
        "bg_top": (69, 10, 10),
        "bg_bottom": (24, 10, 14),
        "title_color": (255, 255, 255),
        "card_border": (248, 113, 113),
        "glow_color": (251, 146, 60, 115),
        "badge_left_bg": (220, 38, 38),
        "badge_right_bg": (245, 158, 11),
        "old_box_bg": (45, 18, 22),
        "old_box_border": (153, 27, 27),
        "old_text_col": (252, 165, 165),
        "arrow_bg": (45, 18, 22),
        "arrow_fg": (250, 204, 21),
        "new_box_bg": (20, 20, 25),
        "new_box_border": (250, 204, 21),
        "new_label_col": (253, 224, 71),
        "new_price_col": (250, 204, 21),
        "savings_pill_bg": (220, 38, 38),
        "savings_pill_fg": (255, 255, 255),
        "cta_bg": (127, 29, 29),
        "cta_line": (250, 204, 21),
        "cta_pill_bg": (250, 204, 21),
        "cta_pill_fg": (69, 10, 10),
        "trust_bg": (254, 242, 242),
        "trust_fg": (153, 27, 27),
        "inst_bg": (254, 242, 242),
        "inst_fg": (185, 28, 28),
    },
    "cyber_gaming": {
        "name": "Cyber Gaming & Setup (Elektrik İndigo & Neon Pembe)",
        "bg_top": (238, 242, 255),
        "bg_bottom": (224, 231, 255),
        "title_color": (30, 27, 75),
        "card_border": (129, 140, 248),
        "glow_color": (167, 139, 250, 95),
        "badge_left_bg": (79, 70, 229),
        "badge_right_bg": (236, 72, 153),
        "old_box_bg": (255, 255, 255),
        "old_box_border": (199, 210, 254),
        "old_text_col": (100, 116, 139),
        "arrow_bg": (255, 255, 255),
        "arrow_fg": (79, 70, 229),
        "new_box_bg": (236, 253, 245),
        "new_box_border": (16, 185, 129),
        "new_label_col": (4, 120, 87),
        "new_price_col": (5, 150, 105),
        "savings_pill_bg": (79, 70, 229),
        "savings_pill_fg": (255, 255, 255),
        "cta_bg": (30, 27, 75),
        "cta_line": (236, 72, 153),
        "cta_pill_bg": (250, 204, 21),
        "cta_pill_fg": (30, 27, 75),
        "trust_bg": (238, 242, 255),
        "trust_fg": (49, 46, 129),
        "inst_bg": (236, 253, 245),
        "inst_fg": (4, 120, 87),
    },
    "emerald_trust": {
        "name": "Zümrüt Yeşili & Altın (Doğal Yaşam, Mutfak & Sağlık)",
        "bg_top": (236, 253, 245),
        "bg_bottom": (209, 250, 229),
        "title_color": (6, 78, 59),
        "card_border": (52, 211, 153),
        "glow_color": (16, 185, 129, 90),
        "badge_left_bg": (6, 78, 59),
        "badge_right_bg": (16, 185, 129),
        "old_box_bg": (255, 255, 255),
        "old_box_border": (167, 243, 208),
        "old_text_col": (100, 116, 139),
        "arrow_bg": (255, 255, 255),
        "arrow_fg": (5, 150, 105),
        "new_box_bg": (6, 78, 59),
        "new_box_border": (245, 158, 11),
        "new_label_col": (253, 224, 71),
        "new_price_col": (52, 211, 153),
        "savings_pill_bg": (16, 185, 129),
        "savings_pill_fg": (255, 255, 255),
        "cta_bg": (6, 78, 59),
        "cta_line": (245, 158, 11),
        "cta_pill_bg": (245, 158, 11),
        "cta_pill_fg": (6, 78, 59),
        "trust_bg": (241, 245, 249),
        "trust_fg": (6, 78, 59),
        "inst_bg": (236, 253, 245),
        "inst_fg": (4, 120, 87),
    }
}

def select_banner_theme(title: str = "", discount_pct: str = "", badge_text: str = "", theme_name: str = "auto") -> dict:
    """
    Ürünün indirim oranına, kategorisine ve görsel çeşitlilik algoritmasına göre 5 lüks stüdyo şablonundan en uygun olanı seçer.
    """
    if theme_name and theme_name in BANNER_THEMES:
        return BANNER_THEMES[theme_name]

    pct_m = re.search(r'(\d+)', str(discount_pct))
    pct_val = int(pct_m.group(1)) if pct_m else 0
    t_low = (title or "").lower()
    b_low = (badge_text or "").lower()

    # 1. %38 ve üzeri dev indirim veya Fiyat Hatası şüphesi -> Şablon: Kırmızı Alarm (fiyat_hatasi_alarm)
    if pct_val >= 38 or "hata" in b_low or "alarm" in b_low or "acil" in b_low:
        return BANNER_THEMES["fiyat_hatasi_alarm"]

    # 2. Gaming / Setup / Bilgisayar Ekipmanları -> Şablon: Cyber Gaming & Setup
    gaming_kw = [
        "mouse", "klavye", "kulaklık", "monitör", "monitor", "gaming", "oyuncu",
        "ps5", "gamepad", "koltuk", "ekran kartı", "ssd", "ram", "laptop",
        "notebook", "kasa", "anakart", "işlemci", "webcam", "mikrofon", "north bayou"
    ]
    if any(k in t_low for k in gaming_kw):
        return BANNER_THEMES["cyber_gaming"]

    # 3. Mutfak, Sağlık, Termos, Doğal Yaşam -> Şablon: Zümrüt Yeşili (emerald_trust)
    nature_kw = [
        "termos", "stanley", "kahve", "airfryer", "tencere", "tava", "blender",
        "çay", "filtre", "su arıtma", "vitamin", "organik", "sağlık"
    ]
    if any(k in t_low for k in nature_kw):
        return BANNER_THEMES["emerald_trust"]

    # 4. Ev, Yaşam, Kişisel Bakım, Kozmetik, Giyim -> Şablon: Apple Studio Warm
    warm_kw = [
        "krem", "bakım", "parfüm", "şampuan", "deterjan", "ayakkabı", "çanta",
        "kamp", "çadır", "ütü", "süpürge", "tıraş", "saç", "fırın", "tost"
    ]
    if any(k in t_low for k in warm_kw):
        return BANNER_THEMES["studio_warm"]

    # 5. Akşam kuşağı veya genel teknoloji ürünleri -> Şablon: Koyu Obsidyen Altın
    import datetime as _dt
    curr_hour = _dt.datetime.now().hour
    if curr_hour >= 18 or curr_hour < 7:
        return BANNER_THEMES["obsidian_dark"]

    return BANNER_THEMES["studio_warm"]

# ==========================================
# ANA ÜRÜN AFİŞİ (1080x960 - V4 STUDIO MULTI-THEME)
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
    output_path: str = None,
    theme_name: str = "auto",
    deal_code: str = ""
) -> str:
    """
    Ürün görseli ve fiyat bilgilerinden 1080x960 ebatlarında
    4 dinamik renk skalasına sahip stüdyo kalitesinde afiş üretir:
    1. Akıllı Dinamik Renk Skalası (Obsidian Dark, Studio Warm, Kırmızı Alarm, Cyber Gaming)
    2. Ürün altında gerçekçi 3D Zemin Gölgesi (Contact Floor Shadow) ve Renkli Spotlight
    3. "Son 30 Günün En Düşüğü" veya piyasa doğrulama rozeti
    4. Dürüst Fiyat Mimarisi (Doğrulanmışsa 2 kutulu, doğrulanmamışsa tek büyük Hero kutusu)
    5. Anti-Spam "LİNK GÖNDER" CTA Bandı ve #işbirliği yasal etiketi
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "product_top.png")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    theme = select_banner_theme(title=title, discount_pct=discount_pct, badge_text=badge_text, theme_name=theme_name)
    print(f"[Banner Engine] 🎨 Seçilen Renk Skalası: {theme['name']}")

    W, H = 1080, 960
    bg_top = theme["bg_top"]
    bg_bottom = theme["bg_bottom"]

    # Dikey yumuşak stüdyo gradyan arka planı
    base_rgb = Image.new("RGB", (W, H), bg_top)
    draw_bg = ImageDraw.Draw(base_rgb)
    for y in range(H):
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * (y / H))
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * (y / H))
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * (y / H))
        draw_bg.line([(0, y), (W, y)], fill=(r, g, b))

    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    f_badge = get_font("segoeuib", 25)
    f_label = get_font("segoeuib", 20)
    f_trust = get_font("segoeuib", 19)
    f_feature = get_font("segoeuib", 20)
    f_old_lbl = get_font("segoeuib", 17)
    f_old_price = get_font("segoeuib", 36)
    f_new_label = get_font("segoeuib", 20)
    f_new_price = get_font("segoeuib", 60)
    f_net = get_font("segoeuib", 19)
    f_pct = get_font("segoeuib", 26)
    f_savings = get_font("segoeuib", 21)
    f_tiny = get_font("segoeuib", 13)

    # 1. Sol Üst Rozet: Kategoriye Özel Dinamik Kanca Rozeti (Hedef Kitleyi Durduran Rozet)
    clean_badge = badge_text.strip() if badge_text else ""
    pct_m = re.search(r'(\d+)', str(discount_pct))
    pct_val = int(pct_m.group(1)) if pct_m else 0
    t_low = (title or "").lower()

    if not clean_badge or clean_badge in ["DEV İNDİRİM", "SÜPER FIRSAT", "GÜNÜN FIRSATI"]:
        if pct_val >= 40:
            clean_badge = "FİYAT HATASI OLABİLİR"
        elif any(k in t_low for k in ["monitör", "monitor", "klavye", "mouse", "kulaklık", "gaming", "oyuncu", "gamepad", "ekran kartı", "ps5", "xbox"]):
            clean_badge = "OYUNCU FIRSATI"
        elif any(k in t_low for k in ["kahve", "termos", "stanley", "airfryer", "tencere", "tava", "blender", "mutfak", "süpürge", "fırın", "çay"]):
            clean_badge = "MUTFAK & EV FIRSATI"
        elif any(k in t_low for k in ["şarj", "powerbank", "bluetooth", "hoparlör", "saat", "tablet", "kablo", "adaptör", "kulak içi"]):
            clean_badge = "TEKNOLOJİ FIRSATI"
        elif any(k in t_low for k in ["krem", "parfüm", "serum", "şampuan", "tıraş", "bakım", "losyon", "güneş", "diş"]):
            clean_badge = "BAKIM & KOZMETİK"
        elif pct_val >= 30:
            clean_badge = "SÜPER FIRSAT"
        else:
            clean_badge = "GÜNÜN FIRSATI"

    b_w = draw.textlength(clean_badge, font=f_badge)
    b1_x2 = int(54 + b_w + 64)
    draw.rounded_rectangle((54, 80, b1_x2, 132), radius=14, fill=theme["badge_left_bg"])
    draw_vector_bolt(draw, 78, 106, (255, 215, 0))
    draw.text((96 + b_w // 2, 106), clean_badge, font=f_badge, fill=(255, 255, 255), anchor="mm")

    # 2. Sağ Üst Rozet: % İNDİRİM (Varsa) (Reels Safe Zone: Sağdan 54px ve Üstten 80px)
    clean_pct = discount_pct.strip()
    if clean_pct and clean_pct != "0%" and clean_pct != "-0%":
        if not clean_pct.endswith("İNDİRİM") and not clean_pct.endswith("FİYAT"):
            clean_pct = f"{clean_pct} İNDİRİM"
        p_w = draw.textlength(clean_pct, font=f_pct)
        b2_x1 = int(W - 54 - p_w - 44)
        draw.rounded_rectangle((b2_x1, 80, W - 54, 132), radius=14, fill=theme["badge_right_bg"])
        draw.text(((b2_x1 + W - 54) // 2, 106), clean_pct, font=f_pct, fill=(255, 255, 255), anchor="mm")

    # 3. Başlık (Temiz 1 veya 2 Satır Formatı - Reels Safe Zone: y=145..205)
    title_lines = wrap_text(title, max_chars_per_line=36)
    if len(title_lines) == 1:
        f_title = get_font("segoeuib", 34)
        draw.text((54, 172), title_lines[0], font=f_title, fill=theme["title_color"], anchor="lm")
        card_top = 206
    else:
        f_title = get_font("segoeuib", 29)
        draw.text((54, 146), title_lines[0], font=f_title, fill=theme["title_color"])
        draw.text((54, 180), title_lines[1], font=f_title, fill=theme["title_color"])
        card_top = 216

    # 4. Ürün Kartı (Stüdyo Çerçevesi - Kenarlardan 54px ferah pay)
    card_box = (54, card_top, W - 54, 734)
    draw.rounded_rectangle(card_box, radius=24, fill=(255, 255, 255, 255), outline=theme["card_border"], width=3)

    # 🌟 Ürün Arkasına Temaya Uyumlu Soft Spotlight (Işıma) Efekti
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    glow_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    gcx = cw // 2
    gcy = ch // 2 + 6
    glow_draw.ellipse((gcx - 210, gcy - 185, gcx + 210, gcy + 185), fill=theme["glow_color"])
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=55))
    img.paste(glow_layer, (card_box[0], card_box[1]), glow_layer)
    draw = ImageDraw.Draw(img, "RGBA")

    # 🛡️ Kart İçi Sol Üst: Resmi Satıcı Doğrulama Rozeti
    if seller_badge_text:
        trust_text = seller_badge_text
    else:
        trust_text = "AMAZON TR RESMİ SATICI" if "amazon" in store_name.lower() else f"{store_name.upper()} DOĞRULANMIŞ"
    tr_w = draw.textlength(trust_text, font=f_trust)
    tx2 = int(card_box[0] + 60 + tr_w)
    draw.rounded_rectangle((card_box[0] + 16, card_box[1] + 16, tx2, card_box[1] + 50), radius=10, fill=theme["trust_bg"])
    draw_vector_shield_check(draw, card_box[0] + 33, card_box[1] + 33, (16, 185, 129))
    draw.text((card_box[0] + 50 + tr_w // 2, card_box[1] + 33), trust_text, font=f_trust, fill=theme["trust_fg"], anchor="mm")

    # 🏷️ Kart İçi Sağ Üst: "Son 30 Günün En Düşüğü" veya "Piyasanın X TL Altında"
    top_badge_text = ""
    if is_lowest_30d:
        top_badge_text = "SON 30 GÜNÜN EN DÜŞÜĞÜ"
    elif market_badge:
        top_badge_text = market_badge.strip().upper()

    if top_badge_text:
        low_w = draw.textlength(top_badge_text, font=f_trust)
        lx1 = int(card_box[2] - low_w - 58)
        draw.rounded_rectangle((lx1, card_box[1] + 16, card_box[2] - 16, card_box[1] + 50), radius=10, fill=(255, 241, 242), outline=(254, 205, 211), width=1)
        draw_vector_trend_down(draw, lx1 + 20, card_box[1] + 33, (225, 29, 72))
        draw.text((lx1 + 36 + low_w // 2, card_box[1] + 33), top_badge_text, font=f_trust, fill=(225, 29, 72), anchor="mm")

    # 🎨 rembg ile Arka Planı Temizlenmiş Ürün Görseli + 3D Zemin Gölgesi (Contact Floor Shadow)
    if product_image_path and os.path.exists(product_image_path):
        try:
            cutout_path = f"{os.path.splitext(product_image_path)[0]}_cutout.png"
            if not os.path.exists(cutout_path) or os.path.getmtime(cutout_path) < os.path.getmtime(product_image_path):
                try:
                    import rembg
                    with Image.open(product_image_path) as raw_p:
                        cutout = rembg.remove(raw_p)
                        cutout.save(cutout_path)
                except Exception as ex:
                    print(f"[Banner] rembg atlandı/uyarısı: {ex}")

            load_path = cutout_path if os.path.exists(cutout_path) else product_image_path
            p_img = Image.open(load_path).convert("RGBA")
            alpha = p_img.split()[-1]
            bbox = alpha.getbbox()
            if bbox:
                p_img = p_img.crop(bbox)

            max_img_w = card_box[2] - card_box[0] - 70
            max_img_h = card_box[3] - card_box[1] - 135
            p_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2 - 10

            # 3D Zemin Gölgesi (Ürünün havada asılı durmasını engeller, stüdyo derinliği verir)
            sh_w = max(80, int(p_img.width * 0.82))
            sh_h = 30
            shadow_layer = Image.new("RGBA", (sh_w + 80, sh_h + 60), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(shadow_layer)
            sh_draw.ellipse((40, 30, 40 + sh_w, 30 + sh_h), fill=(15, 23, 42, 85))
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=13))
            sh_x = card_box[0] + (card_box[2] - card_box[0] - shadow_layer.width) // 2
            sh_y = py + p_img.height - 20
            img.paste(shadow_layer, (sh_x, sh_y), shadow_layer)

            img.paste(p_img, (px, py), p_img)
            draw = ImageDraw.Draw(img, "RGBA")
        except Exception as e:
            print(f"[Banner] Görsel yükleme uyarısı: {e}")

    # 📦 Ürünün Can Alıcı Killer Hook / Özellik Rozeti (Varsa)
    if feature_text and len(feature_text.strip()) > 3:
        # Standart PIL TTF fontları için emoji karakterlerini temizle (Vector bolt zaten çiziliyor)
        clean_feat = re.sub(r'[\U00010000-\U0010ffff]', '', feature_text)
        clean_feat = re.sub(r'[\u2600-\u27BF]', '', clean_feat).strip().upper()
        f_killer = get_font("segoeuib", 24)
        feat_w = draw.textlength(clean_feat, font=f_killer)
        feat_box_w = min(W - 80, int(feat_w + 64))
        feat_box_h = 50
        feat_x = (W - feat_box_w) // 2
        feat_y = card_box[3] - 58
        # Derin obsidian zemin ve altın/parlak sarı çerçeve
        draw.rounded_rectangle((feat_x, feat_y, feat_x + feat_box_w, feat_y + feat_box_h), radius=16, fill=(15, 23, 42, 245), outline=(250, 204, 21), width=2)
        draw_vector_bolt(draw, feat_x + 22, feat_y + feat_box_h // 2, (250, 204, 21))
        draw.text((feat_x + 36 + feat_w // 2, feat_y + feat_box_h // 2), clean_feat, font=f_killer, fill=(254, 240, 138), anchor="mm")
    else:
        # Kart İçi Dinamik Mağaza Rozeti (Sağ Alt Köşe)
        store_styles = {
            "Trendyol": {"name": "TRENDYOL", "bg": (242, 122, 26), "fg": (255, 255, 255)},
            "Hepsiburada": {"name": "HEPSİBURADA", "bg": (255, 96, 0), "fg": (255, 255, 255)},
            "Amazon TR": {"name": "AMAZON TÜRKİYE", "bg": (15, 23, 42), "fg": (255, 255, 255)},
            "Amazon": {"name": "AMAZON TÜRKİYE", "bg": (15, 23, 42), "fg": (255, 255, 255)},
        }
        st_info = store_styles.get(store_name, {"name": store_name.upper(), "bg": (15, 23, 42), "fg": (255, 255, 255)})
        tag_text = f"{st_info['name']}  •  @flasfirsat.tr"
        t_w = draw.textlength(tag_text, font=f_label)
        sx1 = int(card_box[2] - t_w - 40)
        draw.rounded_rectangle((sx1, card_box[3] - 48, card_box[2] - 16, card_box[3] - 14), radius=9, fill=st_info["bg"])
        draw.text(((sx1 + card_box[2] - 16) // 2, card_box[3] - 31), tag_text, font=f_label, fill=st_info["fg"], anchor="mm")

        # Kart İçi Dinamik Taksit Rozeti (Sol Alt Köşe)
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip() if installment else "Peşin Fiyatına 3 Taksit"
        it_w = draw.textlength(clean_inst, font=f_label)
        ix2 = int(card_box[0] + 44 + it_w)
        draw.rounded_rectangle((card_box[0] + 16, card_box[3] - 48, ix2, card_box[3] - 14), radius=9, fill=theme["inst_bg"], outline=(16, 185, 129), width=1)
        draw.text(((card_box[0] + 16 + ix2) // 2, card_box[3] - 31), clean_inst, font=f_label, fill=theme["inst_fg"], anchor="mm")

    # 5. DÜRÜST FİYAT MİMARİSİ: Doğrulanmış Eski Fiyat Varsa İki Kutu, Yoksa Tek Büyük Hero Kutu
    old_val = parse_price_to_float(old_price) if (old_price and str(old_price).strip()) else 0
    new_val = parse_price_to_float(new_price)
    show_old_price = bool(has_verified_old_price and old_val >= (new_val * 1.08))
    savings = (old_val - new_val) if (show_old_price and old_val > new_val) else 0

    sub_parts = []
    clean_coupon = re.sub(r'[^\w\s.,xX+\-/%]', '', str(coupon_text)).strip() if coupon_text else ""
    if clean_coupon:
        sub_parts.append("🎟️ Sayfadaki Kuponu Aktif Et")
    if installment:
        clean_inst_s = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()
        sub_parts.append(clean_inst_s)
    elif savings > 0 and not clean_coupon:
        sav_fmt = f"{int(savings):,} TL".replace(',', '.')
        sub_parts.append(f"Net Tasarruf: {sav_fmt}")
    sub_str = "  •  ".join(sub_parts) if sub_parts else ""
    new_str = new_price if new_price else "Fırsat Fiyatı"

    def _draw_coupon_or_savings_pill(center_x: int):
        if clean_coupon:
            up_c = clean_coupon.upper()
            c_clean = up_c if up_c.startswith("KUPON") else f"KUPON: {up_c}"
            if len(c_clean) > 32:
                c_clean = c_clean[:32].strip()
            c_w = draw.textlength(c_clean, font=f_savings)
            pill_w = int(c_w + 48)
            pill_x1 = center_x - pill_w // 2
            pill_y1, pill_y2 = 716, 750
            draw.rounded_rectangle((pill_x1, pill_y1, pill_x1 + pill_w, pill_y2), radius=12, fill=theme["savings_pill_bg"])
            draw.text((center_x, (pill_y1 + pill_y2) // 2), c_clean, font=f_savings, fill=theme["savings_pill_fg"], anchor="mm")
        elif savings > 0 and not (feature_text and len(feature_text.strip()) > 3):
            sav_str = f"{int(savings):,} TL".replace(',', '.')
            sav_text = f"{sav_str} NET TASARRUF"
            s_w = draw.textlength(sav_text, font=f_savings)
            pill_w = int(s_w + 54)
            pill_x1 = center_x - pill_w // 2
            pill_y1, pill_y2 = 716, 750
            draw.rounded_rectangle((pill_x1, pill_y1, pill_x1 + pill_w, pill_y2), radius=12, fill=theme["savings_pill_bg"])
            draw.text((center_x, (pill_y1 + pill_y2) // 2), sav_text, font=f_savings, fill=theme["savings_pill_fg"], anchor="mm")

    if show_old_price:
        # Sol Kutu: Piyasa Fiyatı (Safe Zone: x=54..)
        old_box = (54, 750, 328, 888)
        draw.rounded_rectangle(old_box, radius=20, fill=theme["old_box_bg"], outline=theme["old_box_border"], width=2)
        ocx = (old_box[0] + old_box[2]) // 2
        draw.text((ocx, 774), "PİYASA FİYATI", font=f_old_lbl, fill=theme["old_text_col"], anchor="mm")

        op_w = draw.textlength(old_price, font=f_old_price)
        draw.text((ocx, 828), old_price, font=f_old_price, fill=theme["old_text_col"], anchor="mm")
        draw.line((ocx - op_w // 2 - 8, 828, ocx + op_w // 2 + 8, 828), fill=(239, 68, 68), width=2)

        # Orta Ok Kutusu
        arrow_box = (340, 800, 382, 842)
        draw.rounded_rectangle(arrow_box, radius=10, fill=theme["arrow_bg"], outline=theme["old_box_border"], width=1)
        acx, acy = 361, 821
        draw.line((acx - 4, acy - 8, acx + 4, acy), fill=theme["arrow_fg"], width=3)
        draw.line((acx + 4, acy, acx - 4, acy + 8), fill=theme["arrow_fg"], width=3)

        # Sağ Kutu: İndirimli Fırsat Fiyatı (Safe Zone: ..W-54)
        new_box = (394, 750, W - 54, 888)
        draw.rounded_rectangle(new_box, radius=20, fill=theme["new_box_bg"], outline=theme["new_box_border"], width=3)
        box_center_x = (new_box[0] + new_box[2]) // 2

        lbl_text = "KUPONLU FIRSAT FİYATI" if clean_coupon else "İNDİRİMLİ FIRSAT FİYATI"
        draw.text((box_center_x, 770), lbl_text, font=f_new_label, fill=theme["new_label_col"], anchor="mm")

        price_cy = 818 if sub_str else 828
        draw.text((box_center_x, price_cy), new_str, font=f_new_price, fill=theme["new_price_col"], anchor="mm")

        if sub_str:
            draw.text((box_center_x, 864), sub_str, font=f_net, fill=theme["new_label_col"], anchor="mm")

        # Floating Kupon / Net Tasarruf Rozeti
        _draw_coupon_or_savings_pill(box_center_x)

    else:
        # Tek Büyük ve Geniş Hero Kutu (Tam Ortalanmış - Safe Zone: 54..W-54)
        new_box = (54, 750, W - 54, 888)
        draw.rounded_rectangle(new_box, radius=20, fill=theme["new_box_bg"], outline=theme["new_box_border"], width=3)
        box_center_x = (new_box[0] + new_box[2]) // 2

        lbl_single = "KUPONLU FIRSAT FİYATI" if clean_coupon else "GÜNÜN ÖNE ÇIKAN SATIŞ FİYATI"
        draw.text((box_center_x, 770), lbl_single, font=f_new_label, fill=theme["new_label_col"], anchor="mm")

        price_cy = 818 if sub_str else 828
        draw.text((box_center_x, price_cy), new_str, font=f_new_price, fill=theme["new_price_col"], anchor="mm")

        if sub_str:
            draw.text((box_center_x, 864), sub_str, font=f_net, fill=theme["new_label_col"], anchor="mm")

        _draw_coupon_or_savings_pill(box_center_x)

    # 7. Etkileşim & Anti-Spam DM / BİO CTA Bandı (Platforma Özel: Instagram vs YouTube) + #işbirliği
    cta_box = (0, 898, W, 960)
    draw.rectangle(cta_box, fill=theme["cta_bg"])
    draw.line((0, 898, W, 898), fill=theme["cta_line"], width=4)

    f_cta_bold = get_font("segoeuib", 24)
    cy_cta = 929

    if str(cta_type).strip().lower() == "youtube":
        cta_prefix = "İndirim linkine "
        cta_highlight = "BİO'DAN"
        cta_suffix = f" ulaşın • KOD: {deal_code}" if deal_code else " ulaşabilirsiniz!"

        p_w = draw.textlength(cta_prefix, font=f_cta_bold)
        h_w = draw.textlength(cta_highlight, font=f_cta_bold)
        s_w = draw.textlength(cta_suffix, font=f_cta_bold)

        pill_w = int(h_w + 26)
        total_cta_w = int(34 + p_w + 8 + pill_w + 10 + s_w + 34)
        start_x = (W - total_cta_w) // 2

        draw_vector_link(draw, start_x + 14, cy_cta, theme["cta_line"])
        text_x = int(start_x + 36)

        draw.text((text_x, cy_cta), cta_prefix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
        text_x += int(p_w + 6)

        draw.rounded_rectangle((text_x, 910, text_x + pill_w, 948), radius=8, fill=theme["cta_pill_bg"])
        draw.text((text_x + pill_w // 2, cy_cta), cta_highlight, font=f_cta_bold, fill=theme["cta_pill_fg"], anchor="mm")
        text_x += pill_w + 10

        draw.text((text_x, cy_cta), cta_suffix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
        text_x += int(s_w + 18)

        draw_vector_globe(draw, text_x, cy_cta, theme["cta_line"])
    else:
        cta_prefix = "Ürün linki "
        cta_highlight = "PROFİLDE & HİKAYEDE"
        cta_suffix = f" • KOD: {deal_code}" if deal_code else " • Fırsatı Kaçırma!"

        p_w = draw.textlength(cta_prefix, font=f_cta_bold)
        h_w = draw.textlength(cta_highlight, font=f_cta_bold)
        s_w = draw.textlength(cta_suffix, font=f_cta_bold)

        pill_w = int(h_w + 26)
        total_cta_w = int(34 + p_w + 8 + pill_w + 10 + s_w + 34)
        start_x = (W - total_cta_w) // 2 - 20

        draw_vector_link(draw, start_x + 14, cy_cta, theme["cta_line"])
        text_x = int(start_x + 36)

        draw.text((text_x, cy_cta), cta_prefix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
        text_x += int(p_w + 6)

        draw.rounded_rectangle((text_x, 910, text_x + pill_w, 948), radius=8, fill=theme["cta_pill_bg"])
        draw.text((text_x + pill_w // 2, cy_cta), cta_highlight, font=f_cta_bold, fill=theme["cta_pill_fg"], anchor="mm")
        text_x += pill_w + 10

        draw.text((text_x, cy_cta), cta_suffix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
        text_x += int(s_w + 18)

        draw_vector_dm_plane(draw, text_x, cy_cta, theme["cta_line"])

    # Yasal Uyum Etiketi (#işbirliği)
    draw.text((W - 20, 930), "#işbirliği #reklam", font=f_tiny, fill=(148, 163, 184), anchor="rm")

    img.convert("RGB").save(output_path, "PNG")
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
    chk_a = safe_run_subprocess(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
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

    # 5. Meme süresini al ve Anti-Hash Rastgele Milisaniye Kırpması Yap
    cmd_len = ["ffmpeg", "-i", bottom_meme_path]
    p = safe_run_subprocess(cmd_len, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    raw_duration = float(m.group(3)) + int(m.group(2))*60 if m else 10.0

    # Anti-Hash: Her renderda süreyi 0.15 - 0.40 saniye rastgele kırparak toplam kare sayısını (frame count) benzersiz yap
    rnd_trim = round(random.uniform(0.15, 0.40), 3)
    duration = max(3.5, round(raw_duration - rnd_trim, 3))

    print(f"[Montaj] Seçilen Meme: {os.path.basename(bottom_meme_path)} (Süre: {duration:.2f}s, Anti-Hash Kırpma: -{rnd_trim}s)")
    if use_external_audio:
        print(f"[Montaj] Seçilen Harici Ses: {os.path.basename(audio_path)}")

    is_image = top_source.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    scale_top = "scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA" if is_image else "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960"

    # İlk 1 Saniyede Dinamik Mikro Punch-in Zoom + Anti-Hash Özgünlük Kalkanı (İnsan gözü fark etmez, Instagram pHash algoritması her videoyu %100 yeni görür)
    rnd_bright = round(random.uniform(-0.012, 0.012), 4)
    rnd_sat = round(random.uniform(0.985, 1.025), 4)
    rnd_contrast = round(random.uniform(0.99, 1.015), 4)
    scale_bottom = (
        f"scale=w='1080*(1+0.05*max(0,1-t))':h='960*(1+0.05*max(0,1-t))':eval=frame,"
        f"crop=1080:960,"
        f"eq=brightness={rnd_bright}:saturation={rnd_sat}:contrast={rnd_contrast}"
    )

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

    # Ses mikseri filtrelerini oluştur (Anti-Hash için %0.5 mikro ses frekans/tempo tazelemesi)
    audio_parts = []
    mix_sources = []

    # Meme'in kendi sesi
    bg_vol = 0.35 if voice_path else round(random.uniform(0.98, 1.02), 3)
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

    import datetime as _dt
    iso_now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
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
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    res = safe_run_subprocess(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Montaj] Video başarıyla oluşturuldu (Redmi Note 11 Pro Metadata & Clean Header): {output_path}")
        return output_path
    else:
        print("[Montaj] Hata:", res.stderr[-500:])
        return None


def build_top3_split_screen_video(
    deals: list,
    meme_name: str = None,
    output_filename: str = "top3_deal_reel.mp4"
) -> str:
    """
    En yüksek puanlı 3 fırsatı tek bir 12 saniyelik Reels videosunda sırayla (1/3 -> 2/3 -> 3/3)
    üst yarıda gösteren, kaydetme rekoru kıran 'TOP 3 Fırsat Listesi' videosu üretir.
    """
    if not deals or len(deals) < 2:
        raise ValueError("Top 3 video için en az 2-3 fırsat gereklidir.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    top_deals = deals[:3]
    banner_paths = []
    for idx, d in enumerate(top_deals, 1):
        b_path = os.path.join(TEMP_DIR, f"top3_banner_{idx}.png")
        code_str = d.get("deal_code", "")
        badge_lbl = f"FIRSAT #{idx}/{len(top_deals)}" + (f" ({code_str})" if code_str else "")
        create_product_banner(
            title=d.get("title", "Fırsat Ürünü"),
            product_image_path=d.get("image_path", ""),
            old_price=d.get("old_price", ""),
            new_price=d.get("new_price", ""),
            discount_pct=d.get("discount_pct", "-30%"),
            badge_text=badge_lbl,
            store_name=d.get("store_name", "Amazon TR"),
            bank_campaign=d.get("bank_campaign", ""),
            net_cost=d.get("net_cost", ""),
            installment=d.get("installment", ""),
            feature_text=d.get("killer_hook") or d.get("feature_pill", ""),
            is_lowest_30d=d.get("is_lowest_30d", False),
            has_verified_old_price=d.get("has_verified_old_price", True),
            seller_badge_text=d.get("seller_badge", "AMAZON TR"),
            coupon_text=d.get("coupon_info", ""),
            output_path=b_path
        )
        banner_paths.append(b_path)

    if meme_name:
        if not meme_name.endswith(".mp4"):
            meme_name += ".mp4"
        bottom_meme_path = os.path.join(MEMES_DIR, meme_name)
    else:
        chosen = select_smart_meme("-40%", top_deals[0].get("title", ""))
        bottom_meme_path = os.path.join(MEMES_DIR, chosen)

    reaction_text = "FİYATI ÇÖKEN BU 3 FIRSATI KAYDEDEN TAYFA:"
    reaction_overlay_path = os.path.join(TEMP_DIR, "reaction_top3_overlay.png")
    create_reaction_hook_overlay(reaction_text, reaction_overlay_path)

    raw_dur = get_media_duration(bottom_meme_path)
    rnd_trim = round(random.uniform(0.15, 0.40), 3)
    duration = round(max(9.6, min(raw_dur - rnd_trim, 12.6)), 3)
    seg_dur = round(duration / len(banner_paths), 3)

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    rnd_sat = round(random.uniform(1.01, 1.03), 3)
    rnd_contrast = round(random.uniform(1.005, 1.015), 3)

    import datetime as _dt
    iso_now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Input 0, 1, 2: banners; Input 3: meme; Input 4: reaction overlay
    cmd = ["ffmpeg", "-y"]
    for bp in banner_paths:
        cmd += ["-loop", "1", "-t", str(duration), "-i", bp]
    cmd += ["-i", bottom_meme_path]
    cmd += ["-loop", "1", "-t", str(duration), "-i", reaction_overlay_path]

    n_b = len(banner_paths)
    meme_idx = n_b
    ovl_idx = n_b + 1

    # Build top sequence via overlay enable=between(t,...)
    top_chain = "[0:v]scale=1080:960,setsar=1[t0];"
    for i in range(1, n_b):
        start_t = round(i * seg_dur, 2)
        end_t = round((i + 1) * seg_dur + 0.5, 2)
        top_chain += f"[{i}:v]scale=1080:960,setsar=1[b{i}];[t{i-1}][b{i}]overlay=0:0:enable='between(t,{start_t},{end_t})'[t{i}];"
    top_final = f"[t{n_b-1}]"

    scale_bottom = (
        f"scale=1080:960:force_original_aspect_ratio=increase,"
        f"crop=1080:960,setsar=1,"
        f"eq=saturation={rnd_sat}:contrast={rnd_contrast}"
    )
    progress_bar_filter = (
        f"[stacked]drawbox=x=0:y=1906:w=1080:h=14:color=black@0.5:t=fill,"
        f"drawbox=x=0:y=1906:w='1080*(t/{duration:.2f})':h=14:color=#FF5722@0.95:t=fill,"
        f"drawbox=x=0:y=1906:w='1080*(t/{duration:.2f})':h=4:color=#FACC15@1.0:t=fill[v]"
    )

    filter_complex = (
        f"{top_chain}"
        f"[{meme_idx}:v]{scale_bottom}[bottom_raw];"
        f"[bottom_raw][{ovl_idx}:v]overlay=0:0[bottom];"
        f"{top_final}[bottom]vstack=inputs=2[stacked];"
        f"{progress_bar_filter};"
        f"[{meme_idx}:a]volume=1.0[a]"
    )

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
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
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    res = safe_run_subprocess(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Montaj] 🏆 TOP 3 Liste Videosu oluşturuldu (Redmi Note 11 Pro Metadata): {output_path}")
        return output_path
    else:
        print("[Montaj] Top 3 Video Hatası:", res.stderr[-500:])
        return None

