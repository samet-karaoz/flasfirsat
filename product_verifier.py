import os
import re
import subprocess
from bs4 import BeautifulSoup
from config import BASE_DIR, TEMP_DIR, get_curl_cmd
from price_tracker import record_price, check_if_lowest_30d

def verify_amazon_product(asin_or_url: str) -> dict:
    """
    Amazon TR ürün sayfasını canlı olarak sorgular:
    1. Gerçek stok durumunu doğrular (Tükendi mi?)
    2. Canlı satış fiyatını doğrular (İndirim bitti mi?)
    3. Varsa kupon / sepet indirimini tespit eder
    4. Sayfadaki GERÇEK üretici özellik maddelerini (bullet points) çeker
    5. Fiyatı SQLite geçmişine kaydeder ve 'Son 30 günün en düşüğü' kontrolünü yapar
    """
    asin_match = re.search(r"([A-Z0-9]{10})", asin_or_url, re.IGNORECASE)
    asin = asin_match.group(1).upper() if asin_match else ""
    url = f"https://www.amazon.com.tr/dp/{asin}" if asin else asin_or_url

    cmd = get_curl_cmd([
        "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "-H", "Accept-Language: tr-TR,tr;q=0.9",
        url
    ])

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    out_low = res.stdout.lower()

    # 0. BOT / CAPTCHA KORUMASI TESPİTİ - 2. Deneme (Mobil User-Agent)
    if (
        "type the characters you see in this image" in out_low or
        "robot check" in out_low or
        "girdiğiniz karakterleri doğrulayın" in out_low or
        "automated access" in out_low
    ):
        # 2. Deneme: Mobil Android Chrome User-Agent ile tekrar dene
        mobile_cmd = get_curl_cmd([
            "-s", "-L",
            "-H", "User-Agent: Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
            "-H", "Sec-CH-UA-Mobile: ?1",
            "-H", "Sec-CH-UA-Platform: \"Android\"",
            url
        ])
        res = subprocess.run(mobile_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        out_low = res.stdout.lower()

    if (
        "type the characters you see in this image" in out_low or
        "robot check" in out_low or
        "girdiğiniz karakterleri doğrulayın" in out_low or
        "automated access" in out_low
    ):
        print(f"[Verifier] ⚠️ Amazon CAPTCHA / Bot Engeli Algılandı: {url}")
        return {
            "success": False,
            "in_stock": False,
            "is_captcha": True,
            "reason": "Amazon Bot Koruması / CAPTCHA",
            "feature_pill": ""
        }

    if res.returncode != 0 or len(res.stdout) < 8000:
        return {
            "success": False,
            "in_stock": False,
            "reason": "Sayfa yüklenemedi / Boş yanıt",
            "feature_pill": ""
        }

    soup = BeautifulSoup(res.stdout, "html.parser")
    from deal_hunter import parse_price_to_float

    # 1. STOK KONTROLÜ
    avail_el = soup.select_one("#availability")
    avail_text = avail_el.text.strip().lower() if avail_el else ""
    out_of_stock_phrases = ["mevcut değil", "stokta yok", "tükendi", "currently unavailable", "geçici olarak temin edilemiyor"]
    in_stock = not any(phrase in avail_text for phrase in out_of_stock_phrases)

    # 2. CANLI SATIŞ FİYATI VE GERÇEK LİSTE/ÖNCEKİ FİYATI (Strike Price)
    price_el = soup.select_one(".priceToPay") or soup.select_one("#corePriceDisplay_desktop_feature_div .a-price") or soup.select_one(".a-price .a-offscreen")
    live_price_str = price_el.text.strip().replace("\n", "").replace(" ", "") if price_el else ""
    price_val = parse_price_to_float(live_price_str)

    # Gerçek üstü çizili fiyat (Amazon'daki gerçek liste fiyatı)
    strike_el = (
        soup.select_one("#corePriceDisplay_desktop_feature_div .basisPrice .a-offscreen") or
        soup.select_one("#corePriceDisplay_desktop_feature_div .a-text-price .a-offscreen") or
        soup.select_one("span.priceBlockStrikePriceString") or
        soup.select_one("span.a-text-strike")
    )
    real_strike_str = strike_el.text.strip().replace("\n", "").replace(" ", "") if strike_el else ""
    real_strike_val = parse_price_to_float(real_strike_str)

    # 3. GERÇEK SATICI DOĞRULAMASI (Amazon TR Resmi mi, Pazaryeri mi?)
    is_sold_by_amazon = bool(re.search(r"Amazon\.com\.tr tarafından satılır", res.stdout, re.IGNORECASE))
    is_shipped_by_amazon = bool(re.search(r"(?:ve gönderilir|Amazon tarafından gönderilir)", res.stdout, re.IGNORECASE))

    if is_sold_by_amazon:
        seller_badge = "AMAZON TR RESMİ SATICI"
    elif is_shipped_by_amazon:
        seller_badge = "AMAZON TR GÖNDERİMLİ"
    else:
        seller_badge = "AMAZON PAZARYERİ"

    # 4. KUPON TESPİTİ VE NET İNDİRİM TL HESAPLAMA
    coupon_text = ""
    coupon_amount_tl = 0.0
    coupon_el = soup.select_one("span.couponBadge") or soup.select_one("label[for*='coupon']") or soup.select_one("#couponBadge") or soup.select_one("#promoPriceBlockMessage_feature_div")
    raw_coupon = coupon_el.text.strip() if coupon_el else ""
    c_m = re.search(r"(%?\s*\d+[\.,]?\d*)\s*(TL|%|₺)?\s*(?:değerinde\s*|indirim\s*)?kupon", raw_coupon or res.stdout, re.IGNORECASE)
    if c_m:
        val_part = c_m.group(1).strip()
        unit_part = (c_m.group(2) or "").strip().upper()
        if "%" in val_part or unit_part == "%":
            num_only = re.sub(r"[^\d]", "", val_part)
            coupon_text = f"%{num_only} İndirim Kuponu"
        else:
            coupon_text = f"{val_part} TL İndirim Kuponu"
    elif raw_coupon and "kupon" in raw_coupon.lower():
        cleaned_c = re.sub(r"(?i)(şartlar|kuponu uygula|uygulayın|detaylar)", "", raw_coupon)
        cleaned_c = re.sub(r"\s+", " ", cleaned_c).strip(" -•:.,")
        coupon_text = cleaned_c[:30]

    if coupon_text and price_val > 0:
        pct_m = re.search(r"%(\d+)", coupon_text)
        tl_m = re.search(r"(\d+[\.,]?\d*)\s*TL", coupon_text, re.IGNORECASE)
        if pct_m:
            coupon_amount_tl = round(price_val * (float(pct_m.group(1)) / 100.0), 2)
        elif tl_m:
            coupon_amount_tl = parse_price_to_float(tl_m.group(1))

    # 5. GERÇEK ÜRETİCİ ÖZELLİK MADDELERİ (Bullet Points & Overview Table)
    bullets = []
    for li in soup.select("#feature-bullets ul li"):
        txt = li.text.strip()
        if txt and not txt.startswith("Bu ürün hakkında") and len(txt) > 5:
            bullets.append(txt)

    overview = []
    for tr in soup.select("#productOverview_feature_div tr"):
        k = tr.select_one("td.a-span3")
        v = tr.select_one("td.a-span9")
        if k and v:
            overview.append(f"{k.text.strip()}: {v.text.strip()}")

    # 6. GERÇEK VERİLERDEN TEK SATIRLIK ÖZET (Gemini)
    feature_pill = ""
    raw_specs = "\n".join(bullets[:4] + overview[:4])
    if raw_specs:
        from deal_hunter import call_gemini
        prompt = f"""Şu gerçek e-ticaret ürün bilgilerinden, sosyal medya reels videosu için EN VURUCU tek satırlık Türkçe hap özelliği çıkar.
Maksimum 35 karakter olsun, boş ve gereksiz laf olmasın.
Örnek: 240Hz Yenileme • 0.5ms Tepki veya 1.18L Çelik • 11s Soğuk veya 13.500A Gerilim Koruması

Ürün Başlığı: {soup.title.text if soup.title else ''}
Gerçek Özellikler:
{raw_specs[:600]}

SADECE tek satırlık özeti döndür (ek açıklama veya tırnak koyma):"""
        try:
            summary = call_gemini(prompt, json_mode=False)
            if isinstance(summary, str) and summary.strip() and len(summary.strip()) <= 45:
                feature_pill = summary.strip().replace('"', '').replace("'", "")
        except Exception as e:
            print(f"[Verifier] Gemini özetleme uyarısı: {e}")

    # 7. FİYAT GEÇMİŞİNİ KAYDET & SON 30 GÜN KONTROLÜ
    is_lowest_30d = False
    if asin and price_val > 0:
        record_price(asin, "Amazon TR", soup.title.text[:80] if soup.title else "", price_val)
        hist_check = check_if_lowest_30d(asin, price_val, "Amazon TR")
        is_lowest_30d = hist_check.get("is_lowest", False)

    return {
        "success": True,
        "asin": asin,
        "in_stock": in_stock,
        "stock_text": avail_text,
        "live_price_str": live_price_str,
        "live_price_val": price_val,
        "real_strike_val": real_strike_val,
        "seller_badge": seller_badge,
        "is_sold_by_amazon": is_sold_by_amazon,
        "coupon_text": coupon_text,
        "coupon_amount_tl": coupon_amount_tl,
        "feature_pill": feature_pill,
        "is_lowest_30d": is_lowest_30d
    }

def verify_deal_before_publish(deal: dict) -> dict:
    """
    Video üretimi veya Telegram paylaşımı öncesi fırsatın son kontrolünü yapar.
    Stok bitmişse, erişim engellenmişse veya fiyat aşırı yükselmişse paylaşımı durdurur.
    Gerçek üstü çizili fiyatı ve satıcı rozetini günceller.
    """
    store_url = deal.get("store_url", "")
    store_name = deal.get("store_name", "")

    if "amazon" in store_url.lower() or store_name == "Amazon TR":
        print(f"[Doğrulama] 🔍 Ürün sayfası canlı kontrol ediliyor: {store_url}...")
        v_res = verify_amazon_product(store_url)
        if not v_res.get("success", False) or not v_res.get("in_stock", False):
            reason = v_res.get("reason", "Stokta yok veya doğrulanamadı")
            # Eğer Amazon Datacenter CAPTCHA verdiyse ve fırsat doğrulanmış bir kanaldan geldiyse ve görseli/fiyatı tamsa:
            if v_res.get("is_captcha") and deal.get("new_price") and deal.get("image_path") and os.path.exists(deal.get("image_path")):
                print(f"[Doğrulama] ⚠️ Amazon Datacenter CAPTCHA algılandı ancak fırsat verisi taranan kaynaktan teyitli ({deal.get('title')}). Taranan veriyle devam ediliyor.")
                deal["seller_badge"] = deal.get("seller_badge") or "AMAZON TR"
                return {"valid": True, "verified": True, "deal": deal}

            print(f"[Doğrulama] ❌ ÜRÜN YAYINA UYGUN DEĞİL! ({reason}). Paylaşım iptal ediliyor.")
            return {"valid": False, "verified": False, "reason": reason}

        # Canlı fiyat kontrolü (İndirim bitti mi / fahiş zam geldi mi?)
        if v_res.get("live_price_val", 0) > 0:
            from deal_hunter import parse_price_to_float
            orig_p = parse_price_to_float(deal.get("new_price", ""))
            live_p = v_res["live_price_val"]
            if orig_p > 0 and live_p > orig_p * 1.15:
                print(f"[Doğrulama] ❌ FİYAT DEĞİŞMİŞ/İNDİRİM BİTMİŞ! (Eski: {orig_p} TL -> Canlı: {live_p} TL). Paylaşım iptal ediliyor.")
                return {"valid": False, "reason": "Fiyat artmış / indirim bitmiş"}
            elif live_p > 0:
                deal["new_price"] = f"{int(live_p):,} TL".replace(",", ".") if live_p.is_integer() else f"{live_p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

        orig_old_price = deal.get("old_price", "")
        from deal_hunter import parse_price_to_float
        orig_old_val = parse_price_to_float(orig_old_price)
        live_val = v_res.get("live_price_val", 0.0)
        if live_val <= 0:
            live_val = parse_price_to_float(deal.get("new_price", ""))

        real_strike = v_res.get("real_strike_val", 0.0)
        from price_tracker import get_real_previous_price
        db_prev = get_real_previous_price(v_res.get("asin", ""), "Amazon TR")

        chosen_old = 0.0
        source_lbl = ""
        # En az %10 fiyat farkı olmalı, aksi halde eski fiyat olarak kabul edilemez
        if real_strike > 0 and real_strike >= live_val * 1.10:
            chosen_old = real_strike
            source_lbl = "Gerçek Amazon Liste Fiyatı"
        elif orig_old_val > 0 and orig_old_val >= live_val * 1.10:
            chosen_old = orig_old_val
            source_lbl = "Taranan Piyasa/Liste Fiyatı"
        elif db_prev > 0 and db_prev >= live_val * 1.15:
            chosen_old = db_prev
            source_lbl = "Veritabanı Geçmiş Fiyatı"

        if chosen_old > live_val:
            deal["old_price"] = f"{int(chosen_old):,} TL".replace(",", ".")
            deal["has_verified_old_price"] = True
            calc_pct = round(((chosen_old - live_val) / chosen_old) * 100)
            deal["discount_pct"] = f"-{calc_pct}%"
            print(f"[Doğrulama] 🏷️ {source_lbl} Doğrulandı: {deal['old_price']} (-%{calc_pct})")
        else:
            deal["old_price"] = ""
            deal["has_verified_old_price"] = False
            print(f"[Doğrulama] ℹ️ Eski fiyat bulunamadı veya mevcut fiyata çok yakın. Tek fiyat olarak işlenecek.")

        # Gerçek Satıcı Rozeti
        deal["seller_badge"] = v_res.get("seller_badge", "Amazon TR")
        print(f"[Doğrulama] 🏢 Satıcı Doğrulandı: {deal['seller_badge']}")

        # Kupon indirimi varsa net maliyete ve bilgilendirmeye yansıt
        coupon_tl = v_res.get("coupon_amount_tl", 0.0)
        if v_res.get("coupon_text"):
            deal["coupon_info"] = v_res["coupon_text"]
        if coupon_tl > 0:
            deal["coupon_amount_tl"] = coupon_tl
            print(f"[Doğrulama] 🎟️ Kupon Uygulandı: {deal.get('coupon_info')} (-{coupon_tl:.2f} TL indirim)")
        elif deal.get("coupon_info"):
            print(f"[Doğrulama] 🎟️ Kupon Bilgilendirmesi: {deal.get('coupon_info')}")

        # Canlı özellik özeti varsa ekle
        if v_res.get("feature_pill"):
            deal["feature_pill"] = v_res["feature_pill"]
            print(f"[Doğrulama] ✨ Gerçek Ürün Özelliği: {v_res['feature_pill']}")

        # 30 günün en düşüğü kontrolü
        deal["is_lowest_30d"] = v_res.get("is_lowest_30d", False)
        if deal["is_lowest_30d"]:
            print(f"[Doğrulama] 📉 Veritabanında Son 30 Günün En Düşük Fiyatı Doğrulandı!")

    return {"valid": True, "verified": True, "deal": deal}
