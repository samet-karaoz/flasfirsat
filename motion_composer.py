"""
motion_composer.py - Kademeli Hareketli Banner Video Motoru (Staggered Motion Graphics)
========================================================================================
Referans Reels ve TikTok mekaniğini temel alan, statik şablon kısıtlamalarını ve
izlenme cezalarını (90-215 izlenme bariyeri) %100 kıran 3 adımlı dinamik hareket motoru.

Mimari Akış:
- Adım 1 (0.00s - 0.70s): Ürün stüdyo kartı ekranın yukarısından akıcı bir yaylanma (ease_out_back) ile iner.
- Adım 2 (0.70s - 1.35s): Doğrulanmış eski fiyat kutusu ekranın solundan hızla kayarak yerini alır.
  (Eğer eski fiyat yoksa, tek büyük hero fiyat kutusu alttan kayarak oturur).
- Adım 3 (1.35s - 2.05s): İndirimli yeşil fırsat kutusu ve ok ekranın sağından kayıp oturur.
  Floating "NET TASARRUF" rozeti ferah tampon alanıyla (headroom) kesilmeden parlar.
- Adım 4 (2.05s - 2.45s): Dinamik kırmızı çizgi eski fiyatın üzerini çizer.
- Adım 5 (2.45s - 7.00s): Kamera %100 SABİT (kullanıcı talebiyle yakınlaşma kaldırıldı),
  meme altta oynarken üst taraf kaya gibi stabil durur.

Uyumluluk:
- İki fiyatlı (eski + yeni) veya tek fiyatlı tüm ürün tiplerini destekler.
- Kuponlu, taksitli, killer hook rozetli tüm ürün senaryolarıyla %100 çakışmasız çalışır.
- Instagram (Profilde & Hikayede) ve YouTube Shorts (Yorumlarda & BİO'da) CTA bandına tam uyumludur.
- Android 13 Xiaomi Redmi Note 11 Pro üstveri enjeksiyonu ve anti-hash koruması içerir.
"""

import os
import re
import math
import random
import shutil
import datetime
from PIL import Image, ImageDraw, ImageFilter

from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, safe_run_subprocess

MEMES_DIR = os.path.join(BASE_DIR, "assets", "memes")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")
from split_composer import (
    get_font,
    draw_vector_bolt,
    draw_vector_shield_check,
    draw_vector_link,
    draw_vector_dm_plane,
    draw_vector_trend_down,
    select_banner_theme,
    parse_price_to_float,
    BANNER_THEMES,
    select_smart_meme,
    select_smart_reaction_hook,
    create_reaction_hook_overlay,
    AVAILABLE_MEMES,
    AVAILABLE_AUDIOS
)

UNSUPPORTED_TTF_REGEX = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)


def sanitize_text(text: str) -> str:
    """TTF fontunda tofu (kutu) oluşturabilecek emojileri ve geçersiz karakterleri temizler."""
    if not text:
        return ""
    text = UNSUPPORTED_TTF_REGEX.sub("", str(text))
    clean = "".join(c for c in text if c.isprintable())
    return clean.strip()


# =========================================================================
# EASING FONKSİYONLARI (Akıcı Hareket Fiziği)
# =========================================================================
def ease_out_cubic(x: float) -> float:
    return 1 - pow(1 - x, 3)


def ease_out_back(x: float, c1: float = 1.70158) -> float:
    c3 = c1 + 1
    return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2)


