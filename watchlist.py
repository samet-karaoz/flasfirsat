import os
import re
import json
from datetime import datetime
from config import BASE_DIR, TEMP_DIR
from product_verifier import verify_amazon_product
from deal_hunter import parse_price_to_float

WATCHLIST_FILE = os.path.join(BASE_DIR, "data", "watchlist.json")

DEFAULT_WATCHLIST = [
    {
        "asin": "B08H99BPJN",
        "title": "Sony PS5 DualSense Kablosuz Kol",
        "store": "Amazon TR",
        "base_price": 3499.0,
        "target_price": 2499.0,
        "drop_threshold_pct": 25.0,
        "url": "https://www.amazon.com.tr/dp/B08H99BPJN"
    },
    {
        "asin": "B07W4DH8JW",
        "title": "Logitech G G102 Lightsync Gaming Mouse",
        "store": "Amazon TR",
        "base_price": 899.0,
        "target_price": 549.0,
        "drop_threshold_pct": 30.0,
        "url": "https://www.amazon.com.tr/dp/B07W4DH8JW"
    },
    {
        "asin": "B0H5VQFVTG",
        "title": "Lenovo Legion R25f-30 Gaming Monitör",
        "store": "Amazon TR",
        "base_price": 6499.0,
        "target_price": 5199.0,
        "drop_threshold_pct": 20.0,
        "url": "https://www.amazon.com.tr/dp/B0H5VQFVTG"
    },
    {
        "asin": "B0B15VJZQZ",
        "title": "SteelSeries Arctis Nova 1 Oyuncu Kulaklığı",
        "store": "Amazon TR",
        "base_price": 2199.0,
        "target_price": 1499.0,
        "drop_threshold_pct": 25.0,
        "url": "https://www.amazon.com.tr/dp/B0B15VJZQZ"
    }
]

def load_watchlist() -> list:
    """İzleme listesini yükler, yoksa varsayılan popüler ürünlerle başlatır."""
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    save_watchlist(DEFAULT_WATCHLIST)
    return DEFAULT_WATCHLIST

def save_watchlist(items: list):
    """İzleme listesini kaydeder."""
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def add_to_watchlist(asin_or_url: str, title: str, base_price: float, drop_threshold_pct: float = 25.0) -> dict:
    """Yeni bir ürünü izleme listesine ekler."""
    asin_match = re.search(r"([A-Z0-9]{10})", asin_or_url, re.IGNORECASE)
    asin = asin_match.group(1).upper() if asin_match else asin_or_url
    url = f"https://www.amazon.com.tr/dp/{asin}" if len(asin) == 10 else asin_or_url

    items = load_watchlist()
    for it in items:
        if it.get("asin") == asin:
            it["base_price"] = base_price
            it["drop_threshold_pct"] = drop_threshold_pct
            save_watchlist(items)
            return it

    new_item = {
        "asin": asin,
        "title": title,
        "store": "Amazon TR",
        "base_price": float(base_price),
        "target_price": round(float(base_price) * (1 - drop_threshold_pct / 100), 2),
        "drop_threshold_pct": float(drop_threshold_pct),
        "url": url,
        "added_at": datetime.now().isoformat()
    }
    items.append(new_item)
    save_watchlist(items)
    return new_item

def check_watchlist_drops(min_drop_pct: float = 20.0) -> list:
    """
    İzleme listesindeki popüler ürünleri canlı sorgular.
    Fiyatı taban fiyata göre %20 veya daha fazla düşmüş fırsatları tespit eder.
    """
    items = load_watchlist()
    triggered_deals = []

    print(f"\n[İzleme Listesi] 📡 {len(items)} adet takip edilen ürün canlı kontrol ediliyor...")

    for item in items:
        url = item.get("url")
        base_p = float(item.get("base_price", 0))
        asin = item.get("asin", "")

        res = verify_amazon_product(url or asin)
        if not res.get("success") or not res.get("in_stock"):
            continue

        live_price = res.get("live_price_val", 0)
        if live_price <= 0 or base_p <= 0:
            continue

        # Düşüş oranı
        if live_price < base_p:
            drop_pct = round(((base_p - live_price) / base_p) * 100)
            threshold = item.get("drop_threshold_pct", min_drop_pct)

            print(f"[İzleme] {item['title']}: Taban {base_p:.0f} TL -> Canlı {live_price:.0f} TL (-%{drop_pct})")

            if drop_pct >= threshold:
                print(f"[İzleme] 🚨 FİYAT DÜŞÜŞÜ ALARMI! {item['title']} -%{drop_pct} DÜŞTÜ!")
                deal_data = {
                    "title": item["title"],
                    "old_price": f"{int(base_p):,} TL".replace(",", "."),
                    "new_price": f"{int(live_price):,} TL".replace(",", "."),
                    "discount_pct": f"-{drop_pct}%",
                    "badge": "FİYAT ÇÖKÜŞÜ" if drop_pct >= 35 else "DİP FİYAT",
                    "hook": f"Takip listemizdeki ürünün fiyatı aniden %{drop_pct} düştü!",
                    "store_name": item.get("store", "Amazon TR"),
                    "store_url": url,
                    "feature_pill": res.get("feature_pill", ""),
                    "is_lowest_30d": res.get("is_lowest_30d", False),
                    "coupon_info": res.get("coupon_text", "")
                }
                triggered_deals.append(deal_data)

    return triggered_deals

if __name__ == "__main__":
    drops = check_watchlist_drops(min_drop_pct=15.0)
    print(f"\nToplam {len(drops)} adet fiyat düşüş alarmı tetiklendi.")
    for d in drops:
        print(f"- {d['title']}: {d['old_price']} -> {d['new_price']} ({d['discount_pct']})")
