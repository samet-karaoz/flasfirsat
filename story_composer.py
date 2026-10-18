import os
import math
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR, TEMP_DIR, ASSETS_DIR

FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

def get_font(size: int, bold: bool = True):
    font_file = "segoeuib.ttf" if bold else "DMSerifDisplay-Regular.ttf"
    font_path = os.path.join(FONTS_DIR, font_file)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    # Fallback to standard
    candidates = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "arial.ttf"]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

def clean_text_for_pil(text: str) -> str:
    if not text:
        return ""
    # Pilmoji kullanılamadığı durumlarda font uyumsuzluğundaki kutucukları (tofu) önle
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[\u2600-\u27BF]', '', cleaned)
    return cleaned.strip()

def draw_text_with_emojis(img: Image.Image, draw: ImageDraw.ImageDraw, pos: tuple, text: str, font, fill, anchor: str = "mm"):
    """
    Pilmoji ile gerçek renkli emojileri metin içinde çizer.
    Pilmoji yoksa veya hata verirse emojileri temizleyerek standart PIL ile yazar.
    """
    try:
        from pilmoji import Pilmoji
        with Pilmoji(img) as p:
            p.text(pos, text, font=font, fill=fill, anchor=anchor)
    except Exception as e:
        safe_text = clean_text_for_pil(text)
        draw.text(pos, safe_text, font=font, fill=fill, anchor=anchor)