# =========================================================================
# KADEMELİ HAREKETLİ BANNER KARELERİ OLUŞTURUCU
# =========================================================================
def generate_staggered_banner_frames(
    deal: dict,
    total_frames: int,
    fps: int = 30,
    cta_type: str = "instagram",
    frames_dir: str = None
) -> str:
    """
    Belirtilen deal verisi için 1080x960 çözünürlüğünde 3 adımlı kademeli animasyonlu
    PNG kare dizisini (staggered frames) üretir ve dizin yolunu döndürür.
    """
    if not frames_dir:
        frames_dir = os.path.join(TEMP_DIR, f"staggered_frames_{random.randint(1000, 9999)}")
    os.makedirs(frames_dir, exist_ok=True)

    W, H = 1080, 960

    # 1. Deal Verilerini Çözümle
    title = sanitize_text(deal.get("title", "Günün Fırsatı"))
    old_price = sanitize_text(deal.get("old_price", ""))
    new_price = sanitize_text(deal.get("new_price", "İndirimde"))
    discount_pct = sanitize_text(deal.get("discount_pct", "-30%"))
    store_name = sanitize_text(deal.get("store_name", "Amazon TR"))
    badge_text = sanitize_text(deal.get("badge", "DEV İNDİRİM"))
    installment = sanitize_text(deal.get("installment", ""))
    coupon_text = sanitize_text(deal.get("coupon_info", ""))
    deal_code = sanitize_text(deal.get("deal_code", "#101"))
    feature_text = sanitize_text(deal.get("killer_hook") or deal.get("feature_pill", ""))
    is_lowest_30d = bool(deal.get("is_lowest_30d", False))
    market_badge = sanitize_text(deal.get("market_badge", ""))
    seller_badge_text = sanitize_text(deal.get("seller_badge", ""))
    image_path = deal.get("image_path")
    skip_rembg = bool(deal.get("skip_rembg", False))

    # Fiyat Doğrulama Mantığı
    old_val = parse_price_to_float(old_price) if old_price else 0.0
    new_val = parse_price_to_float(new_price) if new_price else 0.0
    has_verified_old_price = bool(
        deal.get("has_verified_old_price", False) or
        (old_val > 0 and new_val > 0 and old_val >= new_val * 1.08)
    )
    show_old_price = bool(has_verified_old_price and old_val >= new_val * 1.08)
    savings = (old_val - new_val) if (show_old_price and old_val > new_val) else 0.0

    # Tema Seçimi
    theme = select_banner_theme(title=title, discount_pct=discount_pct, badge_text=badge_text, theme_name="auto")
    theme_title_col = theme["title_color"]

    # Fontlar
    f_badge = get_font("segoeuib", 25)
    f_pct = get_font("segoeuib", 26)
    f_title = get_font("segoeuib", 29)
    f_tiny = get_font("segoeuib", 13)
    f_cta_bold = get_font("segoeuib", 24)
    f_trust = get_font("segoeuib", 19)
    f_label = get_font("segoeuib", 19)
    f_killer = get_font("segoeuib", 22)
    f_old_lbl = get_font("segoeuib", 17)
    f_old_price = get_font("segoeuib", 36)
    f_new_lbl = get_font("segoeuib", 20)
    f_new_price = get_font("segoeuib", 60)
    f_net = get_font("segoeuib", 19)
    f_savings = get_font("segoeuib", 21)

    # -------------------------------------------------------------------------
    # KATMAN A: Sabit Arka Plan (Gradyan + Başlık + Üst Rozetler + Alt CTA)
    # -------------------------------------------------------------------------
    bg_rgb = Image.new("RGB", (W, H), theme["bg_top"])
    draw_bg = ImageDraw.Draw(bg_rgb)
    for y in range(H):
        r = int(theme["bg_top"][0] + (theme["bg_bottom"][0] - theme["bg_top"][0]) * (y / H))
        g = int(theme["bg_top"][1] + (theme["bg_bottom"][1] - theme["bg_top"][1]) * (y / H))
        b = int(theme["bg_top"][2] + (theme["bg_bottom"][2] - theme["bg_top"][2]) * (y / H))
        draw_bg.line([(0, y), (W, y)], fill=(r, g, b))

    bg_img = bg_rgb.convert("RGBA")
    draw_a = ImageDraw.Draw(bg_img, "RGBA")

    # Sol Rozet
    left_badge = badge_text if badge_text else "DEV İNDİRİM"
    b_w = draw_a.textlength(left_badge, font=f_badge)
    b1_x2 = int(54 + b_w + 64)
    draw_a.rounded_rectangle((54, 90, b1_x2, 140), radius=14, fill=theme["badge_left_bg"])
    draw_vector_bolt(draw_a, 78, 115, (255, 215, 0))
    draw_a.text((96 + b_w // 2, 115), left_badge, font=f_badge, fill=(255, 255, 255), anchor="mm")

    # Sağ Rozet (% İndirim)
    pct_txt = discount_pct if discount_pct else "-%30 İNDİRİM"
    if not pct_txt.endswith("İNDİRİM"):
        pct_txt = f"{pct_txt} İNDİRİM"
    p_w = draw_a.textlength(pct_txt, font=f_pct)
    b2_x1 = int(W - 54 - p_w - 44)
    draw_a.rounded_rectangle((b2_x1, 90, W - 54, 140), radius=14, fill=theme["badge_right_bg"])
    draw_a.text(((b2_x1 + W - 54) // 2, 115), pct_txt, font=f_pct, fill=(255, 255, 255), anchor="mm")

    # Ürün Başlığı (2 Satıra Güvenli Bölme)
    words = title.split()
    line1, line2 = "", ""
    for w in words:
        test = f"{line1} {w}".strip()
        if draw_a.textlength(test, font=f_title) <= (W - 108):
            line1 = test
        else:
            line2 = f"{line2} {w}".strip()

    if len(line2) > 42:
        line2 = line2[:40] + "..."

    draw_a.text((54, 148), line1, font=f_title, fill=theme_title_col)
    if line2:
        draw_a.text((54, 182), line2, font=f_title, fill=theme_title_col)

    # Alt CTA Bandı (Platforma Göre: Instagram vs YouTube)
    draw_a.rectangle((0, 898, W, 960), fill=theme["cta_bg"])
    draw_a.line((0, 898, W, 898), fill=theme["cta_line"], width=4)

    clean_code = f"#{re.sub(r'[^a-zA-Z0-9]', '', deal_code)}" if deal_code else "#101"

    if cta_type == "youtube":
        cta_prefix = "Satın alma linki "
        cta_highlight = "YORUMLARDA & BİO'DA"
        cta_suffix = f" • KOD: {clean_code} • Kaçırma!"
        cta_tag = "#Shorts"
    else:
        cta_prefix = "Ürün linki "
        cta_highlight = "PROFİLDE & HİKAYEDE"
        cta_suffix = f" • KOD: {clean_code} • Fırsatı Kaçırma!"
        cta_tag = "#işbirliği #reklam"

    cp_w = draw_a.textlength(cta_prefix, font=f_cta_bold)
    ch_w = draw_a.textlength(cta_highlight, font=f_cta_bold)
    cs_w = draw_a.textlength(cta_suffix, font=f_cta_bold)
    pill_w = int(ch_w + 26)
    tot_cta_w = int(34 + cp_w + 8 + pill_w + 10 + cs_w + 34)
    st_x = (W - tot_cta_w) // 2 - 20
    draw_vector_link(draw_a, st_x + 14, 929, theme["cta_line"])
    tx = int(st_x + 36)
    draw_a.text((tx, 929), cta_prefix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
    tx += int(cp_w + 6)
    draw_a.rounded_rectangle((tx, 910, tx + pill_w, 948), radius=8, fill=theme["cta_pill_bg"])
    draw_a.text((tx + pill_w // 2, 929), cta_highlight, font=f_cta_bold, fill=theme["cta_pill_fg"], anchor="mm")
    tx += pill_w + 10
    draw_a.text((tx, 929), cta_suffix, font=f_cta_bold, fill=(255, 255, 255), anchor="lm")
    tx += int(cs_w + 18)
    draw_vector_dm_plane(draw_a, tx, 929, theme["cta_line"])
    draw_a.text((W - 20, 930), cta_tag, font=f_tiny, fill=(148, 163, 184), anchor="rm")

    # -------------------------------------------------------------------------
    # KATMAN B: Ürün Stüdyo Kartı (Beyaz Kart + Spotlight + Ürün + Rozetler)
    # -------------------------------------------------------------------------
    CARD_W, CARD_H = 972, 516
    card_img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw_card = ImageDraw.Draw(card_img, "RGBA")
    draw_card.rounded_rectangle((0, 0, CARD_W, CARD_H), radius=24, fill=(255, 255, 255, 255), outline=theme["card_border"], width=3)

    # Spotlight Işıma
    glow_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    gcx, gcy = CARD_W // 2, CARD_H // 2 + 6
    glow_draw.ellipse((gcx - 210, gcy - 185, gcx + 210, gcy + 185), fill=theme["glow_color"])
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=55))
    card_img.paste(glow_layer, (0, 0), glow_layer)
    draw_card = ImageDraw.Draw(card_img, "RGBA")

    # Satıcı Rozeti (Sol Üst)
    trust_text = seller_badge_text if seller_badge_text else ("AMAZON TR RESMİ SATICI" if "amazon" in store_name.lower() else f"{store_name.upper()} DOĞRULANMIŞ")
    tr_w = draw_card.textlength(trust_text, font=f_trust)
    draw_card.rounded_rectangle((16, 16, 16 + 44 + tr_w, 50), radius=10, fill=theme["trust_bg"])
    draw_vector_shield_check(draw_card, 33, 33, (16, 185, 129))
    draw_card.text((50 + tr_w // 2, 33), trust_text, font=f_trust, fill=theme["trust_fg"], anchor="mm")

    # Sağ Üst: Son 30 Günün En Düşüğü / Market Badge
    top_badge_text = "SON 30 GÜNÜN EN DÜŞÜĞÜ" if is_lowest_30d else (market_badge.strip().upper() if market_badge else "")
    if top_badge_text:
        low_w = draw_card.textlength(top_badge_text, font=f_trust)
        lx1 = int(CARD_W - low_w - 58)
        draw_card.rounded_rectangle((lx1, 16, CARD_W - 16, 50), radius=10, fill=(255, 241, 242), outline=(254, 205, 211), width=1)
        draw_vector_trend_down(draw_card, lx1 + 20, 33, (225, 29, 72))
        draw_card.text((lx1 + 36 + low_w // 2, 33), top_badge_text, font=f_trust, fill=(225, 29, 72), anchor="mm")

    # Ürün Görseli & 3D Zemin Gölgesi
    if image_path and os.path.exists(image_path):
        try:
            cutout_p = f"{os.path.splitext(image_path)[0]}_cutout.png"
            load_p = cutout_p if (not skip_rembg and os.path.exists(cutout_p)) else image_path
            p_img = Image.open(load_p).convert("RGBA")
            alpha = p_img.split()[-1]
            bbox = alpha.getbbox()
            if bbox and (bbox[2] - bbox[0] >= 60) and (bbox[3] - bbox[1] >= 60):
                p_img = p_img.crop(bbox)
            elif load_p != image_path:
                p_img = Image.open(image_path).convert("RGBA")

            p_img.thumbnail((CARD_W - 70, CARD_H - 135), Image.Resampling.LANCZOS)
            px = (CARD_W - p_img.width) // 2
            py = (CARD_H - p_img.height) // 2 - 10

            # 3D Zemin Gölgesi
            sh_w = max(80, int(p_img.width * 0.82))
            sh_layer = Image.new("RGBA", (sh_w + 80, 90), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(sh_layer)
            sh_draw.ellipse((40, 30, 40 + sh_w, 60), fill=(15, 23, 42, 85))
            sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=13))
            card_img.paste(sh_layer, ((CARD_W - sh_layer.width) // 2, py + p_img.height - 20), sh_layer)
            card_img.paste(p_img, (px, py), p_img)
            draw_card = ImageDraw.Draw(card_img, "RGBA")
        except Exception as e:
            print(f"[MotionBanner] Görsel yükleme uyarısı: {e}")

    # Kart İçi Alt Kısım: Killer Hook veya Standart Taksit/Mağaza Rozetleri
    has_killer_hook = bool(feature_text and len(feature_text.strip()) > 3)
    if has_killer_hook:
        feat_clean = re.sub(r'[\U00010000-\U0010ffff]', '', feature_text)
        feat_clean = re.sub(r'[\u2600-\u27BF]', '', feat_clean).strip().upper()
        feat_w = draw_card.textlength(feat_clean, font=f_killer)
        fbox_w = min(CARD_W - 80, int(feat_w + 56))
        fbox_h = 44
        fx = (CARD_W - fbox_w) // 2
        # Fiyat kutularıyla çakışmayı kesinlikle önlemek için kart içine 18px yukarı alındı
        fy = CARD_H - 74
        draw_card.rounded_rectangle((fx, fy, fx + fbox_w, fy + fbox_h), radius=14, fill=(15, 23, 42, 245), outline=(250, 204, 21), width=2)
        draw_vector_bolt(draw_card, fx + 20, fy + fbox_h // 2, (250, 204, 21))
        draw_card.text((fx + 34 + feat_w // 2, fy + fbox_h // 2), feat_clean, font=f_killer, fill=(254, 240, 138), anchor="mm")
    else:
        # Dinamik Mağaza Rozeti (Sağ Alt)
        tag_text = f"{store_name.upper()}  •  @flasfirsat.tr"
        t_w = draw_card.textlength(tag_text, font=f_label)
        sx1 = int(CARD_W - t_w - 40)
        draw_card.rounded_rectangle((sx1, CARD_H - 48, CARD_W - 16, CARD_H - 14), radius=9, fill=(15, 23, 42))
        draw_card.text(((sx1 + CARD_W - 16) // 2, CARD_H - 31), tag_text, font=f_label, fill=(255, 255, 255), anchor="mm")

        # Taksit Rozeti (Sol Alt)
        clean_inst = re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip() if installment else "Peşin Fiyatına 3 Taksit"
        it_w = draw_card.textlength(clean_inst, font=f_label)
        ix2 = int(16 + 44 + it_w)
        draw_card.rounded_rectangle((16, CARD_H - 48, ix2, CARD_H - 14), radius=9, fill=theme["inst_bg"], outline=(16, 185, 129), width=1)
        draw_card.text(((16 + ix2) // 2, CARD_H - 31), clean_inst, font=f_label, fill=theme["inst_fg"], anchor="mm")

    # -------------------------------------------------------------------------
    # KATMAN C & D: FİYAT KUTULARI (İki Kutulu veya Tek Hero Kutulu)
    # -------------------------------------------------------------------------
    HEADROOM = 44
    BOX_H = 138

    # Alt Bilgi Metni (Taksit, Kupon, Tasarruf)
    sub_parts = []
    clean_coupon = re.sub(r'[^\w\s.,xX+\-/%]', '', coupon_text).strip() if coupon_text else ""
    if clean_coupon:
        sub_parts.append("Sayfadaki Kuponu Aktif Et")
    if installment:
        sub_parts.append(re.sub(r'[^\w\s.,xX+\-/%]', '', installment).strip())
    elif savings > 0 and not clean_coupon:
        sav_fmt = f"{int(savings):,} TL".replace(',', '.')
        sub_parts.append(f"Net İndirim: {sav_fmt}")
    sub_str = "  •  ".join(sub_parts) if sub_parts else ""

    old_box_img = None
    new_box_img = None
    hero_box_img = None

    if show_old_price:
        # 1. Eski Fiyat Kutusu (Sol: 274 x 138)
        OLD_W = 274
        old_box_img = Image.new("RGBA", (OLD_W, BOX_H), (0, 0, 0, 0))
        draw_old = ImageDraw.Draw(old_box_img, "RGBA")
        draw_old.rounded_rectangle((0, 0, OLD_W, BOX_H), radius=20, fill=theme["old_box_bg"], outline=theme["old_box_border"], width=2)
        ocx = OLD_W // 2
        draw_old.text((ocx, 24), "PİYASA FİYATI", font=f_old_lbl, fill=theme["old_text_col"], anchor="mm")
        draw_old.text((ocx, 78), old_price, font=f_old_price, fill=theme["old_text_col"], anchor="mm")

        # 2. İndirimli Fiyat Kutusu + Ok (Sağ: 686 x 182)
        NEW_W = 686
        NEW_H = BOX_H + HEADROOM
        new_box_img = Image.new("RGBA", (NEW_W, NEW_H), (0, 0, 0, 0))
        draw_new = ImageDraw.Draw(new_box_img, "RGBA")

        # Orta Ok Kutusu
        arrow_y = HEADROOM + (BOX_H - 42) // 2
        draw_new.rounded_rectangle((0, arrow_y, 42, arrow_y + 42), radius=10, fill=theme["arrow_bg"], outline=theme["old_box_border"], width=1)
        draw_new.line((21 - 4, arrow_y + 21 - 8, 21 + 4, arrow_y + 21), fill=theme["arrow_fg"], width=3)
        draw_new.line((21 + 4, arrow_y + 21, 21 - 4, arrow_y + 21 + 8), fill=theme["arrow_fg"], width=3)

        # Sağ Yeşil Kutu
        gw = NEW_W - 54
        draw_new.rounded_rectangle((54, HEADROOM, NEW_W, HEADROOM + BOX_H), radius=20, fill=theme["new_box_bg"], outline=theme["new_box_border"], width=3)
        ncx = 54 + gw // 2
        lbl_new = "KUPONLU FIRSAT FİYATI" if clean_coupon else "İNDİRİMLİ FIRSAT FİYATI"
        draw_new.text((ncx, HEADROOM + 26), lbl_new, font=f_new_lbl, fill=theme["new_label_col"], anchor="mm")
        draw_new.text((ncx, HEADROOM + 72), new_price, font=f_new_price, fill=theme["new_price_col"], anchor="mm")
        if sub_str:
            draw_new.text((ncx, HEADROOM + 116), sub_str, font=f_net, fill=theme["new_label_col"], anchor="mm")

        # Floating Rozet (Kupon veya Net İndirim)
        pill_txt = ""
        if clean_coupon:
            up_c = clean_coupon.upper()
            pill_txt = up_c if up_c.startswith("KUPON") else f"KUPON: {up_c}"
        elif savings > 0:
            sav_fmt = f"{int(savings):,} TL".replace(',', '.')
            pill_txt = f"{sav_fmt} NET İNDİRİM"

        if pill_txt:
            sw = draw_new.textlength(pill_txt, font=f_savings)
            pw = int(sw + 48)
            px1 = ncx - pw // 2
            pill_h = 34
            pill_y1 = HEADROOM - 34 + 6
            pill_y2 = pill_y1 + pill_h
            draw_new.rounded_rectangle((px1, pill_y1, px1 + pw, pill_y2), radius=12, fill=theme["savings_pill_bg"])
            draw_new.text((ncx, (pill_y1 + pill_y2) // 2), pill_txt, font=f_savings, fill=theme["savings_pill_fg"], anchor="mm")

    else:
        # Tek Büyük ve Geniş Hero Kutu (Old price yoksa)
        HERO_W = W - 108  # 972
        HERO_H = BOX_H + HEADROOM
        hero_box_img = Image.new("RGBA", (HERO_W, HERO_H), (0, 0, 0, 0))
        draw_hero = ImageDraw.Draw(hero_box_img, "RGBA")
        draw_hero.rounded_rectangle((0, HEADROOM, HERO_W, HEADROOM + BOX_H), radius=20, fill=theme["new_box_bg"], outline=theme["new_box_border"], width=3)
        hcx = HERO_W // 2
        lbl_single = "KUPONLU FIRSAT FİYATI" if clean_coupon else "GÜNÜN ÖNE ÇIKAN SATIŞ FİYATI"
        draw_hero.text((hcx, HEADROOM + 26), lbl_single, font=f_new_lbl, fill=theme["new_label_col"], anchor="mm")
        draw_hero.text((hcx, HEADROOM + 72), new_price, font=f_new_price, fill=theme["new_price_col"], anchor="mm")
        if sub_str:
            draw_hero.text((hcx, HEADROOM + 116), sub_str, font=f_net, fill=theme["new_label_col"], anchor="mm")

        # Floating Kupon Rozeti
        if clean_coupon:
            up_c = clean_coupon.upper()
            c_clean = up_c if up_c.startswith("KUPON") else f"KUPON: {up_c}"
            cw = draw_hero.textlength(c_clean, font=f_savings)
            pw = int(cw + 48)
            px1 = hcx - pw // 2
            pill_h = 34
            pill_y1 = HEADROOM - 34 + 6
            pill_y2 = pill_y1 + pill_h
            draw_hero.rounded_rectangle((px1, pill_y1, px1 + pw, pill_y2), radius=12, fill=theme["savings_pill_bg"])
            draw_hero.text((hcx, (pill_y1 + pill_y2) // 2), c_clean, font=f_savings, fill=theme["savings_pill_fg"], anchor="mm")

    # -------------------------------------------------------------------------
    # KARE ÜRETİM DÖNGÜSÜ (30 FPS Akıcı Easing Hesaplamaları)
    # -------------------------------------------------------------------------
    target_card_x, target_card_y = 54, 218
    start_card_y = -CARD_H - 80

    target_old_x, target_old_y = 54, 750
    start_old_x = -334  # -OLD_W - 60

    target_new_x, target_new_y = 340, 750
    start_new_x = W + 60

    settled_frame = None

    for f_idx in range(total_frames):
        t = f_idx / fps

        # Animasyon 2.45s sonrasında tamamen yerleştiğinde kareyi kopyala (Hızlandırma)
        if t >= 2.45 and settled_frame is not None:
            out_p = os.path.join(frames_dir, f"frame_{f_idx:04d}.png")
            settled_frame.save(out_p, "PNG")
            continue

        frame = bg_img.copy()

        # ADIM 1: Ürün Stüdyo Kartı (0.00s -> 0.70s, Üstten Aşağı Yaylanarak İniş)
        t_start_card, t_dur_card = 0.0, 0.70
        if t <= t_start_card:
            card_cur_y = start_card_y
        elif t <= t_start_card + t_dur_card:
            prog = (t - t_start_card) / t_dur_card
            card_cur_y = int(start_card_y + (target_card_y - start_card_y) * ease_out_back(prog, c1=1.2))
        else:
            card_cur_y = target_card_y

        if card_cur_y + CARD_H > 0:
            frame.paste(card_img, (target_card_x, card_cur_y), card_img)

        if show_old_price:
            # ADIM 2: Eski Fiyat Kutusu (0.70s -> 1.35s, Soldan Sağa Kayış)
            t_start_old, t_dur_old = 0.70, 0.65
            if t < t_start_old:
                old_cur_x = start_old_x
            elif t <= t_start_old + t_dur_old:
                prog = (t - t_start_old) / t_dur_old
                old_cur_x = int(start_old_x + (target_old_x - start_old_x) * ease_out_back(prog, c1=1.1))
            else:
                old_cur_x = target_old_x

            if old_cur_x + 274 > 0 and old_box_img:
                frame.paste(old_box_img, (old_cur_x, target_old_y), old_box_img)

            # ADIM 3: İndirimli Fiyat Kutusu (1.35s -> 2.05s, Sağdan Sola Kayış)
            t_start_new, t_dur_new = 1.35, 0.70
            if t < t_start_new:
                new_cur_x = start_new_x
            elif t <= t_start_new + t_dur_new:
                prog = (t - t_start_new) / t_dur_new
                new_cur_x = int(start_new_x + (target_new_x - start_new_x) * ease_out_back(prog, c1=1.1))
            else:
                new_cur_x = target_new_x

            if new_cur_x < W and new_box_img:
                frame.paste(new_box_img, (new_cur_x, target_new_y - HEADROOM), new_box_img)

            # ADIM 4: Dinamik Kırmızı Çizgi (2.05s -> 2.45s)
            if t >= 2.05 and old_cur_x == target_old_x:
                draw_strike = ImageDraw.Draw(frame)
                line_start_x = target_old_x + (274 // 2) - 80
                line_target_x = target_old_x + (274 // 2) + 80
                line_y = target_old_y + 78
                t_strike_dur = 0.35
                prog_l = min(1.0, (t - 2.05) / t_strike_dur)
                cur_end_x = int(line_start_x + (line_target_x - line_start_x) * ease_out_cubic(prog_l))
                draw_strike.line([(line_start_x, line_y), (cur_end_x, line_y)], fill=(239, 68, 68), width=3)

        else:
            # Tek Hero Kutu Durumu: 0.70s -> 1.45s Alttan Yukarı Kayış
            t_start_hero, t_dur_hero = 0.70, 0.75
            start_hero_y = H + 60
            target_hero_y = 750
            if t < t_start_hero:
                hero_cur_y = start_hero_y
            elif t <= t_start_hero + t_dur_hero:
                prog = (t - t_start_hero) / t_dur_hero
                hero_cur_y = int(start_hero_y + (target_hero_y - start_hero_y) * ease_out_back(prog, c1=1.1))
            else:
                hero_cur_y = target_hero_y

            if hero_cur_y < H and hero_box_img:
                frame.paste(hero_box_img, (54, hero_cur_y - HEADROOM), hero_box_img)

        # 2.45s anında veya sonrasında settled frame'i kaydet
        if t >= 2.45 and settled_frame is None:
            settled_frame = frame.convert("RGB")

        out_frame_p = os.path.join(frames_dir, f"frame_{f_idx:04d}.png")
        frame.convert("RGB").save(out_frame_p, "PNG")

    return frames_dir


# =========================================================================
# ANA VİDEO MOTORU (build_motion_deal_video)
# =========================================================================
def build_motion_deal_video(
    deal: dict,
    meme_name: str = None,
    audio_name: str = None,
    output_filename: str = None,
    cta_type: str = "instagram",
    reaction_text: str = None,
    is_price_error: bool = False,
    duration: float = 9.0
) -> str:
    """
    Kademeli Hareket Grafikleri (Staggered Motion) motoru ile 9.0 saniyelik rahat okunur,
    1080x1920 MP4 video derler:
    - Üst Yarı (1080x960): 3 adımlı dinamik motion banner (Ürün üstten, eski fiyat soldan, indirim sağdan).
    - Alt Yarı (1080x960): İlgili viral meme videosu (Tam 1080x960 ve doğal sesiyle).
    - Meme Üstü: Akıllı reaksiyon kancası (Reaction Hook).
    - En Alt: Dinamik neon ilerleme çubuğu (Animated Progress Bar).
    - Üstveri: Xiaomi Redmi Note 11 Pro Android 13 mobil üstveri enjeksiyonu.
    - Kamera: Yakınlaşma yok, %100 net ve stabil.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    FPS = 30
    # Süre: 9.0 saniye (Kullanıcı talebiyle 2 saniye uzatıldı: 270 kare, rahat okunur stabil bekleme)
    TOTAL_DURATION = float(duration if duration is not None else 9.0)
    TOTAL_FRAMES = int(FPS * TOTAL_DURATION)  # 270 Kare

    # 1. Meme Videosunu Seç
    if meme_name:
        if not meme_name.endswith(".mp4"):
            meme_name += ".mp4"
        bottom_meme_path = os.path.join(MEMES_DIR, meme_name)
    else:
        chosen = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
        bottom_meme_path = os.path.join(MEMES_DIR, chosen)

    if not os.path.exists(bottom_meme_path):
        for candidate in ["vince_mcmahon.mp4", "degirmenci_dayi_cj.mp4", "the_rock.mp4", "knight_cat.mp4"]:
            cand_p = os.path.join(MEMES_DIR, candidate)
            if os.path.exists(cand_p):
                bottom_meme_path = cand_p
                break

    if not os.path.exists(bottom_meme_path):
        raise FileNotFoundError(f"Meme videosu bulunamadı: {bottom_meme_path}")

    # 2. Akıllı Reaksiyon Başlığı (Reaction Hook Overlay)
    if not reaction_text:
        reaction_text = select_smart_reaction_hook(
            discount_pct=deal.get("discount_pct", ""),
            product_title=deal.get("title", ""),
            is_price_error=is_price_error,
            meme_name=bottom_meme_path,
            deal=deal
        )
    reaction_overlay_path = os.path.join(TEMP_DIR, f"reaction_{random.randint(1000, 9999)}.png")
    create_reaction_hook_overlay(reaction_text, reaction_overlay_path)

    # 3. Kademeli Hareketli Kareleri Üret (Pillow)
    frames_dir = os.path.join(TEMP_DIR, f"staggered_frames_{random.randint(1000, 9999)}")
    try:
        generate_staggered_banner_frames(
            deal=deal,
            total_frames=TOTAL_FRAMES,
            fps=FPS,
            cta_type=cta_type,
            frames_dir=frames_dir
        )

        # 4. Çıktı Dosya Adı
        if not output_filename:
            slug = sanitize_text(deal.get("title", "firsat"))[:25]
            slug = "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in slug)
            slug = "_".join(slug.split()).lower()
            output_filename = f"motion_{slug}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # 5. Ses Yapılandırması (Öncelik: Meme'in kendi sesi)
        chk_a = safe_run_subprocess(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
        has_meme_audio = "Audio:" in chk_a.stderr

        use_ext_audio = False
        if audio_name:
            if not audio_name.endswith(".m4a"):
                audio_name += ".m4a"
            audio_path = os.path.join(AUDIO_DIR, audio_name)
            use_ext_audio = os.path.exists(audio_path)
        elif not has_meme_audio:
            available_audios = [a for a in AVAILABLE_AUDIOS if os.path.exists(os.path.join(AUDIO_DIR, a))]
            chosen_audio = random.choice(available_audios) if available_audios else "phonk_meme.m4a"
            audio_path = os.path.join(AUDIO_DIR, chosen_audio)
            use_ext_audio = os.path.exists(audio_path)

        # 6. Anti-Hash Mikro Varyasyon (Gözle fark edilmez, pHash ve MD5'i %100 özgün yapar)
        rnd_bright = round(random.uniform(-0.008, 0.008), 4)
        rnd_sat = round(random.uniform(0.99, 1.02), 4)
        rnd_contrast = round(random.uniform(0.995, 1.015), 4)

        scale_bottom = (
            f"scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,"
            f"eq=brightness={rnd_bright}:saturation={rnd_sat}:contrast={rnd_contrast}"
        )

        # Neon İlerleme Çubuğu (7.0s)
        progress_bar_filter = (
            f"color=c=0x0F172A@0.8:s=1080x14:d={TOTAL_DURATION:.2f}[pbg];"
            f"color=c=0xFF5722:s=1080x14:d={TOTAL_DURATION:.2f}[pfill];"
            f"[stacked][pbg]overlay=0:1906[with_pbg];"
            f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{TOTAL_DURATION:.2f})':y=1906[v]"
        )

        # FFmpeg Komutu:
        # [0:v]: Üstteki 210 karelik kademeli animasyon dizisi (1080x960, 30fps) - Sabit, yakınlaşma yok!
        # [1:v]: Alttaki meme videosu
        # [2:v]: Meme üzerindeki reaksiyon kancası overlay'i
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(frames_dir, "frame_%04d.png"),
            "-stream_loop", "-1", "-ss", "00:00:00", "-t", str(TOTAL_DURATION),
            "-i", bottom_meme_path,
            "-loop", "1", "-i", reaction_overlay_path,
        ]

        if use_ext_audio:
            cmd += ["-i", audio_path]
            audio_source = "[3:a]"
        else:
            audio_source = "[1:a]"

        filter_complex = (
            f"[0:v]copy[top];"
            f"[1:v]{scale_bottom}[bottom_raw];"
            f"[bottom_raw][2:v]overlay=0:0[bottom];"
            f"[top][bottom]vstack=inputs=2[stacked];"
            f"{progress_bar_filter};"
            f"{audio_source}volume=1.0[a]"
        )

        iso_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]",
            "-t", str(TOTAL_DURATION),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            # Anti-Hash Kalkanı: Android 13 Xiaomi Redmi Note 11 Pro mobil üstveri enjeksiyonu
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            "-flags:v", "+bitexact",
            "-flags:a", "+bitexact",
            "-brand", "mp42",
            "-metadata", "com.android.version=13",
            "-metadata", "com.android.manufacturer=Xiaomi",
            "-metadata", 'com.android.model="Redmi Note 11 Pro"',
            "-metadata:s:v:0", "handler_name=VideoHandle",
            "-metadata:s:a:0", "handler_name=SoundHandle",
            "-metadata", f"creation_time={iso_now}",
            "-movflags", "+faststart+use_metadata_tags",
            output_path
        ]

        safe_run_subprocess(cmd, capture_output=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 50000:
            print(f"🎬 [Staggered Motion] Video başarıyla üretildi: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"FFmpeg render başarısız oldu veya dosya üretilemedi: {output_path}")

    finally:
        # Geçici kareleri ve overlay dosyasını temizle
        if os.path.exists(frames_dir):
            try:
                shutil.rmtree(frames_dir, ignore_errors=True)
            except Exception:
                pass
        if os.path.exists(reaction_overlay_path):
            try:
                os.remove(reaction_overlay_path)
            except Exception:
                pass
