import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, safe_run_subprocess

FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

def get_font(size: int, bold: bool = True):
    fname = "segoeuib.ttf" if bold else "segoeui.ttf"
    p = os.path.join(FONTS_DIR, fname)
    if os.path.exists(p):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    for win_font in ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(win_font):
            try:
                return ImageFont.truetype(win_font, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_red_arrow(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int, color=(225, 29, 72), width=10):
    # Düz gövde çizgisi
    draw.line([(x1, y1), (x2 - 15, y2)], fill=color, width=width)
    # Ok ucu (üçgen)
    head_size = 28
    points = [
        (x2, y2),
        (x2 - head_size, y2 - head_size // 2),
        (x2 - head_size + 6, y2),
        (x2 - head_size, y2 + head_size // 2)
    ]
    draw.polygon(points, fill=color)

# =========================================================================
# SEÇENEK A: DOĞAL MOBİL UYGULAMA / SEPET EKRANI (REFERANS VİDEO BİREBİR)
# =========================================================================

def create_option_a_assets(deal: dict):
    os.makedirs(TEMP_DIR, exist_ok=True)
    W, H = 1080, 960

    # 1. Sahne: Sol Ürün Kartı (Slide-in) + Sağ Taraf Ok ve KODUNU KULLAN
    # Sol kart 470x860, Sağ alan 610x960
    img_s1_card = Image.new("RGBA", (480, 880), (255, 255, 255, 0))
    draw_c = ImageDraw.Draw(img_s1_card)

    # Beyaz yuvarlatılmış mobil kart + ince gri kenarlık
    draw_c.rounded_rectangle((10, 10, 470, 870), radius=28, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=2)

    # Üst bar: Sol ok (<), kalp ve paylaş ikonları simülasyonu
    draw_c.text((36, 32), "<", font=get_font(42, bold=True), fill=(71, 85, 105))
    draw_c.text((375, 36), "", font=get_font(28, bold=True), fill=(71, 85, 105))
    draw_c.text((420, 36), "", font=get_font(28, bold=True), fill=(71, 85, 105))

    # Taksit Rozeti (Sol Üst)
    draw_c.rounded_rectangle((32, 85, 160, 125), radius=10, fill=(124, 58, 237))
    draw_c.text((96, 105), "PEŞİN FİYATINA\n3 TAKSİT", font=get_font(13, bold=True), fill=(255, 255, 255), anchor="mm")

    # Ürün Görseli
    prod_p = deal.get("image_path")
    if prod_p and os.path.exists(prod_p):
        with Image.open(prod_p) as p_raw:
            p_img = p_raw.convert("RGBA")
            p_img.thumbnail((380, 320), Image.Resampling.LANCZOS)
            px = (480 - p_img.width) // 2
            py = 145 + (320 - p_img.height) // 2
            img_s1_card.paste(p_img, (px, py), p_img)

    # Başlık
    title = deal.get("title", "Mekanik Klavye")
    f_t = get_font(21, bold=True)
    draw_c.text((32, 495), title[:30], font=f_t, fill=(15, 23, 42))
    if len(title) > 30:
        draw_c.text((32, 524), title[30:58], font=f_t, fill=(15, 23, 42))

    # Yıldız & Değerlendirme
    draw_c.rounded_rectangle((32, 560, 130, 592), radius=6, fill=(255, 247, 237), outline=(254, 215, 170), width=1)
    draw_c.text((81, 576), "4.8 (124 Yorum)", font=get_font(14, bold=True), fill=(234, 88, 12), anchor="mm")

    # Taksit Satırı
    draw_c.rounded_rectangle((32, 608, 448, 646), radius=8, fill=(248, 250, 252))
    draw_c.text((46, 627), "💳 Peşin fiyatına 3 x 933 TL", font=get_font(15, bold=False), fill=(71, 85, 105), anchor="lm")

    # Fiyat ve Turuncu Sepete Ekle Butonu
    old_p = deal.get("old_price", "3.499 TL")
    draw_c.text((32, 700), f"Piyasa: {old_p}", font=get_font(26, bold=True), fill=(15, 23, 42))

    draw_c.rounded_rectangle((32, 740, 230, 800), radius=12, fill=(255, 255, 255), outline=(249, 115, 22), width=2)
    draw_c.text((131, 770), "Şimdi Al", font=get_font(19, bold=True), fill=(249, 115, 22), anchor="mm")

    draw_c.rounded_rectangle((245, 740, 448, 800), radius=12, fill=(249, 115, 22))
    draw_c.text((346, 770), "Sepete Ekle", font=get_font(19, bold=True), fill=(255, 255, 255), anchor="mm")

    card_s1_path = os.path.join(TEMP_DIR, "opt_a_s1_card.png")
    img_s1_card.save(card_s1_path, "PNG")

    # 1b. Sağ Taraf Ok ve Yazı Katmanı (Overlay)
    img_s1_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(img_s1_overlay)

    # Kırmızı Ok (x1=490, y1=630 -> x2=610, y2=630)
    draw_red_arrow(draw_ov, 475, 630, 615, 630, color=(225, 29, 72), width=12)

    # Sağ Taraf Büyük Yazı
    code_text = deal.get("deal_code", "#134")
    f_code = get_font(72, bold=True)
    f_sub = get_font(52, bold=True)

    draw_ov.text((820, 420), code_text, font=f_code, fill=(15, 23, 42), anchor="mm")
    draw_ov.text((820, 520), "KODUNU", font=f_sub, fill=(15, 23, 42), anchor="mm")
    draw_ov.text((820, 610), "KULLAN", font=f_sub, fill=(15, 23, 42), anchor="mm")

    s1_overlay_path = os.path.join(TEMP_DIR, "opt_a_s1_overlay.png")
    img_s1_overlay.save(s1_overlay_path, "PNG")

    # 2. Sahne: Sepet Özeti & Son İndirimli Fiyat (1080x960 Tam Ekran)
    img_s2 = Image.new("RGB", (W, H), (255, 255, 255))
    draw_s2 = ImageDraw.Draw(img_s2)

    # 2a. Üstte Yeşil Kupon Uygulandı Bandı
    draw_s2.rounded_rectangle((70, 70, 620, 220), radius=18, fill=(240, 253, 244), outline=(134, 239, 172), width=2)
    draw_s2.text((100, 110), f" {deal.get('discount_pct', '-%20')} İndirim Kuponu Uygulandı", font=get_font(22, bold=True), fill=(22, 101, 52))
    draw_s2.text((100, 155), "700 TL NET TASARRUF SAĞLANDI", font=get_font(28, bold=True), fill=(21, 128, 61))
    draw_s2.rounded_rectangle((480, 135, 595, 185), radius=10, fill=(255, 255, 255), outline=(22, 101, 52), width=1)
    draw_s2.text((537, 160), "Uygulandı ", font=get_font(16, bold=True), fill=(22, 101, 52), anchor="mm")

    # 2b. Satıcı & Kargo
    draw_s2.text((80, 260), "Satıcı: Amazon TR  •  Yetkili Resmi Satıcı", font=get_font(22, bold=False), fill=(71, 85, 105))
    draw_s2.text((850, 260), "Kargo Bedava ", font=get_font(22, bold=True), fill=(16, 185, 129))
    draw_s2.line([(70, 300), (W - 70, 300)], fill=(241, 245, 249), width=2)

    # 2c. Ürün Küçük Resmi ve Başlık
    if prod_p and os.path.exists(prod_p):
        with Image.open(prod_p) as p_raw:
            p_thumb = p_raw.convert("RGBA")
            p_thumb.thumbnail((220, 220), Image.Resampling.LANCZOS)
            draw_s2.rounded_rectangle((70, 330, 310, 570), radius=18, fill=(248, 250, 252), outline=(226, 232, 240), width=1)
            px = 70 + (240 - p_thumb.width) // 2
            py = 330 + (240 - p_thumb.height) // 2
            img_s2.paste(p_thumb, (px, py), p_thumb)

    draw_s2.text((340, 360), deal.get("title", "Mekanik Klavye")[:36], font=get_font(28, bold=True), fill=(15, 23, 42))
    draw_s2.text((340, 405), "Teslimat: Yarın Kapında Prime", font=get_font(20, bold=False), fill=(100, 116, 139))
    draw_s2.rounded_rectangle((340, 445, 590, 485), radius=8, fill=(243, 232, 255))
    draw_s2.text((465, 465), "Peşin fiyatına 3 x 933 TL", font=get_font(18, bold=True), fill=(124, 58, 237), anchor="mm")

    # 2d. SON İNDİRİMLİ FİYAT VE KAZANCIM KUTUSU (Hero Alanı)
    new_p = deal.get("new_price", "2.799 TL")
    draw_s2.text((340, 545), new_p, font=get_font(68, bold=True), fill=(15, 23, 42))

    # Kazancım Rozeti
    draw_s2.rounded_rectangle((700, 495, 990, 565), radius=14, fill=(240, 253, 244), outline=(34, 197, 94), width=2)
    draw_s2.text((845, 530), "Kazancım: 700,00 TL ", font=get_font(22, bold=True), fill=(22, 101, 52), anchor="mm")

    draw_s2.line([(70, 610), (W - 70, 610)], fill=(241, 245, 249), width=2)

    # 2e. Alt Buton & Yönlendirme (Sepeti Onayla)
    draw_s2.rounded_rectangle((70, 660, W - 70, 760), radius=18, fill=(249, 115, 22))
    draw_s2.text((W // 2, 710), f"FIRSATI YAKALA • KOD: {deal.get('deal_code', '#134')}", font=get_font(34, bold=True), fill=(255, 255, 255), anchor="mm")

    draw_s2.text((W // 2, 820), " İndirim linki ve fırsat kodu Hikayemizde & Profilimizde!", font=get_font(24, bold=True), fill=(71, 85, 105), anchor="mm")

    s2_path = os.path.join(TEMP_DIR, "opt_a_s2_cart.png")
    img_s2.save(s2_path, "PNG")

    return {
        "s1_card": card_s1_path,
        "s1_overlay": s1_overlay_path,
        "s2_cart": s2_path
    }

# =========================================================================
# SEÇENEK B: STÜDYO SİNEMATİK / DİNAMİK KAMERA HAREKETLİ ŞABLON
# =========================================================================

def create_option_b_assets(deal: dict):
    os.makedirs(TEMP_DIR, exist_ok=True)
    W, H = 1080, 960

    # Koyu Obsidian Arka Plan
    bg_top = (11, 15, 25)
    bg_bot = (20, 28, 46)

    # 1. Sahne: Koyu Stüdyo Zemin + Soldan Gelen Stüdyo Kartı + Sağda Neon Kod
    img_s1_card = Image.new("RGBA", (500, 880), (0, 0, 0, 0))
    draw_c = ImageDraw.Draw(img_s1_card)

    # Beyaz Stüdyo Kartı + Neon Mavi Çerçeve
    draw_c.rounded_rectangle((10, 10, 490, 870), radius=28, fill=(255, 255, 255), outline=(56, 189, 248), width=3)
    draw_c.rounded_rectangle((30, 30, 220, 75), radius=10, fill=(15, 23, 42))
    draw_c.text((125, 52), " OYUNCU FIRSATI", font=get_font(18, bold=True), fill=(250, 204, 21), anchor="mm")

    # Ürün Görseli
    prod_p = deal.get("image_path")
    if prod_p and os.path.exists(prod_p):
        with Image.open(prod_p) as p_raw:
            p_img = p_raw.convert("RGBA")
            p_img.thumbnail((420, 340), Image.Resampling.LANCZOS)
            px = (500 - p_img.width) // 2
            py = 110 + (340 - p_img.height) // 2
            img_s1_card.paste(p_img, (px, py), p_img)

    # Başlık
    title = deal.get("title", "Mekanik Klavye")
    draw_c.text((30, 485), title[:30], font=get_font(22, bold=True), fill=(15, 23, 42))
    if len(title) > 30:
        draw_c.text((30, 515), title[30:58], font=get_font(22, bold=True), fill=(15, 23, 42))

    # Fiyat Kutusu (Sadece Liste Fiyatı)
    draw_c.rounded_rectangle((30, 570, 470, 680), radius=18, fill=(241, 245, 249), outline=(203, 213, 225), width=2)
    draw_c.text((250, 600), "PİYASA LİSTE FİYATI", font=get_font(16, bold=True), fill=(100, 116, 139), anchor="mm")
    draw_c.text((250, 642), deal.get("old_price", "3.499 TL"), font=get_font(34, bold=True), fill=(71, 85, 105), anchor="mm")

    # Kilitli İndirim Butonu
    draw_c.rounded_rectangle((30, 715, 470, 805), radius=16, fill=(15, 23, 42), outline=(250, 204, 21), width=2)
    draw_c.text((250, 760), " İNDİRİMLİ FİYAT AÇILIYOR...", font=get_font(20, bold=True), fill=(254, 240, 138), anchor="mm")

    card_s1_path = os.path.join(TEMP_DIR, "opt_b_s1_card.png")
    img_s1_card.save(card_s1_path, "PNG")

    # 1b. Sağ Taraf Neon Ok ve Yazı Katmanı
    img_s1_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(img_s1_overlay)

    # Neon Turkuaz Ok
    draw_red_arrow(draw_ov, 500, 580, 640, 580, color=(56, 189, 248), width=12)

    code_text = deal.get("deal_code", "#134")
    draw_ov.text((840, 390), code_text, font=get_font(76, bold=True), fill=(250, 204, 21), anchor="mm")
    draw_ov.text((840, 490), "FIRSAT KODU", font=get_font(46, bold=True), fill=(255, 255, 255), anchor="mm")
    draw_ov.text((840, 565), "İLE FİYAT", font=get_font(46, bold=True), fill=(255, 255, 255), anchor="mm")
    draw_ov.text((840, 640), "ÇÖKTÜ! ", font=get_font(52, bold=True), fill=(244, 63, 94), anchor="mm")

    s1_overlay_path = os.path.join(TEMP_DIR, "opt_b_s1_overlay.png")
    img_s1_overlay.save(s1_overlay_path, "PNG")

    # 2. Sahne: Büyük Stüdyo Son Fiyat & Tasarruf Patlaması
    img_s2 = Image.new("RGB", (W, H), bg_top)
    draw_bg = ImageDraw.Draw(img_s2)
    for y in range(H):
        r = int(bg_top[0] + (bg_bot[0] - bg_top[0]) * (y / H))
        g = int(bg_top[1] + (bg_bot[1] - bg_top[1]) * (y / H))
        b = int(bg_top[2] + (bg_bot[2] - bg_top[2]) * (y / H))
        draw_bg.line([(0, y), (W, y)], fill=(r, g, b))

    draw_s2 = ImageDraw.Draw(img_s2)

    # Üst Rozetler
    draw_s2.rounded_rectangle((54, 70, 310, 120), radius=14, fill=(234, 88, 12))
    draw_s2.text((182, 95), " OYUNCU FIRSATI", font=get_font(22, bold=True), fill=(255, 255, 255), anchor="mm")

    draw_s2.rounded_rectangle((W - 270, 70, W - 54, 120), radius=14, fill=(225, 29, 72))
    draw_s2.text(((W - 270 + W - 54) // 2, 95), f"{deal.get('discount_pct', '-%20')} İNDİRİM", font=get_font(24, bold=True), fill=(255, 255, 255), anchor="mm")

    # Başlık
    draw_s2.text((54, 155), deal.get("title", "Mekanik Klavye")[:36], font=get_font(32, bold=True), fill=(248, 250, 252))

    # Orta Stüdyo Beyaz Kartı (Küçük ve Şık)
    card_box = (54, 195, W - 54, 690)
    draw_s2.rounded_rectangle(card_box, radius=24, fill=(255, 255, 255), outline=(56, 189, 248), width=3)

    if prod_p and os.path.exists(prod_p):
        with Image.open(prod_p) as p_raw:
            p_img = p_raw.convert("RGBA")
            p_img.thumbnail((700, 390), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2
            img_s2.paste(p_img, (px, py), p_img)

    # Killer Hook Rozeti (Kart İçi Altında)
    draw_s2.rounded_rectangle((180, 630, W - 180, 680), radius=14, fill=(15, 23, 42), outline=(250, 204, 21), width=2)
    draw_s2.text((W // 2, 655), " 2.799 TLYE HOT SWAP GRAY SWITCH KLAVYE", font=get_font(21, bold=True), fill=(254, 240, 138), anchor="mm")

    # Alt Fiyat Alanı: Sol Eski Fiyat (Üstü Kırmızı Çizili) -> Sağ Dev Fırsat Fiyatı
    # Sol Kutu
    draw_s2.rounded_rectangle((54, 715, 330, 855), radius=20, fill=(30, 41, 59), outline=(71, 85, 105), width=2)
    draw_s2.text((192, 745), "PİYASA FİYATI", font=get_font(18, bold=True), fill=(148, 163, 184), anchor="mm")
    old_val = deal.get("old_price", "3.499 TL")
    draw_s2.text((192, 795), old_val, font=get_font(34, bold=True), fill=(148, 163, 184), anchor="mm")
    draw_s2.line([(100, 795), (284, 795)], fill=(239, 68, 68), width=3)

    # Orta Ok
    draw_red_arrow(draw_s2, 345, 785, 385, 785, color=(56, 189, 248), width=8)

    # Sağ Hero Kutu: İndirimli Fiyat
    draw_s2.rounded_rectangle((395, 715, W - 54, 855), radius=20, fill=(6, 78, 59), outline=(16, 185, 129), width=3)
    draw_s2.text((710, 745), "İNDİRİMLİ FIRSAT FİYATI", font=get_font(20, bold=True), fill=(167, 243, 208), anchor="mm")
    draw_s2.text((710, 795), deal.get("new_price", "2.799 TL"), font=get_font(58, bold=True), fill=(52, 211, 153), anchor="mm")
    draw_s2.text((710, 835), "700 TL NET TASARRUF  •  3 Taksit x 933 TL", font=get_font(17, bold=True), fill=(253, 224, 71), anchor="mm")

    # En Alt CTA Bandı
    draw_s2.rectangle((0, 885, W, 960), fill=(9, 13, 22))
    draw_s2.line([(0, 885), (W, 885)], fill=(56, 189, 248), width=3)
    draw_s2.text((W // 2, 922), f"Ürün linki PROFİLDE & SİTEDE • KOD: {deal.get('deal_code', '#134')}", font=get_font(24, bold=True), fill=(255, 255, 255), anchor="mm")

    s2_path = os.path.join(TEMP_DIR, "opt_b_s2_hero.png")
    img_s2.save(s2_path, "PNG")

    return {
        "s1_card": card_s1_path,
        "s1_overlay": s1_overlay_path,
        "s2_hero": s2_path
    }

# =========================================================================
# VIDEO RENDER MOTORU (7.2 SANİYE ALTIN SÜRE + AŞAMALI ANİMASYON)
# =========================================================================

def build_option_a_video(assets: dict, meme_video: str, output_path: str):
    # 0.0s - 1.0s: Sol kart -480'den +40'a kayar
    # 1.0s - 3.4s: Ok ve yazı overlay'i açılır
    # 3.4s - 7.2s: Sahne 2 (Sepet/Kazanç özeti) devreye girer
    duration = 7.2

    # Beyaz arka plan
    bg_canvas = os.path.join(TEMP_DIR, "opt_a_white_bg.png")
    Image.new("RGB", (1080, 960), (255, 255, 255)).save(bg_canvas)

    filter_complex = (
        # 1. Sahne: Beyaz zemin üstünde sol kart slide-in
        f"[0:v]scale=1080:960[bg];"
        f"[1:v]scale=480:880[card];"
        f"[2:v]scale=1080:960[ov];"
        f"[bg][card]overlay=x='min(40, -480 + 520*min(1, t/0.75))':y=40:enable='between(t,0,3.4)'[s1_base];"
        f"[s1_base][ov]overlay=0:0:enable='between(t,0.85,3.4)'[top_s1];"
        # 2. Sahne: Sepet Ekranı (Hafif nefes alan canlı zoom)
        f"[3:v]scale=w='1080*(1+0.02*max(0,t-3.4))':h='960*(1+0.02*max(0,t-3.4))':eval=frame,crop=1080:960[top_s2];"
        f"[top_s1][top_s2]overlay=0:0:enable='gte(t,3.4)'[top];"
        # Alt Meme: 1080x960 Tam Ekran
        f"[4:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        # İlerleme Çubuğu (Neon Turuncu)
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
        "-i", meme_video,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "4:a?",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    safe_run_subprocess(cmd, capture_output=True)
    return output_path

def build_option_b_video(assets: dict, meme_video: str, output_path: str):
    duration = 7.2

    # Koyu obsidian zemin
    bg_canvas = os.path.join(TEMP_DIR, "opt_b_dark_bg.png")
    Image.new("RGB", (1080, 960), (11, 15, 25)).save(bg_canvas)

    filter_complex = (
        f"[0:v]scale=1080:960[bg];"
        f"[1:v]scale=500:880[card];"
        f"[2:v]scale=1080:960[ov];"
        f"[bg][card]overlay=x='min(40, -500 + 540*min(1, t/0.75))':y=40:enable='between(t,0,3.4)'[s1_base];"
        f"[s1_base][ov]overlay=0:0:enable='between(t,0.85,3.4)'[top_s1];"
        f"[3:v]scale=w='1080*(1+0.025*max(0,t-3.4))':h='960*(1+0.025*max(0,t-3.4))':eval=frame,crop=1080:960[top_s2];"
        f"[top_s1][top_s2]overlay=0:0:enable='gte(t,3.4)'[top];"
        f"[4:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"color=c=0x0F172A@0.7:s=1080x12:d={duration:.2f}[pbg];"
        f"color=c=0x38BDF8:s=1080x12:d={duration:.2f}[pfill];"
        f"[stacked][pbg]overlay=0:1908[with_pbg];"
        f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{duration:.2f})':y=1908[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", bg_canvas,
        "-loop", "1", "-t", "3.4", "-i", assets["s1_card"],
        "-loop", "1", "-t", "3.4", "-i", assets["s1_overlay"],
        "-loop", "1", "-t", str(duration), "-i", assets["s2_hero"],
        "-i", meme_video,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "4:a?",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    safe_run_subprocess(cmd, capture_output=True)
    return output_path

if __name__ == "__main__":
    deal_sample = {
        "title": "Aula F75 RGB Kablosuz Mekanik Klavye",
        "old_price": "3.499 TL",
        "new_price": "2.799 TL",
        "discount_pct": "-%20",
        "deal_code": "#134",
        "image_path": "temp/prod_aula_f75_rgb_kablosuz_mekanik_.jpg"
    }

    meme = "assets/memes/conor_mcgregor.mp4"
    if not os.path.exists(meme):
        meme = "assets/memes/the_rock.mp4"

    print("🎨 Seçenek A varlıkları üretiliyor...")
    assets_a = create_option_a_assets(deal_sample)
    out_a = os.path.join(OUTPUT_DIR, "ornek_secenek_A_dogal_sepet.mp4")
    print(f"🎬 Seçenek A videosu derleniyor: {out_a}...")
    build_option_a_video(assets_a, meme, out_a)

    print("🎨 Seçenek B varlıkları üretiliyor...")
    assets_b = create_option_b_assets(deal_sample)
    out_b = os.path.join(OUTPUT_DIR, "ornek_secenek_B_studyo_hareketli.mp4")
    print(f"🎬 Seçenek B videosu derleniyor: {out_b}...")
    build_option_b_video(assets_b, meme, out_b)

    print("✅ İki örnek video da başarıyla üretildi!")