def create_story_card(deal: dict, output_path: str = None) -> str:
    """
    Instagram Story için 1080x1920 boyutunda, tıklanabilir link çıkartmasına tam uyumlu,
    yüksek dönüşümlü (high-conversion) dikey hikaye kartı üretir.
    Pilmoji ile tüm emojileri eksiksiz renkli basar ve dikey eleman çakışmalarını tamamen önler.
    """
    width, height = 1080, 1920
    out_file = output_path or os.path.join(TEMP_DIR, f"story_{int(deal.get('discount_val', 40))}_{os.path.basename(deal.get('image_path', 'prod.jpg'))}.jpg")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    # 1. Koyu Şık Arka Plan & Hafif Gradient
    img = Image.new("RGBA", (width, height), (15, 17, 21, 255))
    draw = ImageDraw.Draw(img)

    # Üst ve alt için hafif aydınlık daireler (Ambient Glow)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    # Sarı/Turuncu üst ışıma
    glow_draw.ellipse([-200, -200, 1280, 500], fill=(255, 170, 0, 30))
    # Mavi alt ışıma
    glow_draw.ellipse([-100, 1400, 1180, 2100], fill=(0, 130, 255, 25))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # 2. Üst Header: Killer Hook veya FLAŞ FIRSAT Rozeti
    killer = deal.get("killer_hook") or deal.get("feature_pill")
    header_text = killer if (killer and len(killer.strip()) > 3) else (deal.get("market_badge") or "⚡ GÜNÜN FLAŞ İNDİRİMİ ⚡")
    draw.rounded_rectangle([60, 80, 1020, 175], radius=24, fill=(28, 31, 38, 240), outline=(255, 200, 0, 200), width=3)
    header_font = get_font(38, bold=True)
    draw_text_with_emojis(img, draw, (width // 2, 128), header_text, font=header_font, fill=(255, 215, 0), anchor="mm")

    # 3. Ürün Görseli Kartı (Büyük, Ortalanmış, Beyaz Yuvarlak Kutu)
    # Boyut: 900x790px -> Dikey hizada alt bölümlere bol alan bırakır
    card_x1, card_y1 = 90, 205
    card_x2, card_y2 = 990, 995
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=36, fill=(255, 255, 255, 255))

    prod_img_path = deal.get("image_path")
    if prod_img_path and os.path.exists(prod_img_path):
        try:
            prod_raw = Image.open(prod_img_path).convert("RGBA")
            target_w = card_x2 - card_x1 - 80
            target_h = card_y2 - card_y1 - 100
            prod_raw.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            px = card_x1 + ((card_x2 - card_x1) - prod_raw.width) // 2
            py = card_y1 + ((card_y2 - card_y1) - prod_raw.height) // 2 + 10
            img.paste(prod_raw, (px, py), prod_raw)
        except Exception as e:
            print(f"[Story Card] Görsel yerleştirme hatası: {e}")

    # İndirim Rozeti (Görselin Sağ Üst Köşesinde)
    disc_text = str(deal.get("discount_pct", "-%40")).strip()
    draw.rounded_rectangle([card_x2 - 210, card_y1 + 25, card_x2 - 25, card_y1 + 95], radius=18, fill=(225, 29, 72), outline=(255, 255, 255), width=3)
    badge_font = get_font(44, bold=True)
    draw_text_with_emojis(img, draw, (card_x2 - 118, card_y1 + 60), disc_text, font=badge_font, fill=(255, 255, 255), anchor="mm")

    # Satıcı Rozeti (Sol Üst)
    seller = (deal.get("seller_badge") or deal.get("store_name", "Amazon TR")).upper()
    seller_font = get_font(26, bold=True)
    s_bbox = seller_font.getbbox(seller)
    s_w = (s_bbox[2] - s_bbox[0]) + 44
    draw.rounded_rectangle([card_x1 + 25, card_y1 + 25, card_x1 + 25 + s_w, card_y1 + 95], radius=16, fill=(15, 23, 42, 230))
    draw_text_with_emojis(img, draw, (card_x1 + 25 + s_w // 2, card_y1 + 60), seller, font=seller_font, fill=(56, 189, 248), anchor="mm")

    # Kupon Rozeti (Kart İçi Sol Alt - Varsa)
    coupon_str = str(deal.get("coupon_info", "")).strip()
    if coupon_str:
        cp_font = get_font(28, bold=True)
        cp_label = f"🎟️ {coupon_str} KUPON FIRSATI"
        cp_bbox = cp_font.getbbox(cp_label)
        cp_w = (cp_bbox[2] - cp_bbox[0]) + 44
        draw.rounded_rectangle([card_x1 + 25, card_y2 - 80, card_x1 + 25 + cp_w, card_y2 - 20], radius=16, fill=(234, 179, 8, 245), outline=(255, 255, 255), width=2)
        draw_text_with_emojis(img, draw, (card_x1 + 25 + cp_w // 2, card_y2 - 50), cp_label, font=cp_font, fill=(15, 23, 42), anchor="mm")

    # 4. Ürün Başlığı (Temiz 1 veya 2 Satır)
    title = deal.get("title", "Fırsat Ürünü")
    title_font = get_font(46, bold=True)
    words = title.split()
    line1 = " ".join(words[:6])
    line2 = " ".join(words[6:12]) if len(words) > 6 else ""
    
    if line2:
        draw_text_with_emojis(img, draw, (width // 2, 1045), line1, font=title_font, fill=(255, 255, 255), anchor="mm")
        draw_text_with_emojis(img, draw, (width // 2, 1098), line2, font=get_font(40, bold=True), fill=(203, 213, 225), anchor="mm")
    else:
        draw_text_with_emojis(img, draw, (width // 2, 1070), line1, font=title_font, fill=(255, 255, 255), anchor="mm")

    # 5. Fiyat Alanı (Ferah, Geniş, 1175 Merkezli)
    old_p = str(deal.get("old_price", "")).strip()
    new_p = str(deal.get("new_price", "")).strip()

    y_price = 1175
    if old_p and new_p:
        # Eski Fiyat (Üstü Çizili)
        old_font = get_font(42, bold=False)
        bbox = old_font.getbbox(old_p)
        ow = bbox[2] - bbox[0]
        draw_text_with_emojis(img, draw, (330, y_price), old_p, font=old_font, fill=(148, 163, 184), anchor="mm")
        draw.line([330 - ow//2 - 6, y_price, 330 + ow//2 + 6, y_price], fill=(239, 68, 68), width=4)

        # Yeni Fiyat (Büyük Yeşil / Neon)
        new_font = get_font(68, bold=True)
        draw_text_with_emojis(img, draw, (690, y_price), new_p, font=new_font, fill=(74, 222, 128), anchor="mm")
    else:
        new_font = get_font(72, bold=True)
        draw_text_with_emojis(img, draw, (width // 2, y_price), new_p or old_p, font=new_font, fill=(74, 222, 128), anchor="mm")

    # 6. Kupon veya Taksit/Kargo Bilgi Bandı (1245 - 1315, Çakışma Kesinlikle Yok!)
    inst_str = str(deal.get("installment", "")).strip()
    bank_font = get_font(32, bold=True)

    if coupon_str:
        info_text = f"🎟️ {coupon_str} Kupon İndirimi • Sayfada Kuponu İşaretleyin!"
        draw.rounded_rectangle([100, 1245, 980, 1315], radius=18, fill=(234, 179, 8, 45), outline=(250, 204, 21), width=2)
        draw_text_with_emojis(img, draw, (width // 2, 1280), info_text, font=bank_font, fill=(253, 224, 71), anchor="mm")
    elif inst_str:
        info_text = f"⚡ {inst_str} • Prime Teslimat"
        draw.rounded_rectangle([100, 1245, 980, 1315], radius=18, fill=(30, 41, 59, 220), outline=(56, 189, 248), width=2)
        draw_text_with_emojis(img, draw, (width // 2, 1280), info_text, font=bank_font, fill=(56, 189, 248), anchor="mm")
    else:
        info_text = "🔥 Günün Öne Çıkan Fırsatı • Stoklarla Sınırlı"
        draw.rounded_rectangle([100, 1245, 980, 1315], radius=18, fill=(30, 41, 59, 220), outline=(56, 189, 248), width=2)
        draw_text_with_emojis(img, draw, (width // 2, 1280), info_text, font=bank_font, fill=(56, 189, 248), anchor="mm")

    # 7. İnteraktif Hikaye Anketi Hedef Alanı (1350 - 1500)
    poll_y1, poll_y2 = 1350, 1500
    draw.rounded_rectangle([90, poll_y1, 990, poll_y2], radius=24, fill=(139, 92, 246, 25), outline=(167, 139, 250), width=2)
    poll_lbl_font = get_font(32, bold=True)
    poll_sub_font = get_font(26, bold=False)
    draw_text_with_emojis(img, draw, (width // 2, poll_y1 + 40), "🗳️ ANKET ÇIKARTMASI ALANI", font=poll_lbl_font, fill=(216, 180, 254), anchor="mm")
    draw_text_with_emojis(img, draw, (width // 2, poll_y1 + 95), "Sizce bu fiyata değer mi? [🔥 ALINIR] / [😴 DEĞMEZ]", font=poll_sub_font, fill=(243, 232, 255), anchor="mm")

    # 8. Tıklanabilir Link Çıkartması Hedef Alanı (1535 - 1715)
    sticker_y1, sticker_y2 = 1535, 1715
    draw.rounded_rectangle([90, sticker_y1, 990, sticker_y2], radius=28, fill=(234, 179, 8, 35), outline=(250, 204, 21), width=3)
    cta_title_font = get_font(38, bold=True)
    cta_sub_font = get_font(28, bold=False)
    cta_urg_font = get_font(26, bold=True)

    draw_text_with_emojis(img, draw, (width // 2, sticker_y1 + 42), "👇 BURAYA TIKLA & ÜRÜNE GİT 👇", font=cta_title_font, fill=(255, 255, 255), anchor="mm")
    draw_text_with_emojis(img, draw, (width // 2, sticker_y1 + 98), "Doğrudan indirimli resmi mağaza sayfası açılır", font=cta_sub_font, fill=(253, 224, 71), anchor="mm")
    draw_text_with_emojis(img, draw, (width // 2, sticker_y1 + 144), "🔥 FIRSATI KAÇIRMA • STOKLAR TÜKENEBİLİR", font=cta_urg_font, fill=(185, 28, 28), anchor="mm")

    # 9. En Alt Dipnot (1775)
    d_code = deal.get("deal_code", "")
    code_part = f" • KOD: {d_code}" if d_code else ""
    draw_text_with_emojis(img, draw, (width // 2, 1775), f"Flaş Fırsat (@flasfirsat.tr){code_part} • #işbirliği #reklam", font=get_font(26, bold=False), fill=(100, 116, 139), anchor="mm")

    # RGB'ye çevirip kaydet
    final_img = img.convert("RGB")
    final_img.save(out_file, "JPEG", quality=95)
    print(f"✅ [Story Composer] 1080x1920 Instagram Story Kartı Üretildi: {out_file}")
    return out_file

if __name__ == "__main__":
    sample = {
        "title": "Logitech G102 Lightsync RGB Oyuncu Faresi",
        "old_price": "1.299 TL",
        "new_price": "802 TL",
        "discount_pct": "-38%",
        "discount_val": 38,
        "net_cost": "",
        "seller_badge": "AMAZON TR RESMİ SATICI",
        "image_path": "temp/logitech_g102.jpg",
        "installment": "Peşin Fiyatına 3 Taksit x 267 TL"
    }
    create_story_card(sample, "temp/test_story_card.jpg")
