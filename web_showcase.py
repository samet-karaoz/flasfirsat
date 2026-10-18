import os
import json
import shutil
from datetime import datetime
from config import BASE_DIR, ASSETS_DIR, GA_MEASUREMENT_ID, SITE_URL, safe_run_subprocess

# GitHub Pages ve vitrin dosyaları kök dizinde barındırılır
WEB_DIR = BASE_DIR

WEB_DATA_DIR = os.path.join(WEB_DIR, "data")
WEB_ASSETS_DIR = os.path.join(WEB_DIR, "assets")
WEB_IMG_DIR = os.path.join(WEB_ASSETS_DIR, "products")
DEALS_JSON_PATH = os.path.join(WEB_DATA_DIR, "deals.json")

def ensure_web_setup():
    """Web dizini ve gerekli dosyaların varlığını sağlar."""
    os.makedirs(WEB_DIR, exist_ok=True)
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    os.makedirs(WEB_ASSETS_DIR, exist_ok=True)
    os.makedirs(WEB_IMG_DIR, exist_ok=True)

    # Logoyu kopyala
    logo_src = os.path.join(ASSETS_DIR, "logo.jpg")
    logo_dst = os.path.join(WEB_ASSETS_DIR, "logo.jpg")
    if os.path.exists(logo_src) and not os.path.exists(logo_dst):
        shutil.copy2(logo_src, logo_dst)

    # CNAME ve robots.txt dosyalarını her zaman koru (Custom Domain & SEO)
    cname_path = os.path.join(WEB_DIR, "CNAME")
    if not os.path.exists(cname_path):
        with open(cname_path, "w", encoding="utf-8") as f:
            f.write("flasfirsat.com.tr\n")

    robots_path = os.path.join(WEB_DIR, "robots.txt")
    if not os.path.exists(robots_path):
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\nSitemap: https://flasfirsat.com.tr/sitemap.xml\n")

    if not os.path.exists(DEALS_JSON_PATH):
        with open(DEALS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def _ensure_deal_codes(deals: list) -> bool:
    """Tüm ürünlerin #101, #102 gibi benzersiz bir Fırsat Koduna sahip olmasını sağlar."""
    import re
    max_num = 100
    for d in deals:
        c = str(d.get("deal_code", "")).strip()
        m = re.search(r"(\d+)", c)
        if m:
            max_num = max(max_num, int(m.group(1)))

    changed = False
    # Eski ürünlerden başlayarak kodu olmayanlara sırayla ata
    for d in reversed(deals):
        if not d.get("deal_code"):
            max_num += 1
            d["deal_code"] = f"#{max_num}"
            changed = True
    return changed

def load_deals() -> list:
    ensure_web_setup()
    if os.path.exists(DEALS_JSON_PATH):
        try:
            with open(DEALS_JSON_PATH, "r", encoding="utf-8") as f:
                deals = json.load(f)
            if isinstance(deals, list) and _ensure_deal_codes(deals):
                save_deals(deals)
            return deals
        except Exception:
            return []
    return []

def save_deals(deals: list):
    ensure_web_setup()
    with open(DEALS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)

def get_next_deal_code(deals: list = None) -> str:
    """Sıradaki yeni ürün için #1XX fırsat kodunu döndürür."""
    import re
    if deals is None:
        deals = load_deals()
    max_num = 100
    for d in deals:
        c = str(d.get("deal_code", "")).strip()
        m = re.search(r"(\d+)", c)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"#{max_num + 1}"

def add_deal_to_web(deal: dict):
    """
    Yeni fırsatı web sitesi veritabanına ekler ve index.html'i yeniden derler.
    """
    if (
        str(deal.get("old_price", "")).strip() == "Çoklu Ürün"
        or "Top 3" in str(deal.get("new_price", ""))
        or "Top 3" in str(deal.get("title", ""))
    ):
        render_web_html()
        return

    ensure_web_setup()
    deals = load_deals()

    # Ürün resmini web dizinine her ürün için benzersiz bir isimle kopyala
    img_path = deal.get("image_path", "")
    web_img_rel = ""
    if img_path and os.path.exists(img_path):
        import hashlib, re
        title_slug = re.sub(r'[^a-zA-Z0-9]', '_', deal.get("title", "product")).strip('_')[:25].lower()
        unique_hash = hashlib.md5((deal.get("store_url", "") + deal.get("title", "")).encode('utf-8')).hexdigest()[:8]
        ext = os.path.splitext(img_path)[1] or ".jpg"
        unique_fname = f"{title_slug}_{unique_hash}{ext}"
        dst_img = os.path.join(WEB_IMG_DIR, unique_fname)
        shutil.copy2(img_path, dst_img)
        web_img_rel = f"assets/products/{unique_fname}"

    from campaign_calculator import calculate_campaign_and_net_cost
    camp_info = calculate_campaign_and_net_cost(deal.get("new_price", ""), deal.get("store_name", "Amazon TR"))
    bank_camp = deal.get("bank_campaign") or camp_info["bank_campaign"]
    installment = deal.get("installment") or camp_info.get("installment", "Peşin Fiyatına 3 Taksit")
    coupon_info = deal.get("coupon_info", "")

    # Otomatik Kategori Sınıflandırması
    t_low = (deal.get("title", "")).lower()
    if 'monitör' in t_low or 'monitor' in t_low:
        cat = 'monitor'
    elif any(k in t_low for k in ['mouse', 'fare', 'kulakl', 'headset', 'gamepad', 'kol', 'mousepad', 'espor', 'gaming', 'oyuncu']):
        cat = 'gaming'
    elif any(k in t_low for k in ['bellek', 'usb', 'ssd', 'ram', 'playstation', 'ps5', 'konsol']):
        cat = 'hardware'
    elif any(k in t_low for k in ['termos', 'stanley', 'kahve', 'filtre', 'mutfak', 'kolu', 'f80']):
        cat = 'lifestyle'
    else:
        cat = 'general'

    import re
    store_url_val = deal.get("affiliate_url") or deal.get("store_url", "#")
    new_url_clean = store_url_val.split("?")[0].strip().lower()
    new_asin_m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", store_url_val, re.IGNORECASE)
    new_asin = new_asin_m.group(1).upper() if new_asin_m else ""

    existing_idx = None
    existing_code = deal.get("deal_code", "")
    for i, d in enumerate(deals):
        d_title = d.get("title", "")
        d_url = d.get("store_url", "")
        d_url_clean = d_url.split("?")[0].strip().lower()
        if d_title == deal.get("title", ""):
            existing_idx = i
            existing_code = existing_code or d.get("deal_code", "")
            break
        if new_url_clean and new_url_clean != "#" and d_url_clean == new_url_clean:
            existing_idx = i
            existing_code = existing_code or d.get("deal_code", "")
            break
        if new_asin and new_asin.lower() in d_url.lower():
            existing_idx = i
            existing_code = existing_code or d.get("deal_code", "")
            break

    deal_code = existing_code or get_next_deal_code(deals)
    deal["deal_code"] = deal_code

    deal_item = {
        "id": f"deal_{int(datetime.now().timestamp())}_{len(deals)}",
        "deal_code": deal_code,
        "title": deal.get("title", "Fırsat Ürünü"),
        "old_price": deal.get("old_price", ""),
        "new_price": deal.get("new_price", ""),
        "discount_pct": deal.get("discount_pct", ""),
        "store_name": deal.get("store_name", "Amazon TR"),
        "store_url": store_url_val,
        "bank_campaign": bank_camp,
        "net_cost": "",
        "installment": installment,
        "coupon_info": coupon_info,
        "category": cat,
        "image_url": web_img_rel,
        "is_expired": False,
        "expired_reason": "",
        "date_added": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

    if existing_idx is not None:
        deals.pop(existing_idx)
    deals.insert(0, deal_item)

    # Maksimum 100 ürün sakla
    deals = deals[:100]
    save_deals(deals)

    # HTML'i güncelle
    render_web_html(deals)
    print(f"[Web] 🌐 Web vitrini güncellendi: {deal_item['title']}")
    push_to_github()

def remove_deal_from_web(identifier: str) -> bool:
    """
    id veya başlık içeren ürünü web vitrininden siler, HTML'i yeniden oluşturur ve GitHub'a pushlar.
    """
    ensure_web_setup()
    deals = load_deals()
    new_deals = [
        d for d in deals
        if d.get("id") != identifier and identifier.lower() not in d.get("title", "").lower()
    ]
    if len(new_deals) != len(deals):
        save_deals(new_deals)
        render_web_html(new_deals)
        push_to_github()
        print(f"[Web] 🗑️ Ürün vitrinden silindi: {identifier}")
        return True
    return False

def check_and_update_all_deals_status() -> dict:
    """
    Web vitrinindeki tüm ürünlerin Amazon canlı stok ve fiyat durumunu denetler.
    Stok bitmişse veya indirim sona ermişse ürünü otomatik olarak is_expired=True yapar
    ve web vitrinini yeniden derleyip canlı siteye yansıtır.
    """
    ensure_web_setup()
    deals = load_deals()
    if not deals:
        return {"updated": False, "expired_count": 0}

    from product_verifier import verify_amazon_product
    from deal_hunter import parse_price_to_float

    changes_made = False
    expired_count = 0

    print("\n[Web Vitrini] 🔍 Canlı stok ve fiyat kontrolü başlatılıyor...")

    for d in deals:
        url = d.get("store_url", "")
        # Yalnızca Amazon ürünlerini kontrol et
        if "amazon" in url.lower() or d.get("store_name") == "Amazon TR":
            title = d.get("title", "Ürün")
            try:
                v_res = verify_amazon_product(url)
                if not v_res.get("success", False):
                    continue

                in_stock = v_res.get("in_stock", True)
                live_price = v_res.get("live_price_val", 0.0)
                original_deal_price = parse_price_to_float(d.get("new_price", ""))

                was_expired = d.get("is_expired", False)

                # 1. Stok bitmiş mi?
                if not in_stock:
                    d["is_expired"] = True
                    d["expired_reason"] = "Stok Tükendi"
                    if not was_expired:
                        changes_made = True
                        expired_count += 1
                        print(f"[Web Vitrini] 🔴 Stok Tükendi: {title}")

                # 2. Fiyat artmış mı / indirim bitmiş mi? (Örn: %12'den fazla zam gelmişse)
                elif original_deal_price > 0 and live_price > (original_deal_price * 1.12):
                    d["is_expired"] = True
                    d["expired_reason"] = "İndirim Bitti"
                    if not was_expired:
                        changes_made = True
                        expired_count += 1
                        print(f"[Web Vitrini] 🔴 İndirim Bitti (Eski: {original_deal_price} TL -> Canlı: {live_price} TL): {title}")

                # 3. Eğer stok geri geldiyse ve indirim devam ediyorsa aktife al
                elif in_stock and original_deal_price > 0 and live_price <= (original_deal_price * 1.05) and was_expired:
                    d["is_expired"] = False
                    d["expired_reason"] = ""
                    changes_made = True
                    print(f"[Web Vitrini] 🟢 Fırsat Yeniden Aktif: {title}")

            except Exception as e:
                print(f"[Web Vitrini] Kontrol hatası ({title}): {e}")

    if changes_made:
        save_deals(deals)
        render_web_html(deals)
        push_to_github()
        print(f"[Web Vitrini] 🚀 Vitrin güncellendi! {expired_count} adet ürünün durumu yenilendi.")

    return {"updated": changes_made, "expired_count": expired_count}

def push_to_github():
    try:
        safe_run_subprocess(["git", "add", "."], cwd=WEB_DIR, capture_output=True)
        safe_run_subprocess(["git", "commit", "-m", "Auto-update deals"], cwd=WEB_DIR, capture_output=True)
        safe_run_subprocess(["git", "push"], cwd=WEB_DIR, capture_output=True)
        print("[Web] 🚀 GitHub Pages (Canlı Web Sitesi) otomatik senkronize edildi!")
    except Exception as e:
        print(f"[Web] Git push uyarısı: {e}")

def render_web_html(deals: list = None):
    """
    Tüm ürünleri içeren ultra-hızlı, mobil uyumlu, estetik karanlık temalı index.html oluşturur.
    Google Analytics 4 (GA4), UTM kaynak ilişkilendirmesi ve yerel etkileşim telemetrisi içerir.
    """
    if deals is None:
        deals = load_deals()

    ga_id = (GA_MEASUREMENT_ID or os.getenv("GA_MEASUREMENT_ID", "")).strip()

    if ga_id:
        ga_tag = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{ga_id}');
    </script>"""
        ga_configured_js = "true"
        ga_id_js = f"'{ga_id}'"
    else:
        ga_tag = "    <!-- Google Analytics ID ayarlanmadı. Yerel telemetri ve etkileşim motoru çalışıyor. -->"
        ga_configured_js = "false"
        ga_id_js = "''"

    # Ürün kartları HTML üretimi
    cards_html = ""
    if not deals:
        cards_html = """
            <div class="empty-state">
                <h2>⚡ Henüz fırsat eklenmedi</h2>
                <p>En sıcak indirimler birazdan burada listelenecek!</p>
            </div>
"""
    else:
        from campaign_calculator import calculate_campaign_and_net_cost
        from deal_hunter import parse_price_to_float
        first_active_featured = False
        for idx, d in enumerate(deals):
            img_src = d.get("image_url") or "assets/logo.jpg"
            title = d.get("title", "Fırsat Ürünü")
            old_p = d.get("old_price", "")
            new_p = d.get("new_price", "")
            disc = d.get("discount_pct", "")
            store = d.get("store_name", "Fırsat")
            url = d.get("store_url", "#")
            deal_id = d.get("id", "")
            deal_code = d.get("deal_code", f"#{100 + len(deals) - idx}")
            code_num_only = deal_code.replace("#", "").strip()

            # Kategori & Kupon (Nays tamamen kaldırıldı)
            category = d.get("category") or "general"
            coupon_info = d.get("coupon_info", "")

            coupon_html = f"""
                        <div class="advantage-row coupon-highlight">
                            <span class="advantage-icon">🎟️</span>
                            <span class="advantage-txt"><strong>Kupon:</strong> {coupon_info} (Sayfada Aktif Edin)</span>
                        </div>
            """ if coupon_info else ""

            # Görsel Fiyat Geçmişi / Net Kazanç Barı
            old_val_f = parse_price_to_float(old_p) if old_p else 0.0
            new_val_f = parse_price_to_float(new_p) if new_p else 0.0
            savings_bar_html = ""
            if old_val_f > new_val_f and new_val_f > 0:
                sav_tl = int(round(old_val_f - new_val_f))
                sav_fmt = f"{sav_tl:,} TL".replace(",", ".")
                fill_pct = max(25, min(92, int(round((1.0 - (new_val_f / old_val_f)) * 100)) + 35))
                savings_bar_html = f"""
                        <div class="savings-proof-box">
                            <div class="savings-proof-top">
                                <span>📉 Piyasa/Liste: <s>{old_p}</s></span>
                                <span class="savings-gain">🔥 {sav_fmt} Net Kazanç!</span>
                            </div>
                            <div class="savings-bar-track">
                                <div class="savings-bar-fill" style="width: {fill_pct}%"></div>
                            </div>
                        </div>
                """

            # Teslimat & Taksit Bilgisi
            camp_info = calculate_campaign_and_net_cost(new_p, store)
            bank_camp = d.get("bank_campaign") or camp_info["bank_campaign"]
            installment = d.get("installment") or camp_info.get("installment", "Peşin Fiyatına 3 Taksit")

            # Mağaza Rozet Rengi
            store_low = store.lower()
            store_class = "store-trendyol" if "trendyol" in store_low else ("store-hepsiburada" if "hepsi" in store_low else "store-amazon")

            # XSS korumalı veri özellikleri
            safe_title = title.replace('"', '&quot;')
            safe_store = store.replace('"', '&quot;')
            safe_price = new_p.replace('"', '&quot;')

            # Expired Durum Kontrolü
            is_expired = d.get("is_expired", False)
            expired_reason = d.get("expired_reason", "İndirim Bitti") or "İndirim Bitti"
            status_attr = "expired" if is_expired else "active"
            
            # 1 Numaralı Son Paylaşılan Reels Ürünü Vurgusu
            featured_reel_html = ""
            card_class = "deal-card"
            if is_expired:
                card_class = "deal-card expired-card"
            elif not first_active_featured:
                first_active_featured = True
                card_class = "deal-card featured-reel-card"
                badge_lbl = "⚡ REELS'TEKİ FIRSAT" if d.get("is_reel") else "⚡ GÜNÜN ÖNE ÇIKAN FIRSATI"
                featured_reel_html = f'<span class="badge-featured-reel">{badge_lbl}</span>'

            expired_badge_html = f'<span class="badge-expired">🔴 {expired_reason.upper()}</span>' if is_expired else ""
            buy_btn_html = (
                f'<a href="{url}" target="_blank" rel="nofollow noopener sponsored" class="buy-btn expired-btn" data-deal-id="{deal_id}" data-title="{safe_title}" data-store="{safe_store}" data-price="{safe_price}">'
                f'⌛ İndirim Sona Erdi (Fiyatı Gör)'
                f'</a>'
            ) if is_expired else (
                f'<a href="{url}" target="_blank" rel="nofollow noopener sponsored" class="buy-btn" data-deal-id="{deal_id}" data-title="{safe_title}" data-store="{safe_store}" data-price="{safe_price}">'
                f'🔥 Fırsata Git & Satın Al'
                f'</a>'
            )

            cards_html += f"""
            <div class="{card_class}" data-status="{status_attr}" data-category="{category}" data-title="{title.lower()} {store.lower()} {category} {deal_code.lower()} {code_num_only} kod {code_num_only}" data-deal-id="{deal_id}" data-deal-title="{safe_title}" data-store="{safe_store}" data-price="{safe_price}">
                <a href="{url}" target="_blank" rel="nofollow noopener sponsored" class="card-img-link" title="{safe_title}">
                    <div class="card-img-wrap">
                        <img src="{img_src}" alt="{safe_title}" class="card-img" loading="lazy">
                        <span class="badge-store {store_class}">{store}</span>
                        <span class="badge-discount">{disc}</span>
                        <span class="badge-deal-code">🔢 KOD: {deal_code}</span>
                        {featured_reel_html}
                        {expired_badge_html}
                    </div>
                </a>
                <div class="card-content">
                    <a href="{url}" target="_blank" rel="nofollow noopener sponsored" class="card-title-link" title="{safe_title}">
                        <h3 class="card-title">{title}</h3>
                    </a>
                    <div class="price-section">
                        <span class="old-price">{old_p}</span>
                        <span class="new-price">{new_p}</span>
                    </div>
                    {savings_bar_html}

                    <div class="campaign-box">
                        {coupon_html}
                        <div class="advantage-row">
                            <span class="advantage-icon">⚡</span>
                            <span class="advantage-txt">{installment}</span>
                        </div>
                        <div class="advantage-row">
                            <span class="advantage-icon">📦</span>
                            <span class="advantage-txt">{bank_camp}</span>
                        </div>
                    </div>

                    {buy_btn_html}
                </div>
            </div>
"""

    html_template = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flaş Fırsat ⚡ | Amazon, Trendyol & Hepsiburada Dip Fiyat Radarı</title>
    <meta name="description" content="Piyasa altı flaş indirimler, yapay zeka destekli dip fiyat takibi ve en sıcak fırsatlar!">
    <link rel="canonical" href="https://flasfirsat.com.tr/">
    <meta property="og:url" content="https://flasfirsat.com.tr/">
    <meta property="og:site_name" content="Flaş Fırsat">
    <meta property="og:title" content="Flaş Fırsat ⚡ | Dip Fiyat Radarı">
    <meta property="og:description" content="Amazon, Trendyol ve Hepsiburada'daki piyasa altı en sıcak fırsatlar!">
    <meta property="og:image" content="https://flasfirsat.com.tr/assets/logo.jpg">
    <meta property="og:type" content="website">
    <meta name="theme-color" content="#0B0D12">
    <link rel="icon" type="image/jpeg" href="assets/logo.jpg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
{{GA_TAG}}
    <style>
        :root {
            --bg-base: #0B0D12;
            --bg-surface: #141721;
            --bg-card: #1A1E2B;
            --border: rgba(255, 255, 255, 0.08);
            --primary-orange: #FF5722;
            --primary-yellow: #FFC107;
            --accent-green: #10B981;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            padding-bottom: 60px;
        }

        /* Header / Brand */
        header {
            text-align: center;
            padding: 40px 20px 24px;
            background: radial-gradient(circle at top, rgba(255, 87, 34, 0.12) 0%, transparent 70%);
        }

        .logo-wrap {
            position: relative;
            display: inline-block;
            margin-bottom: 16px;
        }

        .logo-img {
            width: 104px;
            height: 104px;
            border-radius: 50%;
            border: 3px solid var(--primary-orange);
            box-shadow: 0 0 25px rgba(255, 87, 34, 0.35);
            object-fit: cover;
        }

        .brand-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FFC107, #FF5722);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .brand-desc {
            color: var(--text-muted);
            font-size: 0.98rem;
            max-width: 500px;
            margin: 0 auto 20px;
            line-height: 1.5;
        }

        /* Social Quick Links */
        .social-bar {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .social-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-main);
            text-decoration: none;
            padding: 10px 18px;
            border-radius: 99px;
            font-size: 0.88rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .social-btn:hover {
            background: var(--primary-orange);
            border-color: var(--primary-orange);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 87, 34, 0.3);
        }

        /* Container */
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 16px;
        }

        /* Dynamic Welcome Banner (UTM Referral) */
        .welcome-banner {
            display: none;
            background: linear-gradient(135deg, rgba(255, 87, 34, 0.15) 0%, rgba(255, 193, 7, 0.10) 100%);
            border: 1px solid rgba(255, 87, 34, 0.35);
            border-radius: 16px;
            padding: 14px 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(255, 87, 34, 0.12);
            animation: fadeInSlide 0.35s ease-out;
        }

        @keyframes fadeInSlide {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .welcome-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }

        .welcome-content {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.94rem;
            color: #F8FAFC;
        }

        .welcome-icon {
            font-size: 1.45rem;
            line-height: 1;
        }

        .welcome-text strong {
            color: #FFC107;
        }

        .welcome-close {
            background: transparent;
            border: none;
            color: #94A3B8;
            font-size: 1.3rem;
            cursor: pointer;
            padding: 0 4px;
            line-height: 1;
            transition: color 0.2s;
        }

        .welcome-close:hover {
            color: #FFFFFF;
        }

        /* Search & Filter Bar */
        .controls-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 28px;
            flex-wrap: wrap;
        }

        .search-box {
            flex: 1;
            min-width: 260px;
            position: relative;
        }

        .search-input {
            width: 100%;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 20px;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-input:focus {
            border-color: var(--primary-orange);
        }

        /* Product Cards Grid */
        .deals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }

        .deal-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        }

        .deal-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 87, 34, 0.4);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
        }

        .card-img-wrap {
            height: 260px;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            position: relative;
            overflow: hidden;
            border-top-left-radius: 19px;
            border-top-right-radius: 19px;
        }

        .card-img {
            max-height: 210px;
            width: auto;
            max-width: 100%;
            object-fit: contain;
            transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
            position: relative;
            z-index: 1;
        }

        .deal-card:hover .card-img {
            transform: scale(1.06);
        }

        .badge-discount {
            position: absolute;
            top: 14px;
            right: 14px;
            background: linear-gradient(135deg, #FF1744, #D50000);
            color: #ffffff;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 6px 12px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(213, 0, 0, 0.35);
            z-index: 10;
            pointer-events: none;
            letter-spacing: 0.5px;
        }

        .badge-featured-reel {
            position: absolute;
            bottom: 12px;
            left: 14px;
            background: linear-gradient(135deg, #F59E0B, #D97706);
            color: #0F172A;
            font-weight: 800;
            font-size: 0.74rem;
            padding: 5px 11px;
            border-radius: 8px;
            box-shadow: 0 4px 14px rgba(245, 158, 11, 0.5);
            z-index: 10;
            letter-spacing: 0.4px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            border: 1px solid rgba(255, 255, 255, 0.8);
            animation: pulse-featured 2.5s infinite;
        }

        @keyframes pulse-featured {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.04); }
        }

        .featured-reel-card {
            border: 2px solid rgba(245, 158, 11, 0.6) !important;
            box-shadow: 0 8px 24px rgba(245, 158, 11, 0.2) !important;
        }

        .badge-store {
            position: absolute;
            top: 14px;
            left: 14px;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(8px);
            color: #F8FAFC;
            font-weight: 700;
            font-size: 0.78rem;
            padding: 6px 12px;
            border-radius: 9px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            z-index: 10;
            pointer-events: none;
            letter-spacing: 0.3px;
        }

        .badge-store.store-trendyol {
            background: rgba(242, 122, 26, 0.92);
            border-color: rgba(255, 255, 255, 0.25);
        }

        .badge-store.store-hepsiburada {
            background: rgba(255, 96, 0, 0.92);
            border-color: rgba(255, 255, 255, 0.25);
        }

        .card-content {
            padding: 20px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }

        .card-img-link {
            text-decoration: none;
            display: block;
        }

        .card-title-link {
            text-decoration: none;
            color: inherit;
            display: block;
        }

        .card-title-link:hover .card-title {
            color: var(--primary-orange);
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 14px;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            height: 2.8em;
        }

        .price-section {
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 14px;
            margin-top: auto;
        }

        .old-price {
            color: var(--text-muted);
            text-decoration: line-through;
            font-size: 0.95rem;
        }

        .new-price {
            color: var(--text-main);
            font-size: 1.55rem;
            font-weight: 800;
        }

        /* Avantaj & Taksit Kutusu */
        .campaign-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 18px;
            display: flex;
            flex-direction: column;
            gap: 7px;
            transition: all 0.2s ease;
        }

        .campaign-box:hover {
            border-color: rgba(255, 193, 7, 0.35);
            background: rgba(255, 255, 255, 0.05);
        }

        .advantage-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            color: #CBD5E1;
        }

        .advantage-row.coupon-highlight {
            color: #FDE047;
            background: rgba(250, 204, 21, 0.1);
            border: 1px dashed rgba(250, 204, 21, 0.4);
            border-radius: 8px;
            padding: 6px 10px;
        }

        .advantage-icon {
            font-size: 0.95rem;
            flex-shrink: 0;
        }

        .advantage-txt {
            line-height: 1.3;
            font-weight: 500;
        }

        /* Category Filter Tabs */
        .category-tabs-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            overflow-x: auto;
            padding-bottom: 6px;
            scrollbar-width: none;
        }

        .category-tabs-wrapper::-webkit-scrollbar {
            display: none;
        }

        .category-tab {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 8px 16px;
            border-radius: 99px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
            white-space: nowrap;
        }

        .category-tab:hover {
            background: rgba(255, 255, 255, 0.09);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.2);
        }

        .category-tab.active {
            background: linear-gradient(135deg, #FFC107, #FF5722);
            color: #0B0D12;
            font-weight: 800;
            border-color: #FFC107;
            box-shadow: 0 4px 14px rgba(255, 193, 7, 0.35);
        }

        .buy-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: linear-gradient(135deg, var(--primary-orange), #FF3D00);
            color: #ffffff;
            text-decoration: none;
            padding: 14px 20px;
            border-radius: 14px;
            font-weight: 700;
            font-size: 1rem;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(255, 87, 34, 0.25);
            cursor: pointer;
        }

        .buy-btn:hover {
            background: linear-gradient(135deg, #FF6E40, #FF5722);
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(255, 87, 34, 0.4);
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            grid-column: 1 / -1;
        }

        /* Filter Tabs (Devam Edenler / Bitenler) */
        .filter-tabs-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 24px;
            overflow-x: auto;
            padding-bottom: 6px;
            scrollbar-width: none;
        }

        .filter-tabs-wrapper::-webkit-scrollbar {
            display: none;
        }

        .filter-tab {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 10px 20px;
            border-radius: 99px;
            font-size: 0.88rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .filter-tab:hover {
            background: rgba(255, 255, 255, 0.09);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.2);
        }

        .filter-tab.active {
            background: linear-gradient(135deg, #FF5722, #E64A19);
            color: #ffffff;
            border-color: #FF5722;
            box-shadow: 0 4px 14px rgba(255, 87, 34, 0.35);
        }

        .tab-badge {
            background: rgba(0, 0, 0, 0.25);
            padding: 2px 8px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 800;
        }

        .filter-tab.active .tab-badge {
            background: rgba(255, 255, 255, 0.25);
            color: #ffffff;
        }

        /* Expired Deal Card Styles */
        .deal-card.expired-card {
            opacity: 0.65;
            filter: grayscale(0.5);
            border-color: rgba(239, 68, 68, 0.25);
            transition: all 0.3s;
        }

        .deal-card.expired-card:hover {
            opacity: 0.92;
            filter: grayscale(0.15);
            border-color: rgba(239, 68, 68, 0.45);
        }

        .badge-expired {
            position: absolute;
            bottom: 12px;
            left: 12px;
            background: linear-gradient(135deg, #EF4444, #B91C1C);
            color: #ffffff;
            font-weight: 800;
            font-size: 0.76rem;
            padding: 5px 11px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.45);
            z-index: 10;
            letter-spacing: 0.5px;
            pointer-events: none;
        }

        .buy-btn.expired-btn {
            background: rgba(255, 255, 255, 0.08);
            color: #94A3B8;
            border: 1px solid var(--border);
            box-shadow: none;
        }

        .buy-btn.expired-btn:hover {
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.4);
            color: #FCA5A5;
            transform: scale(1.01);
        }

        footer {
            text-align: center;
            margin-top: 50px;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* Modern Native HTML5 Dialog (Stats Modal) */
        .stats-dialog {
            background: rgba(20, 23, 33, 0.96);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 24px;
            color: var(--text-main);
            padding: 0;
            width: min(92vw, 760px);
            max-height: 88vh;
            margin: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 87, 34, 0.2);
            overflow: hidden;
        }

        .stats-dialog::backdrop {
            background: rgba(5, 7, 10, 0.78);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }

        .stats-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 26px;
            border-bottom: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.02);
        }

        .stats-header-title {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .stats-badge-live {
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            font-size: 0.72rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .stats-badge-live::before {
            content: '';
            width: 7px;
            height: 7px;
            background: #10B981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10B981;
        }

        .stats-title {
            font-size: 1.22rem;
            font-weight: 800;
            color: #ffffff;
        }

        .stats-close-btn {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border);
            color: #94A3B8;
            border-radius: 10px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .stats-close-btn:hover {
            background: rgba(255, 255, 255, 0.12);
            color: #ffffff;
        }

        .stats-body {
            padding: 24px 26px;
            overflow-y: auto;
            max-height: calc(88vh - 150px);
            display: flex;
            flex-direction: column;
            gap: 22px;
        }

        /* KPI Cards Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
        }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            transition: transform 0.2s;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 87, 34, 0.3);
        }

        .kpi-label {
            font-size: 0.74rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        .kpi-val {
            font-size: 1.7rem;
            font-weight: 800;
            color: #ffffff;
        }

        .kpi-val.highlight { color: #FF9800; }
        .kpi-val.green { color: #34D399; }

        .kpi-sub {
            font-size: 0.72rem;
            color: #94A3B8;
        }

        /* Sections */
        .stats-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 18px;
        }

        .stats-section-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Source Progress Bars */
        .source-bar-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.84rem;
        }

        .source-bar-info {
            display: flex;
            align-items: center;
            gap: 8px;
            width: 140px;
        }

        .source-bar-track {
            flex: 1;
            height: 8px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 99px;
            overflow: hidden;
            margin: 0 12px;
        }

        .source-bar-fill {
            height: 100%;
            border-radius: 99px;
            transition: width 0.5s ease-out;
        }

        .source-bar-fill.ig { background: linear-gradient(90deg, #F58529, #DD2A7B, #8134AF); }
        .source-bar-fill.yt { background: linear-gradient(90deg, #FF0000, #CC0000); }
        .source-bar-fill.tg { background: linear-gradient(90deg, #2AABEE, #229ED9); }
        .source-bar-fill.tt { background: linear-gradient(90deg, #00f2fe, #4facfe); }
        .source-bar-fill.dir { background: #94A3B8; }

        .source-bar-count {
            font-weight: 700;
            width: 60px;
            text-align: right;
            color: #ffffff;
            font-size: 0.8rem;
        }

        /* Top Deals List */
        .top-deals-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .top-deal-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            font-size: 0.85rem;
            gap: 12px;
        }

        .top-deal-title {
            color: #CBD5E1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex: 1;
        }

        .top-deal-clicks {
            background: rgba(255, 87, 34, 0.15);
            color: #FF7043;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            white-space: nowrap;
        }

        /* Recent Activity Log */
        .log-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 180px;
            overflow-y: auto;
        }

        .log-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.78rem;
            padding: 6px 10px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.02);
            color: #94A3B8;
        }

        .log-time {
            color: #64748B;
            font-family: monospace;
        }

        .log-title {
            color: #E2E8F0;
            font-weight: 600;
            flex: 1;
            margin: 0 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .log-tag {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.08);
            color: #CBD5E1;
        }

        .stats-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 26px;
            border-top: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.02);
            flex-wrap: wrap;
            gap: 12px;
        }

        .stats-footer-left {
            display: flex;
            gap: 8px;
        }

        .stats-btn {
            padding: 9px 16px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .stats-btn-primary {
            background: var(--primary-orange);
            color: #ffffff;
        }

        .stats-btn-primary:hover {
            background: #FF6E40;
        }

        .stats-btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: #E2E8F0;
            border: 1px solid var(--border);
        }

        .stats-btn-secondary:hover {
            background: rgba(255, 255, 255, 0.14);
        }

        .stats-btn-danger {
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .stats-btn-danger:hover {
            background: rgba(239, 68, 68, 0.25);
        }

        /* Footer Trigger Link (Sadece Yönetici için Gizli) */
        .footer-stats-trigger {
            display: none;
            margin-top: 16px;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }

        .footer-stats-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 7px 16px;
            border-radius: 99px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .footer-stats-btn:hover {
            background: rgba(255, 87, 34, 0.12);
            border-color: rgba(255, 87, 34, 0.3);
            color: #FF7043;
        }

        .footer-hint {
            font-size: 0.7rem;
            color: #64748B;
        }

        .footer-hint code {
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 5px;
            border-radius: 4px;
            color: #94A3B8;
        }

        /* Fırsat Kodu Rozeti */
        .badge-deal-code {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(15, 23, 42, 0.92);
            color: #FACC15;
            border: 1px solid rgba(250, 204, 21, 0.45);
            font-size: 0.74rem;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 8px;
            letter-spacing: 0.4px;
            backdrop-filter: blur(6px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
            z-index: 3;
        }

        /* Piyasa Kıyaslama & Net Kazanç Barı */
        .savings-proof-box {
            background: rgba(16, 185, 129, 0.07);
            border: 1px solid rgba(16, 185, 129, 0.22);
            border-radius: 10px;
            padding: 8px 11px;
            margin-bottom: 12px;
        }
        .savings-proof-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.76rem;
            color: #CBD5E1;
            margin-bottom: 6px;
            gap: 6px;
        }
        .savings-gain {
            color: #34D399;
            font-weight: 800;
        }
        .savings-bar-track {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 99px;
            overflow: hidden;
        }
        .savings-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10B981, #FACC15);
            border-radius: 99px;
        }

        /* Yüzen (Sticky) Telegram Fırsat Alarmı Barı */
        .sticky-tg-bar {
            position: fixed;
            bottom: 14px;
            left: 50%;
            transform: translateX(-50%);
            width: calc(100% - 28px);
            max-width: 680px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.96));
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-radius: 16px;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            z-index: 999;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(12px);
        }
        .sticky-tg-left {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.84rem;
            color: #F8FAFC;
            font-weight: 600;
            line-height: 1.3;
        }
        .sticky-tg-btn {
            background: linear-gradient(135deg, #0284C7, #38BDF8);
            color: #FFFFFF;
            text-decoration: none;
            font-weight: 800;
            font-size: 0.82rem;
            padding: 8px 14px;
            border-radius: 10px;
            white-space: nowrap;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.35);
            transition: transform 0.2s;
        }
        .sticky-tg-btn:hover {
            transform: scale(1.04);
        }
        .sticky-tg-close {
            background: none;
            border: none;
            color: #94A3B8;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0 4px;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-wrap">
            <img src="assets/logo.jpg" alt="Flaş Fırsat Logo" class="logo-img">
        </div>
        <h1 class="brand-title">FLAŞ FIRSAT ⚡</h1>
        <p class="brand-desc">Amazon, Trendyol ve Hepsiburada'daki piyasa altı en sıcak teknoloji fırsatlarını anlık yakalıyoruz!</p>

        <div class="social-bar">
            <a href="https://t.me/flasfirsat" target="_blank" class="social-btn" data-social="telegram">
                <span>✈️</span> Telegram Kanalı
            </a>
            <a href="https://instagram.com/flasfirsat.tr" target="_blank" class="social-btn" data-social="instagram">
                <span>📸</span> Instagram
            </a>
            <a href="https://www.youtube.com/@flasfirsat" target="_blank" class="social-btn" data-social="youtube">
                <span>▶️</span> YouTube
            </a>
            <a href="https://www.tiktok.com/@flasfirsat" target="_blank" class="social-btn" data-social="tiktok">
                <span>🎵</span> TikTok
            </a>
        </div>
    </header>

    <main class="container">
        <!-- Dinamik Hoş Geldiniz Bildirimi (UTM Kaynak Karşılama) -->
        <div id="welcomeBanner" class="welcome-banner">
            <div class="welcome-inner">
                <div class="welcome-content">
                    <span id="welcomeIcon" class="welcome-icon">⚡</span>
                    <span id="welcomeText" class="welcome-text">Hoş geldiniz!</span>
                </div>
                <button class="welcome-close" onclick="closeWelcomeBanner()" aria-label="Kapat">&times;</button>
            </div>
        </div>

        <div class="controls-bar">
            <div class="search-box">
                <input type="text" id="searchInput" class="search-input" placeholder="🔍 Ürün, marka veya Videodaki Fırsat Kodunu (#101, 102...) ara..." onkeyup="filterDeals()">
            </div>
        </div>

        <!-- Kategori Filtre Sekmeleri -->
        <div class="category-tabs-wrapper">
            <button class="category-tab active" data-cat="all" onclick="setCategoryFilter('all', this)">
                🔥 Tümü
            </button>
            <button class="category-tab" data-cat="gaming" onclick="setCategoryFilter('gaming', this)">
                🎮 Oyuncu & Gaming
            </button>
            <button class="category-tab" data-cat="monitor" onclick="setCategoryFilter('monitor', this)">
                🖥️ Monitör
            </button>
            <button class="category-tab" data-cat="hardware" onclick="setCategoryFilter('hardware', this)">
                💻 Bilgisayar & Donanım
            </button>
            <button class="category-tab" data-cat="lifestyle" onclick="setCategoryFilter('lifestyle', this)">
                ☕ Ev & Yaşam
            </button>
        </div>

        <div class="filter-tabs-wrapper">
            <button class="filter-tab active" data-filter="all" onclick="setStatusFilter('all', this)">
                📦 Tüm Fırsatlar <span class="tab-badge" id="allBadge">0</span>
            </button>
            <button class="filter-tab" data-filter="active" onclick="setStatusFilter('active', this)">
                ⚡ Devam Eden Fırsatlar <span class="tab-badge" id="activeBadge">0</span>
            </button>
            <button class="filter-tab" data-filter="expired" onclick="setStatusFilter('expired', this)">
                ⌛ Biten İndirimler <span class="tab-badge" id="expiredBadge">0</span>
            </button>
        </div>

        <div class="deals-grid" id="dealsGrid">
{{CARDS_HTML}}
        </div>
    </main>

    <footer>
        <p>© 2026 Flaş Fırsat • Fiyatlar anlık olarak değişebilir. Fırsatları kaçırmamak için Telegram'ı takip edin.</p>
        <div id="footerStatsTrigger" class="footer-stats-trigger">
            <button class="footer-stats-btn" onclick="openStatsModal()">
                🔒 Yönetici Paneli
            </button>
        </div>
    </footer>

    <!-- Yüzen Telegram Fırsat Alarmı Barı -->
    <div id="stickyTgBar" class="sticky-tg-bar">
        <div class="sticky-tg-left">
            <span>🚨</span>
            <span>Fiyat hatalarını ve anlık indirimleri tükenmeden yakala!</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            <a href="https://t.me/flasfirsat" target="_blank" class="sticky-tg-btn" data-social="telegram">✈️ Telegram'a Katıl</a>
            <button class="sticky-tg-close" onclick="document.getElementById('stickyTgBar').style.display='none'" aria-label="Kapat">&times;</button>
        </div>
    </div>

    <!-- Native HTML5 Dialog (İstatistik & Ziyaretçi Paneli) -->
    <dialog id="statsModal" class="stats-dialog">
        <div class="stats-header">
            <div class="stats-header-title">
                <span class="stats-badge-live">CANLI RADAR</span>
                <h3 class="stats-title">📊 Ziyaretçi & Etkileşim Paneli</h3>
            </div>
            <button class="stats-close-btn" onclick="closeStatsModal()" aria-label="Kapat">&times;</button>
        </div>
        <div class="stats-body" id="statsModalBody">
            <!-- Dinamik İstatistik İçeriği JavaScript ile yüklenir -->
        </div>
        <div class="stats-footer">
            <div class="stats-footer-left">
                <button class="stats-btn stats-btn-secondary" onclick="exportStatsJSON()">📥 JSON İndir</button>
                <button class="stats-btn stats-btn-danger" onclick="resetStats()">🗑️ Sıfırla</button>
            </div>
            <button class="stats-btn stats-btn-primary" onclick="closeStatsModal()">Tamam</button>
        </div>
    </dialog>

    <script>
        // --- 1. ARAMA VE KATEGORİ FİLTRELEME MOTORU ---
        let currentStatusFilter = 'all';
        let currentCategoryFilter = 'all';

        function setStatusFilter(status, btn) {
            currentStatusFilter = status;
            document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterDeals();
        }

        function setCategoryFilter(cat, btn) {
            currentCategoryFilter = cat;
            document.querySelectorAll('.category-tab').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterDeals();
        }

        function updateBadges() {
            const cards = document.querySelectorAll('.deal-card');
            let activeTotal = 0;
            let expiredTotal = 0;
            cards.forEach(card => {
                if (card.getAttribute('data-status') === 'expired') {
                    expiredTotal++;
                } else {
                    activeTotal++;
                }
            });
            const ab = document.getElementById('activeBadge');
            const alb = document.getElementById('allBadge');
            const eb = document.getElementById('expiredBadge');
            if (ab) ab.textContent = activeTotal;
            if (alb) alb.textContent = cards.length;
            if (eb) eb.textContent = expiredTotal;
        }

        let searchDebounce = null;
        function filterDeals() {
            const input = document.getElementById('searchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('.deal-card');
            let visibleCount = 0;

            cards.forEach(card => {
                const title = (card.getAttribute('data-title') || '').toLowerCase();
                const cardStatus = card.getAttribute('data-status') || 'active';
                const cardCat = card.getAttribute('data-category') || 'general';

                const matchesSearch = !input || title.includes(input);
                const matchesStatus = (currentStatusFilter === 'all') || (cardStatus === currentStatusFilter);
                const matchesCategory = (currentCategoryFilter === 'all') || (cardCat === currentCategoryFilter);

                if (matchesSearch && matchesStatus && matchesCategory) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            // GA4 arama telemetrisi (debounce ile)
            if (input.length >= 3) {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => {
                    if (typeof gtag === 'function') {
                        gtag('event', 'search', {
                            search_term: input,
                            results_count: visibleCount
                        });
                    }
                }, 800);
            }
        }

        // --- 2. ZİYARETÇİ VE ETKİLEŞİM TELEMETRİ MOTORU ---
        const STATS_KEY = 'flas_stats_v1';
        const gaConfigured = {{GA_CONFIGURED}};
        const gaIdSafe = {{GA_ID}};

        function getStoredStats() {
            try {
                const raw = localStorage.getItem(STATS_KEY);
                if (raw) return JSON.parse(raw);
            } catch(e) {}
            return {
                totalVisits: 0,
                totalClicks: 0,
                sourceVisits: { instagram: 0, youtube: 0, telegram: 0, tiktok: 0, whatsapp: 0, direct: 0 },
                storeClicks: { 'Amazon TR': 0, 'Trendyol': 0, 'Hepsiburada': 0, 'Diğer': 0 },
                dealClicks: {},
                recentClicks: []
            };
        }

        function saveStoredStats(stats) {
            try {
                localStorage.setItem(STATS_KEY, JSON.stringify(stats));
            } catch(e) {}
        }

        // UTM ve Referans Kaynak Tespiti
        function detectSource() {
            const params = new URLSearchParams(window.location.search);
            const utm = (params.get('utm_source') || params.get('ref') || '').toLowerCase();
            if (utm) {
                sessionStorage.setItem('flas_detected_source', utm);
                return utm;
            }
            const cached = sessionStorage.getItem('flas_detected_source');
            if (cached) return cached;

            const ref = document.referrer.toLowerCase();
            if (ref.includes('instagram.com')) return 'instagram';
            if (ref.includes('youtube.com') || ref.includes('youtu.be')) return 'youtube';
            if (ref.includes('t.me') || ref.includes('telegram')) return 'telegram';
            if (ref.includes('whatsapp.com') || ref.includes('wa.me')) return 'whatsapp';
            if (ref.includes('tiktok.com')) return 'tiktok';
            return 'direct';
        }

        const currentSource = detectSource();

        // Tekil Oturum Ziyaret Kaydı
        (function recordVisitSession() {
            const sessionActive = sessionStorage.getItem('flas_session_active');
            if (!sessionActive) {
                sessionStorage.setItem('flas_session_active', '1');
                const stats = getStoredStats();
                stats.totalVisits = (stats.totalVisits || 0) + 1;
                const srcKey = stats.sourceVisits[currentSource] !== undefined ? currentSource : 'direct';
                stats.sourceVisits[srcKey] = (stats.sourceVisits[srcKey] || 0) + 1;
                saveStoredStats(stats);
            }
        })();

        // Sosyal Karşılama Bildirimi
        (function renderWelcomeBanner() {
            if (sessionStorage.getItem('flas_banner_dismissed')) return;
            const banner = document.getElementById('welcomeBanner');
            const icon = document.getElementById('welcomeIcon');
            const text = document.getElementById('welcomeText');
            if (!banner || !icon || !text) return;

            if (currentSource === 'instagram') {
                icon.textContent = '📸';
                text.innerHTML = '<strong>Instagram</strong> takipçimiz hoş geldin! Reels videomuzda gördüğün dip fiyat fırsatları aşağıda ⚡';
                banner.style.display = 'block';
            } else if (currentSource === 'youtube') {
                icon.textContent = '📺';
                text.innerHTML = '<strong>YouTube Shorts</strong> izleyicimiz hoş geldin! Videodaki dip fiyat fırsatı ve daha fazlası aşağıda ⚡';
                banner.style.display = 'block';
            } else if (currentSource === 'telegram') {
                icon.textContent = '✈️';
                text.innerHTML = '<strong>Telegram</strong> ailemiz hoş geldin! Radarımıza takılan en sıcak fırsatlar listelendi ⚡';
                banner.style.display = 'block';
            } else if (currentSource === 'whatsapp') {
                icon.textContent = '🟢';
                text.innerHTML = '<strong>WhatsApp</strong> kanalımızdan gelen fırsat avcısı hoş geldin! Sıcak fırsatlar aşağıda listelendi ⚡';
                banner.style.display = 'block';
            } else if (currentSource === 'tiktok') {
                icon.textContent = '🎵';
                text.innerHTML = '<strong>TikTok</strong> fırsat avcısı hoş geldin! Viral fırsatları kaçırmadan incele ⚡';
                banner.style.display = 'block';
            }
        })();

        function closeWelcomeBanner() {
            const banner = document.getElementById('welcomeBanner');
            if (banner) banner.style.display = 'none';
            sessionStorage.setItem('flas_banner_dismissed', '1');
        }

        // Ürün Satın Al Tıklama Takibi (Buton, Görsel veya Başlık)
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('.buy-btn, .card-img-link, .card-title-link');
            if (!btn) return;

            const card = btn.closest('.deal-card');
            const title = btn.getAttribute('data-title') || (card ? card.getAttribute('data-deal-title') : '') || 'Bilinmeyen Ürün';
            const store = btn.getAttribute('data-store') || (card ? card.getAttribute('data-store') : '') || 'Diğer';
            const price = btn.getAttribute('data-price') || (card ? card.getAttribute('data-price') : '') || '';
            const dealId = btn.getAttribute('data-deal-id') || (card ? card.getAttribute('data-deal-id') : '') || '';

            // A) Google Analytics 4 Olayı
            if (typeof gtag === 'function') {
                const numPrice = parseFloat(price.replace(/[^0-9,.]/g, '').replace(',', '.')) || 0;
                gtag('event', 'select_item', {
                    item_list_name: 'Flaş Fırsat Vitrin',
                    items: [{
                        item_id: dealId,
                        item_name: title,
                        affiliation: store,
                        price: numPrice,
                        item_category: store
                    }],
                    traffic_source: currentSource
                });

                gtag('event', 'outbound_deal_click', {
                    deal_id: dealId,
                    deal_title: title,
                    store_name: store,
                    deal_price: price,
                    traffic_source: currentSource
                });
            }

            // B) Yerel Telemetri Kaydı
            const stats = getStoredStats();
            stats.totalClicks = (stats.totalClicks || 0) + 1;

            const storeKey = store.includes('Amazon') ? 'Amazon TR' : (store.includes('Trendyol') ? 'Trendyol' : (store.includes('Hepsi') ? 'Hepsiburada' : 'Diğer'));
            stats.storeClicks[storeKey] = (stats.storeClicks[storeKey] || 0) + 1;

            stats.dealClicks[title] = (stats.dealClicks[title] || 0) + 1;

            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
            stats.recentClicks.unshift({
                time: timeStr,
                title: title,
                store: storeKey,
                price: price,
                source: currentSource
            });
            if (stats.recentClicks.length > 40) stats.recentClicks.pop();

            saveStoredStats(stats);
        });

        // Sosyal Buton Tıklama Takibi
        document.querySelectorAll('.social-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const platform = this.getAttribute('data-social') || 'sosyal';
                if (typeof gtag === 'function') {
                    gtag('event', 'social_channel_click', {
                        channel: platform,
                        traffic_source: currentSource
                    });
                }
            });
        });

        // --- 3. DİNAMİK İSTATİSTİK MODAL PENCERESİ ---
        const statsDialog = document.getElementById('statsModal');

        function renderStatsUI() {
            const stats = getStoredStats();
            const totalVisits = stats.totalVisits || 0;
            const totalClicks = stats.totalClicks || 0;
            const ctr = totalVisits > 0 ? ((totalClicks / totalVisits) * 100).toFixed(1) + '%' : '0.0%';
            const dealsCount = document.querySelectorAll('.deal-card').length;

            const sources = stats.sourceVisits || {};
            const igCount = sources.instagram || 0;
            const ytCount = sources.youtube || 0;
            const tgCount = sources.telegram || 0;
            const ttCount = sources.tiktok || 0;
            const dirCount = sources.direct || 0;
            const totalSrc = (igCount + ytCount + tgCount + ttCount + dirCount) || 1;

            const igPct = Math.round((igCount / totalSrc) * 100);
            const ytPct = Math.round((ytCount / totalSrc) * 100);
            const tgPct = Math.round((tgCount / totalSrc) * 100);
            const ttPct = Math.round((ttCount / totalSrc) * 100);
            const dirPct = Math.round((dirCount / totalSrc) * 100);

            const sortedDeals = Object.entries(stats.dealClicks || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);

            let topDealsHtml = '';
            if (sortedDeals.length === 0) {
                topDealsHtml = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 12px;">Henüz tıklanan fırsat yok.</div>';
            } else {
                sortedDeals.forEach(([t, count], i) => {
                    topDealsHtml += `
                        <div class="top-deal-item">
                            <span style="font-weight: 800; color: #FF9800; width: 20px;">#${i+1}</span>
                            <span class="top-deal-title" title="${t}">${t}</span>
                            <span class="top-deal-clicks">${count} tık</span>
                        </div>`;
                });
            }

            let recentHtml = '';
            if (!stats.recentClicks || stats.recentClicks.length === 0) {
                recentHtml = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 12px;">Henüz son tıklama kaydı yok.</div>';
            } else {
                stats.recentClicks.slice(0, 15).forEach(item => {
                    recentHtml += `
                        <div class="log-item">
                            <span class="log-time">${item.time}</span>
                            <span class="log-title">${item.title}</span>
                            <span class="log-tag">${item.store}</span>
                            <span class="log-tag" style="color: #FFC107;">${item.source}</span>
                        </div>`;
                });
            }

            const gaStatusHtml = gaConfigured 
                ? `<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 12px; padding: 12px 16px; font-size: 0.82rem; color: #A7F3D0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <span>🟢 <b>Google Analytics 4 Aktif:</b> Ölçüm Kimliği (${gaIdSafe})</span>
                    <a href="https://analytics.google.com/" target="_blank" style="color: #34D399; font-weight: 700; text-decoration: underline;">Canlı GA4 Raporunu Aç ↗</a>
                   </div>`
                : `<div style="background: rgba(255, 193, 7, 0.08); border: 1px solid rgba(255, 193, 7, 0.2); border-radius: 12px; padding: 12px 16px; font-size: 0.82rem; color: #FDE68A;">
                    💡 <b>İpucu:</b> Bu panel yerel tarayıcı verilerini gösterir. Google Analytics canlı bulut gösterge panelini aktif etmek için <code>.env</code> dosyasına <code>GA_MEASUREMENT_ID=G-XXXXXXXXXX</code> ekleyebilirsiniz.
                   </div>`;

            document.getElementById('statsModalBody').innerHTML = `
                ${gaStatusHtml}

                <div class="kpi-grid">
                    <div class="kpi-card">
                        <span class="kpi-label">Toplam Ziyaret</span>
                        <span class="kpi-val highlight">${totalVisits}</span>
                        <span class="kpi-sub">Tekil Oturumlar</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Fırsat Tıklaması</span>
                        <span class="kpi-val green">${totalClicks}</span>
                        <span class="kpi-sub">Satın Al Butonları</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Tıklama Oranı</span>
                        <span class="kpi-val">${ctr}</span>
                        <span class="kpi-sub">Tıklama / Ziyaret</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">Aktif Fırsat</span>
                        <span class="kpi-val">${dealsCount}</span>
                        <span class="kpi-sub">Vitrindeki Ürünler</span>
                    </div>
                </div>

                <div class="stats-section">
                    <div class="stats-section-title">
                        <span>🌐 Ziyaretçi Kaynak Dağılımı (Sosyal Medya Radarı)</span>
                    </div>
                    <div class="source-bar-row">
                        <div class="source-bar-info"><span>📸 Instagram</span></div>
                        <div class="source-bar-track"><div class="source-bar-fill ig" style="width: ${igPct}%"></div></div>
                        <span class="source-bar-count">${igCount} (%${igPct})</span>
                    </div>
                    <div class="source-bar-row">
                        <div class="source-bar-info"><span>📺 YouTube</span></div>
                        <div class="source-bar-track"><div class="source-bar-fill yt" style="width: ${ytPct}%"></div></div>
                        <span class="source-bar-count">${ytCount} (%${ytPct})</span>
                    </div>
                    <div class="source-bar-row">
                        <div class="source-bar-info"><span>✈️ Telegram</span></div>
                        <div class="source-bar-track"><div class="source-bar-fill tg" style="width: ${tgPct}%"></div></div>
                        <span class="source-bar-count">${tgCount} (%${tgPct})</span>
                    </div>
                    <div class="source-bar-row">
                        <div class="source-bar-info"><span>🎵 TikTok</span></div>
                        <div class="source-bar-track"><div class="source-bar-fill tt" style="width: ${ttPct}%"></div></div>
                        <span class="source-bar-count">${ttCount} (%${ttPct})</span>
                    </div>
                    <div class="source-bar-row">
                        <div class="source-bar-info"><span>🔗 Doğrudan / Web</span></div>
                        <div class="source-bar-track"><div class="source-bar-fill dir" style="width: ${dirPct}%"></div></div>
                        <span class="source-bar-count">${dirCount} (%${dirPct})</span>
                    </div>
                </div>

                <div class="stats-section">
                    <div class="stats-section-title">
                        <span>🏆 En Çok Tıklanan Fırsatlar</span>
                    </div>
                    <div class="top-deals-list">${topDealsHtml}</div>
                </div>

                <div class="stats-section">
                    <div class="stats-section-title">
                        <span>🕒 Canlı Tıklama Akışı (Son Hareketler)</span>
                    </div>
                    <div class="log-list">${recentHtml}</div>
                </div>
            `;
        }

        function openStatsModal() {
            renderStatsUI();
            if (statsDialog) statsDialog.showModal();
        }

        function closeStatsModal() {
            if (statsDialog) statsDialog.close();
        }

        // Arka plan tıklamasında kapatma (Light dismiss)
        if (statsDialog) {
            statsDialog.addEventListener('click', function(e) {
                if (e.target === statsDialog) statsDialog.close();
            });
        }

        // Yönetici Erişimi: Yalnızca ?admin=flas veya #admin ile girildiğinde paneli aç ve butonu göster
        const isAdmin = new URLSearchParams(window.location.search).get('admin') === 'flas' || 
                        window.location.hash === '#admin';
        if (isAdmin) {
            const trg = document.getElementById('footerStatsTrigger');
            if (trg) trg.style.display = 'flex';
            setTimeout(openStatsModal, 300);
        }

        // Kısayol: Shift + S (Yalnızca sizin klavyenizden gizlice açabilmeniz için)
        document.addEventListener('keydown', function(e) {
            if (e.shiftKey && (e.key === 'S' || e.key === 's')) {
                e.preventDefault();
                openStatsModal();
            }
        });

        function exportStatsJSON() {
            const stats = getStoredStats();
            const blob = new Blob([JSON.stringify(stats, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `flas_firsat_stats_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }

        function resetStats() {
            if (confirm('Tüm yerel istatistikleri ve tıklama geçmişini sıfırlamak istediğinize emin misiniz?')) {
                localStorage.removeItem(STATS_KEY);
                sessionStorage.removeItem('flas_session_active');
                renderStatsUI();
            }
        }

        // İlk açılışta rozet sayılarını hesapla ve aktif fırsatları filtrele
        document.addEventListener('DOMContentLoaded', function() {
            updateBadges();
            filterDeals();
        });
        updateBadges();
        filterDeals();
    </script>
</body>
</html>
"""

    final_html = (
        html_template
        .replace("{{GA_TAG}}", ga_tag)
        .replace("{{CARDS_HTML}}", cards_html)
        .replace("{{GA_CONFIGURED}}", ga_configured_js)
        .replace("{{GA_ID}}", ga_id_js)
    )

    index_path = os.path.join(WEB_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    # Sitemap.xml oluştur (Google indekslemesi için)
    sitemap_path = os.path.join(WEB_DIR, "sitemap.xml")
    today_iso = datetime.now().strftime("%Y-%m-%d")
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://flasfirsat.com.tr/</loc>
    <lastmod>{today_iso}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    return index_path

if __name__ == "__main__":
    ensure_web_setup()
    render_web_html()
    print(f"Web showcase generated at {WEB_DIR}/index.html")
