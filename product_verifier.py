import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from config import BASE_DIR, TEMP_DIR, get_curl_cmd, safe_run_subprocess
from price_tracker import record_price, check_if_lowest_30d

def extract_product_killer_hook(
    title: str,
    new_price: str,
    old_price: str = "",
    discount_pct: str = "",
    raw_specs: str = ""
) -> str:
    """
    Verilen indirimli e-ticaret ürününün o anki GERÇEK teknik/fiziksel özelliklerini ve satış fiyatını inceleyerek,
    kısa videoda izleyiciyi hemen yakalayacak, o ürüne ÖZGÜ tek satırlık VURUCU 'Killer Feature / Hook' üretir.
    Örn: '4.449 TL'YE 200Hz 0.5ms FAST IPS!' veya '1.000 TL ALTINA 2K 360° KAMERA!'
    """
    from deal_hunter import call_gemini
    prompt = f"""Sen viral kısa video (Reels, TikTok, Shorts) içerik üreticisisin.
Verilen indirimli e-ticaret ürününün o anki GERÇEK teknik/fiziksel özelliklerini ve satış fiyatını incele.
İzleyicinin videoda ilk saniyede görüp "Bu fiyata bu özellik inanılmaz!" diyerek dikkatini çekecek, o ürüne ÖZGÜ, EN VURUCU tek satırlık dikkat çekici başlığı yaz.

ZORUNLU KURALLAR:
1. YALNIZCA bu ürünün gerçek özelliklerini kullan (Asla başka bir ürünün özelliğini uydurma veya yazma!).
2. Ürünün en can alıcı 1 veya 2 teknik özelliğini, varsa fiyat avantajıyla vurucu şekilde birleştir.
3. Maksimum 35 karakter uzunluğunda olsun. Kısa, tok ve büyük harflerle vurucu olsun.
4. Başında veya sonunda gereksiz tırnak, emoji, ön ek veya açıklama olmasın. Sadece tek satır metni döndür.

Örnek Çıktılar:
- Kamera (999 TL): 1.000 TL ALTINA 2K 360° KAMERA!
- Monitör (4.449 TL): 4.449 TL'YE 200Hz 0.5ms FAST IPS!
- Mousepad (659 TL): 90x40 CM SU GEÇİRMEZ MİKRO DOKUMA!
- Airfryer (1.399 TL): 1.400 TL ALTINA 8L DİJİTAL AİRFRYER!

Ürün Başlığı: {title}
Satış Fiyatı: {new_price}
Eski Fiyat: {old_price}
İndirim Oranı: {discount_pct}
Ürün Detayları/Teknik Veriler:
{raw_specs[:600]}

SADECE tek satırlık vurucu başlığı döndür:"""
    try:
        summary = call_gemini(prompt, json_mode=False)
        if isinstance(summary, str) and summary.strip():
            clean = summary.strip().replace('"', '').replace("'", "").replace("\n", " ").strip()
            clean = re.sub(r'^[^\w\s%.,+/\-]+', '', clean).strip()
            if 5 <= len(clean) <= 45:
                return clean.upper()
    except Exception as e:
        print(f"[Verifier] Gemini killer hook üretme uyarısı: {e}")
    return ""

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

    html_text = ""
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9"
            },
            timeout=10
        )
        if r.status_code == 200:
            html_text = r.text
    except Exception:
        pass

    if not html_text:
        cmd = get_curl_cmd([
            "-s", "-L", "--compressed",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
            url
        ])
        res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        html_text = res.stdout

    out_low = html_text.lower()

    # 0. BOT / CAPTCHA KORUMASI TESPİTİ - 2. Deneme (Mobil User-Agent)
    captcha_indicators = [
        "type the characters you see in this image",
        "robot check",
        "girdiğiniz karakterleri doğrulayın",
        "automated access",
        "api-services-support@amazon.com",
        "validatecaptcha",
        "alışverişe devam etmek için",
        "alisverise devam etmek icin"
    ]
    if any(ind in out_low for ind in captcha_indicators):
        mobile_cmd = get_curl_cmd([
            "-s", "-L", "--compressed",
            "-H", "User-Agent: Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
            "-H", "Sec-CH-UA-Mobile: ?1",
            "-H", "Sec-CH-UA-Platform: \"Android\"",
            url
        ])
        res = safe_run_subprocess(mobile_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        html_text = res.stdout
        out_low = html_text.lower()

    if any(ind in out_low for ind in captcha_indicators):
        print(f"[Verifier] ⚠️ Amazon CAPTCHA / Bot Engeli Algılandı: {url}")
        return {
            "success": False,
            "in_stock": False,
            "is_captcha": True,
            "reason": "Amazon Bot Koruması / CAPTCHA",
            "feature_pill": "",
            "killer_hook": ""
        }

    if not html_text or len(html_text) < 3000:
        return {
            "success": False,
            "in_stock": False,
            "reason": "Sayfa yüklenemedi / Boş yanıt",
            "feature_pill": "",
            "killer_hook": ""
        }

    soup = BeautifulSoup(html_text, "html.parser")
    from deal_hunter import parse_price_to_float

    # 1. STOK KONTROLÜ
    avail_el = soup.select_one("#availability")
    avail_text = avail_el.text.strip().lower() if avail_el else ""
    out_of_stock_phrases = ["mevcut değil", "stokta yok", "tükendi", "currently unavailable", "geçici olarak temin edilemiyor"]
    in_stock = not any(phrase in avail_text for phrase in out_of_stock_phrases)

    # 2. CANLI SATIŞ FİYATI VE GERÇEK LİSTE/ÖNCEKİ FİYATI (Strike Price)
    price_el = (
        soup.select_one(".priceToPay") or
        soup.select_one("#corePriceDisplay_desktop_feature_div .a-price") or
        soup.select_one("#corePrice_desktop .a-price") or
        soup.select_one("#corePrice_feature_div .a-price") or
        soup.select_one(".apexPriceToPay .a-offscreen") or
        soup.select_one("#apex_desktop .a-price .a-offscreen") or
        soup.select_one("#priceblock_dealprice") or
        soup.select_one("#priceblock_ourprice") or
        soup.select_one(".a-price .a-offscreen")
    )
    live_price_str = price_el.text.strip().replace("\n", "").replace(" ", "") if price_el else ""
    price_val = parse_price_to_float(live_price_str)

    # Eğer doğrudan buybox yoksa ve sadece "Tüm Satın Alma Seçeneklerini Gör" varsa doğrudan fırsat stoğu tükenmiştir
    see_all = soup.select_one("#buybox-see-all-buying-choices, #all-offers-display")
    if (see_all or "tüm satın alma seçeneklerini gör" in out_low or "satın alma seçenekleri" in out_low) and price_val == 0.0:
        in_stock = False
        avail_text = "Tüm Satın Alma Seçenekleri (Doğrudan Fırsat/Stok Tükendi)"

    # Gerçek üstü çizili fiyat (Amazon'daki gerçek liste fiyatı)
    strike_el = (
        soup.select_one("#corePriceDisplay_desktop_feature_div .basisPrice .a-offscreen") or
        soup.select_one(".basisPrice .a-offscreen") or
        soup.select_one("#corePrice_desktop .basisPrice .a-offscreen")
    )
    real_strike_val = parse_price_to_float(strike_el.text) if strike_el else 0.0

    # 3. RESMİ SATICI / AMAZON TR ROZETİ KONTROLÜ
    merchant_el = soup.select_one("#merchant-info")
    merchant_text = merchant_el.text.lower() if merchant_el else ""
    is_sold_by_amazon = "amazon tarafından satılır" in merchant_text or "amazon.com.tr" in merchant_text
    
    if is_sold_by_amazon:
        seller_badge = "AMAZON TR RESMİ SATICI"
    elif "tarafından gönderilir" in merchant_text:
        seller_badge = "AMAZON GÖNDERİSİ GÜVENLİ SATICI"
    else:
        seller_badge = "AMAZON TR"

    # 4. KUPON İNDİRİMİ KONTROLÜ (Coupon Badge & Voucher)
    coupon_text = ""
    coupon_amount_tl = 0.0
    coupon_badge = soup.select_one(".promoPriceBlockMessage, #couponBadge, .couponBadge, span[id*='coupon']")
    if coupon_badge:
        coupon_text = coupon_badge.text.strip().replace("\n", " ")
        pct_m = re.search(r"%(\d+)", coupon_text)
        tl_m = re.search(r"(\d+[\.,]?\d*)\s*TL", coupon_text, re.IGNORECASE)
        if pct_m:
            coupon_amount_tl = round(price_val * (float(pct_m.group(1)) / 100.0), 2)
        elif tl_m:
            coupon_amount_tl = parse_price_to_float(tl_m.group(1))

    # 5.SOSYAL KANIT: YILDIZ PUANI, YORUM SAYISI & "GEÇEN AY X+ SATIN ALINDI" ETİKETİ
    rating_val = 0.0
    review_count = 0
    bought_past_month = ""
    try:
        rating_el = soup.select_one("#acrPopover, span[data-hook='rating-out-of-text'], i.a-icon-star span.a-icon-alt")
        if rating_el:
            r_text = (rating_el.get("title") or rating_el.text or "").strip().replace(",", ".")
            r_m = re.search(r"(\d\.\d)", r_text)
            if r_m:
                rating_val = float(r_m.group(1))
        rev_el = soup.select_one("#acrCustomerReviewText, span[data-hook='total-review-count']")
        if rev_el:
            rev_digits = re.sub(r"[^\d]", "", rev_el.text.strip())
            if rev_digits:
                review_count = int(rev_digits)
        bought_el = soup.select_one("#social-proofing-faceout-title-tk_bought span, span.social-proofing-faceout-title-text")
        if bought_el:
            bought_past_month = bought_el.text.strip()
    except Exception:
        pass

    # 6. GERÇEK ÜRETİCİ ÖZELLİK MADDELERİ (Bullet Points & Overview Table)
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

    # 7. GERÇEK VERİLERDEN TEK SATIRLIK VURUCU ÖZELLİK (Gemini)
    feature_pill = ""
    raw_specs = "\n".join(bullets[:4] + overview[:4])
    prod_title = soup.title.text if soup.title else ""
    if raw_specs or prod_title:
        feature_pill = extract_product_killer_hook(
            title=prod_title,
            new_price=live_price_str,
            old_price=f"{int(real_strike_val):,} TL".replace(',', '.') if real_strike_val else "",
            discount_pct="",
            raw_specs=raw_specs
        )

    # 8. ÜRÜN GÖRSELİ (Yüksek Çözünürlüklü)
    image_url = ""
    landing = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront") or soup.select_one("#main-image") or soup.select_one("#landingImageContainer img")
    if landing:
        image_url = landing.get("data-old-hires") or landing.get("src") or ""
        if not image_url and landing.get("data-a-dynamic-image"):
            try:
                dyn_dict = json.loads(landing.get("data-a-dynamic-image", "{}"))
                if dyn_dict:
                    image_url = list(dyn_dict.keys())[0]
            except Exception:
                pass
    if not image_url:
        og = soup.find("meta", property="og:image")
        if og:
            image_url = og.get("content", "")
    if image_url:
        image_url = re.sub(r'\._AC_.*?_\.', '._AC_SL1500_.', image_url)

    # 9. FİYAT GEÇMİŞİNİ KAYDET & SON 30 GÜN KONTROLÜ
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
        "image_url": image_url,
        "live_price_str": live_price_str,
        "live_price_val": price_val,
        "real_strike_val": real_strike_val,
        "seller_badge": seller_badge,
        "is_sold_by_amazon": is_sold_by_amazon,
        "coupon_text": coupon_text,
        "coupon_amount_tl": coupon_amount_tl,
        "rating": rating_val,
        "review_count": review_count,
        "bought_past_month": bought_past_month,
        "feature_pill": feature_pill,
        "killer_hook": feature_pill,
        "is_lowest_30d": is_lowest_30d
    }

