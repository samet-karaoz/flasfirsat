import os
import subprocess
import random
import re
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR

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
    "shark_nemo.mp4"
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

def wrap_text(text: str, max_chars_per_line: int = 32) -> list:
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

def select_smart_meme(discount_pct: str = "", title: str = "", category: str = "") -> str:
    """
    İndirim oranına, ürün kategorisine ve başlığına göre en yüksek viral potansiyele sahip
    meme videosunu kütüphaneden akıllıca seçer.
    """
    available = [m for m in AVAILABLE_MEMES if os.path.exists(os.path.join(MEMES_DIR, m))]
    if not available:
        available = [f for f in os.listdir(MEMES_DIR) if f.endswith(".mp4")]
    if not available:
        return "knight_cat.mp4"

    # İndirim yüzdesini sayıya çevir
    pct_match = re.search(r'(\d+)', str(discount_pct))
    pct_val = int(pct_match.group(1)) if pct_match else 30
    title_low = (title or "").lower()

    # 1. Dev Çöküş İndirimleri (%40 ve üzeri) - Şok ve Zenginlik Memeleri
    if pct_val >= 40:
        candidates = ["vince_mcmahon.mp4", "walter_white.mp4", "the_rock.mp4", "homelander_stare.mp4"]
        valid = [c for c in candidates if c in available]
        if valid:
            return random.choice(valid)

    # 2. Gaming, Espor ve Donanım Ürünleri - Karizmatik Sigma / Oyuncu Tepkileri
    gaming_kw = ["mouse", "kulaklık", "klavye", "gaming", "ps5", "gamepad", "espor", "oyuncu", "monitor", "ekran kartı"]
    if any(k in title_low for k in gaming_kw):
        candidates = ["bateman_walk.mp4", "bale_nod.mp4", "ryan_gosling.mp4", "bully_maguire.mp4", "the_rock.mp4"]
        valid = [c for c in candidates if c in available]
        if valid:
            return random.choice(valid)

    # 3. Yüksek Fırsat / Viral Hit (%25 - %39) - Zafer ve Kutlama
    if pct_val >= 25:
        candidates = ["dicaprio_cheers.mp4", "mcconaughey_chest.mp4", "bully_maguire.mp4", "bale_nod.mp4", "bateman_walk.mp4"]
        valid = [c for c in candidates if c in available]
        if valid:
            return random.choice(valid)

    # 4. Genel Ürünler
    candidates = ["the_weeknd_lost.mp4", "kanye_stare.mp4", "the_rock.mp4", "dicaprio_cheers.mp4", "walter_white.mp4"]
    valid = [c for c in candidates if c in available]
    return random.choice(valid) if valid else random.choice(available)

