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
    if res.returncode != 0 or len(res.stdout) < 5000:
        return {
            "success": False,
            "in_stock": True,
            "reason": "Sayfa tam çekilemedi",
            "feature_pill": ""
        }

    soup = BeautifulSoup(res.stdout, "html.parser")

    # 1. STOK KONTROLÜ
    avail_el = soup.select_one("#availability")
    avail_text = avail_el.text.strip().lower() if avail_el else ""
    out_of_stock_phrases = ["mevcut değil", "stokta yok", "tükendi", "currently unavailable", "geçici olarak temin edilemiyor"]
    in_stock = not any(phrase in avail_text for phrase in out_of_stock_phrases)

    # 2. CANLI FİYAT TESPİTİ
    price_el = soup.select_one(".priceToPay") or soup.select_one("#corePriceDisplay_desktop_feature_div .a-price") or soup.select_one(".a-price .a-offscreen")
    live_price_str = price_el.text.strip().replace("\n", "").replace(" ", "") if price_el else ""

    # 3. KUPON TESPİTİ
    coupon_text = ""
    coupon_el = soup.select_one("span.couponBadge") or soup.select_one("label[for*='coupon']") or soup.select_one("#couponBadge")
    if coupon_el:
        coupon_text = coupon_el.text.strip()
    else:
        c_m = re.search(r"(\d+[\.,]?\d*)\s*(TL|%)\s*(değerinde\s*)?kupon", res.stdout, re.IGNORECASE)
        if c_m:
            coupon_text = f"{c_m.group(1)} {c_m.group(2)} Kupon Fırsatı"

    # 4. GERÇEK ÜRETİCİ ÖZELLİK MADDELERİ (Bullet Points & Overview Table)
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

    # 5. GERÇEK VERİLERDEN TEK SATIRLIK ÖZET (Gemini)
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

    # 6. FİYAT GEÇMİŞİNİ KAYDET & SON 30 GÜN KONTROLÜ
    from deal_hunter import parse_price_to_float
    price_val = parse_price_to_float(live_price_str)
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
        "coupon_text": coupon_text,
        "feature_pill": feature_pill,
        "is_lowest_30d": is_lowest_30d
    }

def verify_deal_before_publish(deal: dict) -> dict:
    """
    Video üretimi veya Telegram paylaşımı öncesi fırsatın son kontrolünü yapar.
    Stok bitmişse veya fiyat aşırı yükselmişse paylaşımı durdurur.
    """
    store_url = deal.get("store_url", "")
    store_name = deal.get("store_name", "")

    if "amazon" in store_url.lower() or store_name == "Amazon TR":
        print(f"[Doğrulama] 🔍 Ürün sayfası canlı kontrol ediliyor: {store_url}...")
        v_res = verify_amazon_product(store_url)
        if not v_res.get("in_stock", True):
            print(f"[Doğrulama] ❌ ÜRÜN STOKTA YOK! ({v_res.get('stock_text')}). Paylaşım iptal ediliyor.")
            return {"valid": False, "reason": "Stokta yok"}

        # Canlı fiyat kontrolü (İndirim bitti mi / fahiş zam geldi mi?)
        if v_res.get("live_price_val", 0) > 0:
            from deal_hunter import parse_price_to_float
            orig_p = parse_price_to_float(deal.get("new_price", ""))
            live_p = v_res["live_price_val"]
            if orig_p > 0 and live_p > orig_p * 1.15:
                print(f"[Doğrulama] ❌ FİYAT DEĞİŞMİŞ/İNDİRİM BİTMİŞ! (Eski: {orig_p} TL -> Canlı: {live_p} TL). Paylaşım iptal ediliyor.")
                return {"valid": False, "reason": "Fiyat artmış / indirim bitmiş"}
            elif orig_p > 0 and live_p > 0 and abs(live_p - orig_p) > 1.0:
                deal["new_price"] = f"{int(live_p):,} TL".replace(",", ".") if live_p.is_integer() else f"{live_p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

        # Canlı özellik özeti varsa anlaşmaya ekle
        if v_res.get("feature_pill"):
            deal["feature_pill"] = v_res["feature_pill"]
            print(f"[Doğrulama] ✨ Gerçek Ürün Özelliği Doğrulandı: {v_res['feature_pill']}")

        # Kupon varsa ekle
        if v_res.get("coupon_text"):
            deal["coupon_info"] = v_res["coupon_text"]
            print(f"[Doğrulama] 🎟️ Kupon Fırsatı Tespit Edildi: {v_res['coupon_text']}")

        # Gerçek 30 günün en düşüğü doğrulandı mı?
        deal["is_lowest_30d"] = v_res.get("is_lowest_30d", False)
        if deal["is_lowest_30d"]:
            print(f"[Doğrulama] 📉 Veritabanında Son 30 Günün En Düşük Fiyatı Doğrulandı!")

    return {"valid": True, "deal": deal}
