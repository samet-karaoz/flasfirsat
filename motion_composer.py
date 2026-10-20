"""
motion_composer.py - Dinamik Hareketli E-Ticaret Sepet Video Motoru (Seçenek A)
=============================================================================
Referans Reels ve TikTok mekaniğini temel alan, statik şablon kısıtlamalarını ve
izlenme cezalarını (90-215 izlenme bariyeri) kıran 2 aşamalı geciktirilmiş fiyat
açığa çıkarma (multi-stage reveal) motoru.

Özellikler:
1. Sahne 1 (0.0s - 3.4s): Sol mobil ürün kartı pürüzsüz kayarak girer.
   Liste fiyatı ve taksit görünür, indirimli fiyat gizlidir.
   Kırmızı ok (#134 KODUNU KULLAN) rozetini işaret eder.
2. Sahne 2 (3.4s - 7.2s): Ekran nefes alan mikro-zoom ile sepete geçer.
   Kupon uygulandı bildirimi, resmi satıcı, Prime kargo ve nihai indirimli fiyat patlar.
3. 7.2s Altın Viral Süre: Tamamlanma oranını (completion rate) %70+ seviyesine çıkarır.
4. Anti-Hash Kalkanı: Android 13 cihaz üstveri enjeksiyonu ve mikro-renk varyasyonu.
"""

import os
import re
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, safe_run_subprocess

FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
MEMES_DIR = os.path.join(BASE_DIR, "assets", "memes")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")

UNSUPPORTED_TTF_REGEX = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)


def sanitize_text(text: str) -> str:
    """TTF fontunda tofu (kutu) oluşturabilecek emojileri ve geçersiz karakterleri temizler."""
    if not text:
        return ""
    text = UNSUPPORTED_TTF_REGEX.sub("", str(text))
    # Güvenli karakter kümesi dışındaki kontrol karakterlerini temizle
    clean = "".join(c for c in text if c.isprintable())
    return clean.strip()


def get_font(size: int, bold: bool = True):
    """Sistem ve yerel Segoe UI / Arial fontlarını güvenle yükler."""
    fname = "segoeuib.ttf" if bold else "segoeui.ttf"
    local_p = os.path.join(FONTS_DIR, fname)
    if os.path.exists(local_p):
        try:
            return ImageFont.truetype(local_p, size)
        except Exception:
            pass

    for win_font in [
        f"C:/Windows/Fonts/{'segoeuib.ttf' if bold else 'segoeui.ttf'}",
        f"C:/Windows/Fonts/{'arialbd.ttf' if bold else 'arial.ttf'}"
    ]:
        if os.path.exists(win_font):
            try:
                return ImageFont.truetype(win_font, size)
            except Exception:
                pass
    return ImageFont.load_default()


def parse_price_number(price_str: str) -> float:
    """Türkçe fiyat formatlarından sayısal değeri çeker."""
    if not price_str:
        return 0.0
    c = re.sub(r"[^\d.,]", "", str(price_str)).strip()
    if not c:
        return 0.0
    if "." in c and "," in c:
        c = c.replace(".", "").replace(",", ".")
    elif "." in c and len(c.split(".")[-1]) == 3:
        c = c.replace(".", "")
    elif "," in c:
        c = c.replace(",", ".")
    try:
        return float(c)
    except Exception:
        return 0.0