def verify_deal_before_publish(deal: dict) -> dict:
    """
    Video üretimi veya Telegram paylaşımı öncesi fırsatın son kontrolünü yapar.
    Stok bitmişse, erişim engellenmişse, puanı düşükse veya fiyat aşırı yükselmişse paylaşımı durdurur.
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
                if not deal.get("killer_hook"):
                    k_hook = extract_product_killer_hook(
                        title=deal.get("title", ""),
                        new_price=deal.get("new_price", ""),
                        old_price=deal.get("old_price", ""),
                        discount_pct=deal.get("discount_pct", "")
                    )
                    if k_hook:
                        deal["killer_hook"] = k_hook
                        deal["feature_pill"] = k_hook
                return {"valid": True, "verified": True, "deal": deal}

            print(f"[Doğrulama] ❌ ÜRÜN YAYINA UYGUN DEĞİL! ({reason}). Paylaşım iptal ediliyor.")
            return {"valid": False, "verified": False, "reason": reason}

        # Canlı Sosyal Kanıt & Kalite Barajı (Düşük yıldızlı veya yorumsuz fason ürünleri ele)
        live_rating = v_res.get("rating", 0.0)
        live_reviews = v_res.get("review_count", 0)
        if live_rating > 0:
            deal["rating"] = live_rating
        if live_reviews > 0:
            deal["review_count"] = live_reviews
        if v_res.get("bought_past_month"):
            deal["bought_past_month"] = v_res["bought_past_month"]
            print(f"[Doğrulama] 🔥 Canlı Satış Hızı: {v_res['bought_past_month']}")

        if live_rating > 0 and live_rating < 4.0:
            print(f"[Doğrulama] ❌ DÜŞÜK YILDIZ PUANI ({live_rating}⭐ < 4.0⭐)! Kalitesiz ürün koruması devrede, paylaşım iptal ediliyor.")
            return {"valid": False, "reason": f"Yıldız puanı çok düşük ({live_rating}⭐)"}

        from deal_hunter import has_tier1_brand
        if not has_tier1_brand(deal.get("title", "")) and live_reviews > 0 and live_reviews < 10:
            print(f"[Doğrulama] ❌ YETERSİZ SOSYAL KANIT (Bilinmeyen marka ve sadece {live_reviews} yorum)! Paylaşım iptal ediliyor.")
            return {"valid": False, "reason": f"Yetersiz yorum sayısı ({live_reviews} yorum)"}

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

        # Canlı özellik özeti / Killer Hook varsa ekle
        if v_res.get("killer_hook") or v_res.get("feature_pill"):
            hook = v_res.get("killer_hook") or v_res.get("feature_pill")
            deal["feature_pill"] = hook
            deal["killer_hook"] = hook
            print(f"[Doğrulama] ✨ Gerçek Ürün Özelliği / Killer Hook: {hook}")
        elif not deal.get("killer_hook"):
            k_hook = extract_product_killer_hook(
                title=deal.get("title", ""),
                new_price=deal.get("new_price", ""),
                old_price=deal.get("old_price", ""),
                discount_pct=deal.get("discount_pct", "")
            )
            if k_hook:
                deal["killer_hook"] = k_hook
                deal["feature_pill"] = k_hook
                print(f"[Doğrulama] ✨ Dinamik Killer Hook Üretildi: {k_hook}")

        # Canlı ürün görseli kontrolü ve otomatik indirme
        if v_res.get("image_url"):
            deal["image_url"] = v_res["image_url"]
            if not deal.get("image_path") or not os.path.exists(deal.get("image_path", "")):
                from config import download_file
                p_asin = v_res.get("asin") or "prod"
                img_path = os.path.join(TEMP_DIR, f"amz_{p_asin}.jpg")
                if download_file(v_res["image_url"], img_path):
                    deal["image_path"] = img_path
                    print(f"[Doğrulama] 📸 Canlı ürün görseli indirildi: {img_path}")

        # 30 günün en düşüğü kontrolü
        deal["is_lowest_30d"] = v_res.get("is_lowest_30d", False)
        if deal["is_lowest_30d"]:
            print(f"[Doğrulama] 📉 Veritabanında Son 30 Günün En Düşük Fiyatı Doğrulandı!")

    return {"valid": True, "verified": True, "deal": deal}