def create_product_banner(
    product_image_path: str,
    title: str,
    old_price: str,
    new_price: str,
    discount_pct: str = "-35%",
    badge_text: str = "FLAŞ FIRSAT",
    store_name: str = "Amazon TR",
    bank_campaign: str = "",
    net_cost: str = "",
    installment: str = "",
    output_path: str = None
) -> str:
    """
    Ürün görseli ve fiyat bilgilerinden 1080x960 ebatlarında
    profesyonel e-ticaret sayfaları kalitesinde, etiketli ve dinamik afiş üretir.
    Amazon TR, Trendyol ve Hepsiburada marka renklerini yansıtır.
    Taksit avantajı ve net maliyeti öne çıkarır.
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "product_top.png")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    W, H = 1080, 960
    img = Image.new("RGB", (W, H), (244, 246, 250))
    draw = ImageDraw.Draw(img)

    has_extra_info = bool(net_cost or installment)

    f_badge = get_font("segoeuib", 26)
    f_title = get_font("segoeuib", 40)
    f_label = get_font("segoeuib", 22)
    f_old_price = get_font("segoeuib", 40)
    f_new_label = get_font("segoeuib", 22 if has_extra_info else 24)
    f_new_price = get_font("segoeuib", 56 if has_extra_info else 68)
    f_net = get_font("segoeuib", 21)
    f_pct = get_font("segoeuib", 28)

    # 1. Sol Üst Rozet (Badge) - FLAŞ FIRSAT
    clean_badge = badge_text.strip()
    b_w = draw.textlength(clean_badge, font=f_badge)
    draw.rounded_rectangle((40, 24, 40 + b_w + 58, 76), radius=14, fill=(255, 87, 34)) # Alev Turuncusu #FF5722
    # Altın Sarısı Vektör Şimşek İkonu (#FFCC00)
    bolt_icon = [(63, 33), (51, 50), (60, 50), (54, 67), (71, 48), (62, 48)]
    draw.polygon(bolt_icon, fill=(255, 204, 0))
    draw.text((78, 36), clean_badge, font=f_badge, fill=(255, 255, 255))

    # 2. Sağ Üst İndirim Rozeti
    clean_pct = discount_pct.strip()
    if clean_pct and not clean_pct.endswith("İNDİRİM"):
        clean_pct = f"{clean_pct} İNDİRİM"
    p_w = draw.textlength(clean_pct, font=f_pct)
    draw.rounded_rectangle((W - 40 - p_w - 44, 24, W - 40, 76), radius=14, fill=(225, 29, 72)) # Canlı Kırmızı
    draw.text((W - 40 - p_w - 22, 35), clean_pct, font=f_pct, fill=(255, 255, 255))

    # 3. Ürün Başlığı (1 veya 2 satır)
    title_lines = wrap_text(title, max_chars_per_line=36)
    title_y = 94
    for line in title_lines:
        draw.text((40, title_y), line, font=f_title, fill=(15, 23, 42))
        title_y += 48

    # 4. Ürün Fotoğrafını Kart İçine Ekle (980px Genişlik)
    card_top = max(156, title_y + 10)
    card_bottom = 736
    card_box = (40, card_top, W - 40, card_bottom)
    draw.rounded_rectangle(card_box, radius=24, fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    if product_image_path and os.path.exists(product_image_path):
        try:
            p_img = Image.open(product_image_path).convert("RGBA")
            max_img_w = card_box[2] - card_box[0] - 60
            max_img_h = card_box[3] - card_box[1] - 50
            p_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2
            img.paste(p_img, (px, py), p_img)
        except Exception as e:
            print(f"[Banner] Görsel ekleme uyarısı: {e}")

    # Kart içi dinamik mağaza güven rozeti (Sağ Alt Köşe)
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

    # Kart içi dinamik Taksit Avantaj Rozeti (Sol Alt Köşe)
    if installment:
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()
        inst_label = f"Taksit: {clean_inst}" if "taksit" not in clean_inst.lower() else clean_inst
        it_w = draw.textlength(inst_label, font=f_label)
        draw.rounded_rectangle((card_box[0] + 16, card_box[3] - 46, card_box[0] + 16 + it_w + 24, card_box[3] - 14), radius=8, fill=(236, 253, 245), outline=(16, 185, 129), width=1)
        # Yeşil onay noktası
        draw.ellipse((card_box[0] + 24, card_box[3] - 33, card_box[0] + 32, card_box[3] - 25), fill=(5, 150, 105))
        draw.text((card_box[0] + 38, card_box[3] - 42), inst_label, font=f_label, fill=(4, 120, 87))

    # 5. Alt Fiyat Bölümü: Çift Kartlı Premium Tasarım
    # Sol Kart: Piyasa / Eski Fiyat
    old_box = (40, 756, 420, 924)
    draw.rounded_rectangle(old_box, radius=18, fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    old_lbl = "PİYASA FİYATI"
    ol_w = draw.textlength(old_lbl, font=f_label)
    draw.text((old_box[0] + (old_box[2] - old_box[0] - ol_w) // 2, 780), old_lbl, font=f_label, fill=(148, 163, 184))

    old_str = old_price if old_price else "Piyasa Fiyatı"
    op_w = draw.textlength(old_str, font=f_old_price)
    op_x = old_box[0] + (old_box[2] - old_box[0] - op_w) // 2
    draw.text((op_x, 825), old_str, font=f_old_price, fill=(100, 116, 139))
    # Üstü Çizili Kırmızı Çizgi
    draw.line((op_x - 6, 850, op_x + op_w + 6, 850), fill=(239, 68, 68), width=4)

    # Orta Geçiş İkonu (Chevron >)
    arrow_box = (436, 815, 484, 865)
    draw.rounded_rectangle(arrow_box, radius=12, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    cx, cy = 460, 840
    draw.line((cx - 5, cy - 10, cx + 5, cy), fill=(234, 88, 12), width=3)
    draw.line((cx + 5, cy, cx - 5, cy + 10), fill=(234, 88, 12), width=3)

    # Sağ Kart: İndirimli Yeni Fiyat (Öne Çıkarılmış Zümrüt Yeşili)
    new_box = (500, 756, W - 40, 924)
    draw.rounded_rectangle(new_box, radius=18, fill=(236, 253, 245), outline=(16, 185, 129), width=3)

    new_lbl = "İNDİRİMLİ FIRSAT FİYATI"
    nl_w = draw.textlength(new_lbl, font=f_new_label)
    nl_x = new_box[0] + (new_box[2] - new_box[0] - nl_w) // 2
    draw.ellipse((nl_x - 18, 778 if has_extra_info else 788, nl_x - 8, 788 if has_extra_info else 798), fill=(5, 150, 105))
    draw.text((nl_x, 770 if has_extra_info else 780), new_lbl, font=f_new_label, fill=(4, 120, 87))

    new_str = new_price if new_price else "Fırsat Fiyatı"
    np_w = draw.textlength(new_str, font=f_new_price)
    np_x = new_box[0] + (new_box[2] - new_box[0] - np_w) // 2
    draw.text((np_x, 802 if has_extra_info else 820), new_str, font=f_new_price, fill=(5, 150, 105))

    # Banka Kampanyası & Net Maliyet & Taksit Çizgisi
    clean_net = re.sub(r'[^\w\s.,xX+\-/%]', '', net_cost).strip()
    clean_camp = re.sub(r'[^\w\s.,xX+\-/%]', '', bank_campaign).strip()
    clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip()

    net_str = ""
    if clean_net and clean_inst:
        net_str = f"Net: {clean_net}  •  {clean_inst}"
    elif clean_net:
        net_str = f"Net: {clean_net} ({clean_camp})" if clean_camp else f"Net: {clean_net}"
    elif clean_inst:
        net_str = clean_inst

    if net_str:
        net_w = draw.textlength(net_str, font=f_net)
        net_x = new_box[0] + (new_box[2] - new_box[0] - net_w) // 2
        draw.text((net_x, 872), net_str, font=f_net, fill=(4, 120, 87))

    img.save(output_path, "PNG")
    return output_path

def build_split_screen_video(
    top_source: str,
    meme_name: str = None,
    audio_name: str = None,
    output_filename: str = "deal_reel.mp4",
    discount_pct: str = "",
    product_title: str = ""
) -> str:
    """
    Üst yarıda ürün banner'ı (1080x960),
    Alt yarıda viral meme videosu (1080x960),
    Arka planda viral phonk müziği veya meme'in orijinal sesi ile 1080x1920 MP4 video üretir.
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

    # 2. Ses kaynağını belirle (Öncelik: Meme'in kendi orijinal sesi)
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

    # 3. Meme süresini al
    cmd_len = ["ffmpeg", "-i", bottom_meme_path]
    p = subprocess.run(cmd_len, capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    duration = float(m.group(3)) + int(m.group(2))*60 if m else 10.0

    print(f"[Montaj] Seçilen Meme: {os.path.basename(bottom_meme_path)} (Süre: {duration:.1f}s)")
    if use_external_audio:
        print(f"[Montaj] Seçilen Harici Ses: {os.path.basename(audio_path)}")

    is_image = top_source.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))

    if not use_external_audio:
        # Meme'in kendi sesini doğrudan kullan
        if is_image:
            filter_complex = (
                f"[0:v]scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA[top];"
                f"[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
                f"[top][bottom]vstack=inputs=2[v];"
                f"[1:a]volume=1.0[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", top_source,
                "-i", bottom_meme_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                output_path
            ]
        else:
            filter_complex = (
                f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
                f"[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
                f"[top][bottom]vstack=inputs=2[v];"
                f"[1:a]volume=1.0[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", top_source,
                "-i", bottom_meme_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                output_path
            ]
    else:
        # Harici ses dosyasıyla birleştir
        if is_image:
            filter_complex = (
                f"[0:v]scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA[top];"
                f"[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
                f"[top][bottom]vstack=inputs=2[v];"
                f"[2:a]volume=1.0[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", top_source,
                "-i", bottom_meme_path,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                output_path
            ]
        else:
            filter_complex = (
                f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
                f"[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
                f"[top][bottom]vstack=inputs=2[v];"
                f"[2:a]volume=1.0[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", top_source,
                "-i", bottom_meme_path,
                "-i", audio_path,
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
