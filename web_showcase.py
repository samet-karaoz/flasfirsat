import os
import json
import shutil
from datetime import datetime
from config import BASE_DIR, ASSETS_DIR

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

    if not os.path.exists(DEALS_JSON_PATH):
        with open(DEALS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_deals() -> list:
    ensure_web_setup()
    if os.path.exists(DEALS_JSON_PATH):
        try:
            with open(DEALS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_deals(deals: list):
    ensure_web_setup()
    with open(DEALS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)

def add_deal_to_web(deal: dict):
    """
    Yeni fırsatı web sitesi veritabanına ekler ve index.html'i yeniden derler.
    """
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
    net_cost = deal.get("net_cost") or camp_info["net_cost"]
    installment = deal.get("installment") or camp_info.get("installment", "")

    deal_item = {
        "id": f"deal_{int(datetime.now().timestamp())}_{len(deals)}",
        "title": deal.get("title", "Fırsat Ürünü"),
        "old_price": deal.get("old_price", ""),
        "new_price": deal.get("new_price", ""),
        "discount_pct": deal.get("discount_pct", ""),
        "store_name": deal.get("store_name", "Amazon TR"),
        "store_url": deal.get("affiliate_url") or deal.get("store_url", "#"),
        "bank_campaign": bank_camp,
        "net_cost": net_cost,
        "installment": installment,
        "image_url": web_img_rel,
        "date_added": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

    # Başa ekle (en yeni en üstte)
    # Aynı url veya başlık varsa güncelle
    existing_idx = None
    for i, d in enumerate(deals):
        if d.get("title") == deal_item["title"]:
            existing_idx = i
            break

    if existing_idx is not None:
        deals[existing_idx] = deal_item
    else:
        deals.insert(0, deal_item)

    # Maksimum 100 ürün sakla
    deals = deals[:100]
    save_deals(deals)

    # HTML'i güncelle
    render_web_html(deals)
    print(f"[Web] 🌐 Web vitrini güncellendi: {deal_item['title']}")
    push_to_github()

def push_to_github():
    try:
        import subprocess
        subprocess.run(["git", "add", "."], cwd=WEB_DIR, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Auto-update deals"], cwd=WEB_DIR, capture_output=True)
        subprocess.run(["git", "push"], cwd=WEB_DIR, capture_output=True)
        print("[Web] 🚀 GitHub Pages (Canlı Web Sitesi) otomatik senkronize edildi!")
    except Exception as e:
        print(f"[Web] Git push uyarısı: {e}")

def render_web_html(deals: list = None):
    """
    Tüm ürünleri içeren ultra-hızlı, mobil uyumlu, estetik karanlık temalı index.html oluşturur.
    """
    if deals is None:
        deals = load_deals()

    # Statik HTML Şablonu
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flaş Fırsat ⚡ | Amazon, Trendyol & Hepsiburada Dip Fiyat Radarı</title>
    <meta name="description" content="Piyasa altı flaş indirimler, yapay zeka destekli dip fiyat takibi ve en sıcak fırsatlar!">
    <link rel="icon" type="image/jpeg" href="assets/logo.jpg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0B0D12;
            --bg-surface: #141721;
            --bg-card: #1A1E2B;
            --border: rgba(255, 255, 255, 0.08);
            --primary-orange: #FF5722;
            --primary-yellow: #FFC107;
            --accent-green: #10B981;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        body {{
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            padding-bottom: 60px;
        }}

        /* Header / Brand */
        header {{
            text-align: center;
            padding: 40px 20px 24px;
            background: radial-gradient(circle at top, rgba(255, 87, 34, 0.12) 0%, transparent 70%);
        }}

        .logo-wrap {{
            position: relative;
            display: inline-block;
            margin-bottom: 16px;
        }}

        .logo-img {{
            width: 104px;
            height: 104px;
            border-radius: 50%;
            border: 3px solid var(--primary-orange);
            box-shadow: 0 0 25px rgba(255, 87, 34, 0.35);
            object-fit: cover;
        }}

        .brand-title {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FFC107, #FF5722);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}

        .brand-desc {{
            color: var(--text-muted);
            font-size: 0.98rem;
            max-width: 500px;
            margin: 0 auto 20px;
            line-height: 1.5;
        }}

        /* Social Quick Links */
        .social-bar {{
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .social-btn {{
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
        }}

        .social-btn:hover {{
            background: var(--primary-orange);
            border-color: var(--primary-orange);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 87, 34, 0.3);
        }}

        /* Container */
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 16px;
        }}

        /* Search & Filter Bar */
        .controls-bar {{
            display: flex;
            gap: 12px;
            margin-bottom: 28px;
            flex-wrap: wrap;
        }}

        .search-box {{
            flex: 1;
            min-width: 260px;
            position: relative;
        }}

        .search-input {{
            width: 100%;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 20px;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--primary-orange);
        }}

        /* Product Cards Grid */
        .deals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}

        .deal-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        }}

        .deal-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 87, 34, 0.4);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
        }}

        .card-img-wrap {{
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
        }}

        .card-img {{
            max-height: 210px;
            width: auto;
            max-width: 100%;
            object-fit: contain;
            transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
            position: relative;
            z-index: 1;
        }}

        .deal-card:hover .card-img {{
            transform: scale(1.06);
        }}

        .badge-discount {{
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
        }}

        .badge-store {{
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
        }}

        .badge-store.store-trendyol {{
            background: rgba(242, 122, 26, 0.92);
            border-color: rgba(255, 255, 255, 0.25);
        }}

        .badge-store.store-hepsiburada {{
            background: rgba(255, 96, 0, 0.92);
            border-color: rgba(255, 255, 255, 0.25);
        }}

        .card-content {{
            padding: 20px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}

        .card-title {{
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
        }}

        .price-section {{
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 14px;
            margin-top: auto;
        }}

        .old-price {{
            color: var(--text-muted);
            text-decoration: line-through;
            font-size: 0.95rem;
        }}

        .new-price {{
            color: var(--text-main);
            font-size: 1.55rem;
            font-weight: 800;
        }}

        /* Banka & Net Maliyet Hesaplayıcı Kutusu */
        .campaign-box {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.04) 100%);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 18px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: all 0.2s ease;
        }}

        .campaign-box:hover {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(5, 150, 105, 0.08) 100%);
            border-color: rgba(16, 185, 129, 0.45);
            transform: translateY(-1px);
        }}

        .campaign-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.78rem;
        }}

        .campaign-tag {{
            background: #10B981;
            color: #064E3B;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 6px;
            font-size: 0.7rem;
            letter-spacing: 0.3px;
        }}

        .campaign-name {{
            color: #A7F3D0;
            font-weight: 600;
            font-size: 0.82rem;
        }}

        .net-cost-row {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-top: 2px;
        }}

        .net-cost-lbl {{
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
        }}

        .net-cost-val {{
            font-size: 1.25rem;
            font-weight: 800;
            color: #34D399;
            text-shadow: 0 0 12px rgba(52, 211, 153, 0.25);
        }}

        .installment-row {{
            font-size: 0.75rem;
            color: #94A3B8;
            border-top: 1px dashed rgba(255, 255, 255, 0.08);
            padding-top: 6px;
            margin-top: 2px;
        }}

        .installment-txt {{
            color: #CBD5E1;
        }}

        .buy-btn {{
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
        }}

        .buy-btn:hover {{
            background: linear-gradient(135deg, #FF6E40, #FF5722);
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(255, 87, 34, 0.4);
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            grid-column: 1 / -1;
        }}

        footer {{
            text-align: center;
            margin-top: 50px;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
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
            <a href="https://t.me/flasfirsat" target="_blank" class="social-btn">
                <span>✈️</span> Telegram Kanalı
            </a>
            <a href="https://instagram.com/flasfirsat" target="_blank" class="social-btn">
                <span>📸</span> Instagram
            </a>
            <a href="https://www.tiktok.com/@flasfirsat" target="_blank" class="social-btn">
                <span>🎵</span> TikTok
            </a>
        </div>
    </header>

    <main class="container">
        <div class="controls-bar">
            <div class="search-box">
                <input type="text" id="searchInput" class="search-input" placeholder="🔍 Ürün ara (kulaklık, mouse, monitör...)" onkeyup="filterDeals()">
            </div>
        </div>

        <div class="deals-grid" id="dealsGrid">
"""

    if not deals:
        html_content += """
            <div class="empty-state">
                <h2>⚡ Henüz fırsat eklenmedi</h2>
                <p>En sıcak indirimler birazdan burada listelenecek!</p>
            </div>
"""
    else:
        for d in deals:
            img_src = d.get("image_url") or "assets/logo.jpg"
            title = d.get("title", "Fırsat Ürünü")
            old_p = d.get("old_price", "")
            new_p = d.get("new_price", "")
            disc = d.get("discount_pct", "")
            store = d.get("store_name", "Fırsat")
            url = d.get("store_url", "#")

            # Banka Kampanyası ve Net Maliyet
            from campaign_calculator import calculate_campaign_and_net_cost
            camp_info = calculate_campaign_and_net_cost(new_p, store)
            bank_camp = d.get("bank_campaign") or camp_info["bank_campaign"]
            net_cost = d.get("net_cost") or camp_info["net_cost"]
            installment = d.get("installment") or camp_info.get("installment", "")

            # Mağaza Rozet Rengi
            store_low = store.lower()
            store_class = "store-trendyol" if "trendyol" in store_low else ("store-hepsiburada" if "hepsi" in store_low else "store-amazon")

            html_content += f"""
            <div class="deal-card" data-title="{title.lower()}">
                <div class="card-img-wrap">
                    <img src="{img_src}" alt="{title}" class="card-img" loading="lazy">
                    <span class="badge-store {store_class}">{store}</span>
                    <span class="badge-discount">{disc}</span>
                </div>
                <div class="card-content">
                    <h3 class="card-title">{title}</h3>
                    <div class="price-section">
                        <span class="old-price">{old_p}</span>
                        <span class="new-price">{new_p}</span>
                    </div>

                    <div class="campaign-box">
                        <div class="campaign-header">
                            <span class="campaign-tag">💳 EK AVANTAJ</span>
                            <span class="campaign-name">{bank_camp}</span>
                        </div>
                        <div class="net-cost-row">
                            <span class="net-cost-lbl">Net Fırsat Maliyeti:</span>
                            <span class="net-cost-val">{net_cost}</span>
                        </div>
                        <div class="installment-row">
                            <span class="installment-txt">⚡ {installment}</span>
                        </div>
                    </div>

                    <a href="{url}" target="_blank" rel="nofollow noopener sponsored" class="buy-btn">
                        🔥 Fırsata Git & Satın Al
                    </a>
                </div>
            </div>
"""

    html_content += """
        </div>
    </main>

    <footer>
        <p>© 2026 Flaş Fırsat • Fiyatlar anlık olarak değişebilir. Fırsatları kaçırmamak için Telegram'ı takip edin.</p>
    </footer>

    <script>
        function filterDeals() {
            const input = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.deal-card');
            cards.forEach(card => {
                const title = card.getAttribute('data-title');
                if (title.includes(input)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

    index_path = os.path.join(WEB_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return index_path

if __name__ == "__main__":
    ensure_web_setup()
    render_web_html()
    print(f"Web showcase generated at {WEB_DIR}/index.html")