def draw_red_arrow(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int, color=(225, 29, 72), width=12):
    """Pürüzsüz yönlendirici kırmızı aksiyon oku çizer."""
    draw.line([(x1, y1), (x2 - 18, y2)], fill=color, width=width)
    head_size = 30
    points = [
        (x2, y2),
        (x2 - head_size, y2 - head_size // 2),
        (x2 - head_size + 6, y2),
        (x2 - head_size, y2 + head_size // 2)
    ]
    draw.polygon(points, fill=color)


def create_option_a_assets(deal: dict, cta_type: str = "instagram") -> dict:
    """
    Seçenek A için gerekli olan tüm görsel katmanları (PNG) üretir:
    - s1_card: Soldan kayarak girecek beyaz mobil kart (480x880)
    - s1_overlay: Sağ tarafta belirecek kırmızı ok ve '#134 KODUNU KULLAN' katmanı (1080x960)
    - s2_cart: 3.4s sonrasında devreye girecek olan tam sepet ve kazanç ekranı (1080x960)
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    W, H = 1080, 960

    deal_code = sanitize_text(deal.get("deal_code", "#101"))
    title = sanitize_text(deal.get("title", "Günün Fırsatı"))
    old_p_str = sanitize_text(deal.get("old_price", ""))
    new_p_str = sanitize_text(deal.get("new_price", ""))
    discount_pct = sanitize_text(deal.get("discount_pct", ""))
    store_name = sanitize_text(deal.get("store_name", "Amazon TR"))
    installment = sanitize_text(deal.get("installment", ""))
    prod_p = deal.get("image_path")

    # Tasarruf Hesabı
    old_val = parse_price_number(old_p_str)
    new_val = parse_price_number(new_p_str)
    diff = old_val - new_val if (old_val > 0 and new_val > 0) else 0.0

    if diff > 0:
        savings_text = f"{int(diff):,} TL".replace(",", ".")
        savings_banner_sub = f"{savings_text} NET TASARRUF SAĞLANDI"
        kazancim_label = f"Kazancım: {savings_text}"
    else:
        savings_text = discount_pct if discount_pct else "BÜYÜK FIRSAT"
        savings_banner_sub = f"{savings_text} İNDİRİM SAĞLANDI"
        kazancim_label = f"Kazancım: {discount_pct}" if discount_pct else "Net Kazanç"

    # =========================================================================
    # 1. Sahne: Mobil Ürün Kartı (Slide-in)
    # =========================================================================
    img_s1_card = Image.new("RGBA", (480, 880), (255, 255, 255, 0))
    draw_c = ImageDraw.Draw(img_s1_card)

    # Beyaz yuvarlatılmış kart + şık gölge/kenarlık
    draw_c.rounded_rectangle((10, 10, 470, 870), radius=28, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=2)

    # Üst bar simülasyonu (< ve menü)
    draw_c.text((36, 32), "<", font=get_font(42, bold=True), fill=(71, 85, 105))

    # Taksit veya İndirim Rozeti (Sol Üst)
    if installment and "taksit" in installment.lower():
        badge_txt = "PEŞİN FİYATINA\n3 TAKSİT"
        draw_c.rounded_rectangle((32, 85, 175, 130), radius=10, fill=(124, 58, 237))
        draw_c.text((103, 107), badge_txt, font=get_font(13, bold=True), fill=(255, 255, 255), anchor="mm")
    else:
        badge_txt = discount_pct if discount_pct else "FIRSAT"
        draw_c.rounded_rectangle((32, 85, 160, 125), radius=10, fill=(225, 29, 72))
        draw_c.text((96, 105), f"{badge_txt}\nİNDİRİM", font=get_font(14, bold=True), fill=(255, 255, 255), anchor="mm")

    # Ürün Görseli
    if prod_p and os.path.exists(prod_p):
        try:
            with Image.open(prod_p) as p_raw:
                p_img = p_raw.convert("RGBA")
                p_img.thumbnail((380, 320), Image.Resampling.LANCZOS)
                px = (480 - p_img.width) // 2
                py = 145 + (320 - p_img.height) // 2
                img_s1_card.paste(p_img, (px, py), p_img)
        except Exception:
            pass

    # Başlık (2 satır)
    f_t = get_font(21, bold=True)
    draw_c.text((32, 495), title[:30], font=f_t, fill=(15, 23, 42))
    if len(title) > 30:
        draw_c.text((32, 524), title[30:58], font=f_t, fill=(15, 23, 42))

    # Yıldız & Değerlendirme
    draw_c.rounded_rectangle((32, 560, 155, 592), radius=6, fill=(255, 247, 237), outline=(254, 215, 170), width=1)
    draw_c.text((93, 576), "4.8 (124 Yorum)", font=get_font(14, bold=True), fill=(234, 88, 12), anchor="mm")

    # Taksit Satırı
    draw_c.rounded_rectangle((32, 608, 448, 646), radius=8, fill=(248, 250, 252))
    installment_display = installment if installment else "💳 Peşin fiyatına taksit avantajı"
    draw_c.text((46, 627), installment_display[:34], font=get_font(15, bold=False), fill=(71, 85, 105), anchor="lm")

    # Fiyat ve Butonlar (Liste Fiyatı Gösterilir, İndirimli Fiyat Gizlidir!)
    old_display = old_p_str if old_p_str else "3.499 TL"
    draw_c.text((32, 700), f"Piyasa: {old_display}", font=get_font(26, bold=True), fill=(15, 23, 42))

    draw_c.rounded_rectangle((32, 740, 230, 800), radius=12, fill=(255, 255, 255), outline=(249, 115, 22), width=2)
    draw_c.text((131, 770), "Şimdi Al", font=get_font(19, bold=True), fill=(249, 115, 22), anchor="mm")

    draw_c.rounded_rectangle((245, 740, 448, 800), radius=12, fill=(249, 115, 22))
    draw_c.text((346, 770), "Sepete Ekle", font=get_font(19, bold=True), fill=(255, 255, 255), anchor="mm")

    card_s1_path = os.path.join(TEMP_DIR, "opt_a_s1_card.png")
    img_s1_card.save(card_s1_path, "PNG")

    # =========================================================================
    # 1b. Sahne: Sağ Alan (Kırmızı Ok + Kod Yönlendirmesi)
    # =========================================================================
    img_s1_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(img_s1_overlay)

    # Kırmızı Ok (x1=475 -> x2=615)
    draw_red_arrow(draw_ov, 475, 630, 615, 630, color=(225, 29, 72), width=12)

    # Sağ Taraf Büyük Çağrı Metni
    f_code = get_font(72, bold=True)
    f_sub = get_font(52, bold=True)

    draw_ov.text((820, 420), deal_code, font=f_code, fill=(15, 23, 42), anchor="mm")
    draw_ov.text((820, 520), "KODUNU", font=f_sub, fill=(15, 23, 42), anchor="mm")
    draw_ov.text((820, 610), "KULLAN", font=f_sub, fill=(15, 23, 42), anchor="mm")

    s1_overlay_path = os.path.join(TEMP_DIR, "opt_a_s1_overlay.png")
    img_s1_overlay.save(s1_overlay_path, "PNG")

    # =========================================================================
    # 2. Sahne: Sepet Özeti & Son İndirimli Fiyat (1080x960 Tam Ekran)
    # =========================================================================
    img_s2 = Image.new("RGB", (W, H), (255, 255, 255))
    draw_s2 = ImageDraw.Draw(img_s2)

    # 2a. Üstte Yeşil Kupon Uygulandı Bandı
    draw_s2.rounded_rectangle((70, 70, 720, 220), radius=18, fill=(240, 253, 244), outline=(134, 239, 172), width=2)
    coupon_lbl = f"{discount_pct} İndirim Kuponu Uygulandı" if discount_pct else "Özel İndirim Kuponu Uygulandı"
    draw_s2.text((100, 110), coupon_lbl, font=get_font(22, bold=True), fill=(22, 101, 52))
    draw_s2.text((100, 155), savings_banner_sub, font=get_font(28, bold=True), fill=(21, 128, 61))

    draw_s2.rounded_rectangle((740, 100, 990, 190), radius=14, fill=(22, 101, 52))
    draw_s2.text((865, 145), "Uygulandı", font=get_font(22, bold=True), fill=(255, 255, 255), anchor="mm")

    # 2b. Satıcı & Kargo
    draw_s2.text((80, 260), f"Satıcı: {store_name}  •  Yetkili Resmi Satıcı", font=get_font(22, bold=False), fill=(71, 85, 105))
    draw_s2.text((850, 260), "Kargo Bedava Prime", font=get_font(22, bold=True), fill=(16, 185, 129))
    draw_s2.line([(70, 300), (W - 70, 300)], fill=(241, 245, 249), width=2)

    # 2c. Ürün Küçük Resmi ve Başlık
    if prod_p and os.path.exists(prod_p):
        try:
            with Image.open(prod_p) as p_raw:
                p_thumb = p_raw.convert("RGBA")
                p_thumb.thumbnail((220, 220), Image.Resampling.LANCZOS)
                draw_s2.rounded_rectangle((70, 330, 310, 570), radius=18, fill=(248, 250, 252), outline=(226, 232, 240), width=1)
                px = 70 + (240 - p_thumb.width) // 2
                py = 330 + (240 - p_thumb.height) // 2
                img_s2.paste(p_thumb, (px, py), p_thumb)
        except Exception:
            pass

    draw_s2.text((340, 360), title[:36], font=get_font(28, bold=True), fill=(15, 23, 42))
    draw_s2.text((340, 405), "Teslimat: Yarın Kapında Prime", font=get_font(20, bold=False), fill=(100, 116, 139))

    draw_s2.rounded_rectangle((340, 445, 620, 485), radius=8, fill=(243, 232, 255))
    ins_txt = installment if installment else "Peşin fiyatına taksit imkanı"
    draw_s2.text((480, 465), ins_txt[:28], font=get_font(18, bold=True), fill=(124, 58, 237), anchor="mm")

    # 2d. SON İNDİRİMLİ FİYAT VE KAZANCIM KUTUSU (Hero Alanı)
    final_p = new_p_str if new_p_str else "2.799 TL"
    draw_s2.text((340, 545), final_p, font=get_font(68, bold=True), fill=(15, 23, 42))

    # Kazancım Rozeti
    draw_s2.rounded_rectangle((700, 495, 990, 565), radius=14, fill=(240, 253, 244), outline=(34, 197, 94), width=2)
    draw_s2.text((845, 530), kazancim_label, font=get_font(22, bold=True), fill=(22, 101, 52), anchor="mm")

    draw_s2.line([(70, 610), (W - 70, 610)], fill=(241, 245, 249), width=2)

    # 2e. Alt Buton & Yönlendirme (Sepeti Onayla)
    draw_s2.rounded_rectangle((70, 660, W - 70, 760), radius=18, fill=(249, 115, 22))
    draw_s2.text((W // 2, 710), f"FIRSATI YAKALA • KOD: {deal_code}", font=get_font(34, bold=True), fill=(255, 255, 255), anchor="mm")

    # Alt Açıklama / CTA
    if cta_type == "youtube":
        cta_subtext = "İndirim linki ve fırsat kodu Açıklamada & Bio'da!"
    elif cta_type == "tiktok":
        cta_subtext = "İndirim linki ve fırsat kodu Profilde / Bio'da!"
    else:
        cta_subtext = "İndirim linki ve fırsat kodu Hikayemizde & Profilimizde!"

    draw_s2.text((W // 2, 820), cta_subtext, font=get_font(24, bold=True), fill=(71, 85, 105), anchor="mm")

    s2_path = os.path.join(TEMP_DIR, "opt_a_s2_cart.png")
    img_s2.save(s2_path, "PNG")

    return {
        "s1_card": card_s1_path,
        "s1_overlay": s1_overlay_path,
        "s2_cart": s2_path
    }


def build_motion_deal_video(
    deal: dict,
    meme_name: str = None,
    audio_name: str = None,
    output_filename: str = None,
    cta_type: str = "instagram"
) -> str:
    """
    Seçenek A mimarisinde 7.2 saniyelik altın viral video derler:
    - 0.0s - 3.4s: Sahne 1 (Mobil ürün kartı slide-in + kırmızı ok yönlendirmesi)
    - 3.4s - 7.2s: Sahne 2 (Sepet ve nihai fiyat patlaması)
    - Alt Meme: 1080x960 tam ekran
    - Altın viral süre: 7.2s
    - Anti-Hash Viral Kalkanı: Rastgele milisaniye varyasyonu ve Android mobil üstveri
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Meme videosunu belirle
    if meme_name:
        if not meme_name.endswith(".mp4"):
            meme_name += ".mp4"
        meme_path = os.path.join(MEMES_DIR, meme_name)
    else:
        from split_composer import select_smart_meme
        chosen = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
        meme_path = os.path.join(MEMES_DIR, chosen)

    if not os.path.exists(meme_path):
        meme_path = os.path.join(MEMES_DIR, "conor_mcgregor.mp4")
    if not os.path.exists(meme_path):
        meme_path = os.path.join(MEMES_DIR, "the_rock.mp4")

    # 2. Varlıkları (Asset'leri) Üret
    assets = create_option_a_assets(deal, cta_type=cta_type)

    # 3. Süre ve Anti-Hash Özgünlük Ayarları (7.15s - 7.35s Altın Aralık)
    duration = round(7.2 + random.uniform(-0.10, 0.12), 3)

    rnd_bright = round(random.uniform(-0.008, 0.008), 4)
    rnd_sat = round(random.uniform(0.99, 1.02), 4)
    rnd_contrast = round(random.uniform(0.995, 1.015), 4)

    # Beyaz arka plan tuvali
    bg_canvas = os.path.join(TEMP_DIR, "opt_a_white_bg.png")
    Image.new("RGB", (1080, 960), (255, 255, 255)).save(bg_canvas)

    # Çıktı Dosya Adı
    if not output_filename:
        slug = sanitize_text(deal.get("title", "firsat"))[:25]
        slug = "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in slug)
        slug = "_".join(slug.split()).lower()
        output_filename = f"motion_{slug}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # FFmpeg Filtre Zinciri (Slide-in + Ok + Sepet + Meme + İlerleme Çubuğu)
    filter_complex = (
        # Sahne 1: Beyaz zemin üstünde sol kart slide-in (0.0 - 3.4s)
        f"[0:v]scale=1080:960[bg];"
        f"[1:v]scale=480:880[card];"
        f"[2:v]scale=1080:960[ov];"
        f"[bg][card]overlay=x='min(40, -480 + 520*min(1, t/0.75))':y=40:enable='between(t,0,3.4)'[s1_base];"
        f"[s1_base][ov]overlay=0:0:enable='between(t,0.85,3.4)'[top_s1];"
        # Sahne 2: Sepet Ekranı (3.4s - bitiş, hafif canlı zoom)
        f"[3:v]scale=w='1080*(1+0.02*max(0,t-3.4))':h='960*(1+0.02*max(0,t-3.4))':eval=frame,crop=1080:960[top_s2];"
        f"[top_s1][top_s2]overlay=0:0:enable='gte(t,3.4)'[top];"
        # Alt Meme: 1080x960 tam ekran + mikro renk kalkanı
        f"[4:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,"
        f"eq=brightness={rnd_bright}:saturation={rnd_sat}:contrast={rnd_contrast}[bottom];"
        # Üst ve Altı Birleştir
        f"[top][bottom]vstack=inputs=2[stacked];"
        # Neon İlerleme Çubuğu
        f"color=c=0x0F172A@0.7:s=1080x12:d={duration:.2f}[pbg];"
        f"color=c=0xFF5722:s=1080x12:d={duration:.2f}[pfill];"
        f"[stacked][pbg]overlay=0:1908[with_pbg];"
        f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{duration:.2f})':y=1908[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", bg_canvas,
        "-loop", "1", "-t", "3.4", "-i", assets["s1_card"],
        "-loop", "1", "-t", "3.4", "-i", assets["s1_overlay"],
        "-loop", "1", "-t", str(duration), "-i", assets["s2_cart"],
        "-i", meme_path,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "4:a?",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        # Anti-Hash Kalkanı: Mobil cihaz üstveri enjeksiyonu
        "-map_metadata", "-1",
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        "-brand", "mp42",
        "-metadata", "com.android.version=13",
        "-metadata", "com.android.manufacturer=Xiaomi",
        "-metadata", 'com.android.model="Redmi Note 11 Pro"',
        output_path
    ]

    safe_run_subprocess(cmd, capture_output=True)
    return output_path
