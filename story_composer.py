import os
import math
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
def clean_text_for_pil(text: str) -> str:
    if not text:
        return ""
    import re
    # 4-byte emojileri ve yazı tipi tarafından desteklenmeyen sembolleri (kutu [] karakterlerini) temizle
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[\u2600-\u27BF]', '', cleaned)
    return cleaned.strip()

def create_story_card(deal: dict, output_path: str = None) -> str:
    """
    Instagram Story için 1080x1920 boyutunda, tıklanabilir link çıkartmasına tam uyumlu,
    yüksek dönüşümlü (high-conversion) dikey hikaye kartı üretir.
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

    # 2. Üst Header: Logo & FLAŞ FIRSAT Rozeti (Varsa Akakçe Piyasa Rozeti)
    header_text = clean_text_for_pil(deal.get("market_badge") or "GÜNÜN FLAŞ İNDİRİMİ")
    draw.rounded_rectangle([60, 90, 1020, 200], radius=25, fill=(28, 31, 38, 240), outline=(255, 200, 0, 180), width=3)
    header_font = get_font(44, bold=True)
    draw.text((width // 2, 145), header_text, font=header_font, fill=(255, 215, 0), anchor="mm")

    # 3. Ürün Görseli Kartı (Büyük, Ortalanmış, Beyaz Yuvarlak Kutu)
    card_x1, card_y1 = 90, 240
    card_x2, card_y2 = 990, 1140
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=40, fill=(255, 255, 255, 255))

    prod_img_path = deal.get("image_path")
    if prod_img_path and os.path.exists(prod_img_path):
        try:
            prod_raw = Image.open(prod_img_path).convert("RGBA")
            target_w = card_x2 - card_x1 - 80
            target_h = card_y2 - card_y1 - 80
            prod_raw.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            px = card_x1 + ((card_x2 - card_x1) - prod_raw.width) // 2
            py = card_y1 + ((card_y2 - card_y1) - prod_raw.height) // 2
            img.paste(prod_raw, (px, py), prod_raw)
        except Exception as e:
            print(f"[Story Card] Görsel yerleştirme hatası: {e}")

    # İndirim Rozeti (Görselin Sağ Üst Köşesinde Patlayan Rozet)
    disc_text = clean_text_for_pil(deal.get("discount_pct", "-%40"))
    draw.rounded_rectangle([card_x2 - 220, card_y1 + 30, card_x2 - 30, card_y1 + 130], radius=20, fill=(225, 29, 72), outline=(255, 255, 255), width=3)
    badge_font = get_font(48, bold=True)
    draw.text((card_x2 - 125, card_y1 + 80), disc_text, font=badge_font, fill=(255, 255, 255), anchor="mm")

    # Satıcı Rozeti (Sol Üst - Otomatik Genişleyen ve Taşmayan Kutu)
    seller = clean_text_for_pil((deal.get("seller_badge") or deal.get("store_name", "Amazon TR")).upper())
    seller_font = get_font(28, bold=True)
    s_bbox = seller_font.getbbox(seller)
    s_w = (s_bbox[2] - s_bbox[0]) + 48
    draw.rounded_rectangle([card_x1 + 30, card_y1 + 30, card_x1 + 30 + s_w, card_y1 + 105], radius=18, fill=(15, 23, 42, 230))
    draw.text((card_x1 + 30 + s_w // 2, card_y1 + 68), seller, font=seller_font, fill=(56, 189, 248), anchor="mm")

    # 4. Ürün Başlığı (Alt Alan)
    title = clean_text_for_pil(deal.get("title", "Fırsat Ürünü"))
    title_font = get_font(52, bold=True)
    # 2 satıra böl
    words = title.split()
    line1 = " ".join(words[:5])
    line2 = " ".join(words[5:10]) if len(words) > 5 else ""
    draw.text((width // 2, 1200), line1, font=title_font, fill=(255, 255, 255), anchor="mm")
    if line2:
        draw.text((width // 2, 1265), line2, font=title_font, fill=(203, 213, 225), anchor="mm")

    # 5. Fiyat Alanı
    old_p = deal.get("old_price", "")
    new_p = deal.get("new_price", "")
    net_c = deal.get("net_cost", "")

    y_price = 1350
    if old_p and new_p:
        # Eski Fiyat (Üstü Çizili)
        old_font = get_font(44, bold=False)
        bbox = old_font.getbbox(old_p)
        ow = bbox[2] - bbox[0]
        draw.text((320, y_price), old_p, font=old_font, fill=(148, 163, 184), anchor="mm")
        draw.line([320 - ow//2 - 5, y_price, 320 + ow//2 + 5, y_price], fill=(239, 68, 68), width=4)

        # Yeni Fiyat (Büyük Yeşil / Neon)
        new_font = get_font(72, bold=True)
        draw.text((680, y_price), new_p, font=new_font, fill=(74, 222, 128), anchor="mm")
    else:
        new_font = get_font(76, bold=True)
        draw.text((width // 2, y_price), new_p or old_p, font=new_font, fill=(74, 222, 128), anchor="mm")

    # Banka/Nays Kampanyası (Varsa)
    if net_c:
        bank_font = get_font(38, bold=True)
        camp_text = clean_text_for_pil(f"Nays ile Net Fiyat: {net_c}")
        draw.rounded_rectangle([200, 1420, 880, 1490], radius=20, fill=(30, 41, 59, 220), outline=(56, 189, 248), width=2)
        draw.text((width // 2, 1455), camp_text, font=bank_font, fill=(56, 189, 248), anchor="mm")

    # 6. Tıklanabilir Link Çıkartması Hedef Alanı (En Kritik Çağrı)
    sticker_y1, sticker_y2 = 1550, 1750
    draw.rounded_rectangle([120, sticker_y1, 960, sticker_y2], radius=35, fill=(234, 179, 8, 30), outline=(250, 204, 21), width=4)
    cta_title_font = get_font(46, bold=True)
    cta_sub_font = get_font(34, bold=False)
    draw.text((width // 2, sticker_y1 + 55), "LİNKE TIKLAYARAK SATIN ALIN", font=cta_title_font, fill=(255, 255, 255), anchor="mm")
    draw.text((width // 2, sticker_y1 + 125), "Doğrudan indirimli resmi mağaza sayfası açılır", font=cta_sub_font, fill=(253, 224, 71), anchor="mm")

    # En Alt Dipnot
    draw.text((width // 2, 1840), "Flaş Fırsat • #işbirliği #reklam", font=get_font(28, bold=False), fill=(100, 116, 139), anchor="mm")

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
        "net_cost": "722 TL",
        "seller_badge": "AMAZON TR RESMİ SATICI",
        "image_path": "temp/logitech_g102.jpg"
    }
    create_story_card(sample, "temp/test_story_card.jpg")
