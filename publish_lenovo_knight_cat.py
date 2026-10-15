import os
import sys
from autopilot_engine import run_autopilot_deal_cycle

deal = {
    "title": "Lenovo Legion 240Hz Gaming Monitör",
    "old_price": "8.998 TL",
    "new_price": "5.879,02 TL",
    "discount_pct": "-35%",
    "badge": "DEV İNDİRİM",
    "hook": "240Hz yenileme hızı ve 0.5ms IPS panele sahip bu seviyedeki bir oyuncu monitörü için piyasada bulunmaz bir fiyat.",
    "asin": "B0GRWGJS54",
    "feature_pill": "27 inç IPS • 240Hz • 0.5ms",
    "bank_campaign": "Nays ile 250 TL İade + 3 Taksit",
    "net_cost": "5.629 TL",
    "installment": "Peşin Fiyatına 3 Taksit x 1.959 TL",
    "image_path": os.path.abspath("assets/products/amz_B0GRWGJS54.jpg"),
    "store_name": "Amazon TR",
    "store_url": "https://www.amazon.com.tr/dp/B0GRWGJS54",
    "reaction_text": "BU FİYATA 240Hz MONİTÖR GÖRÜNCE BENİM ODAK SEVİYESİ:"
}

if __name__ == "__main__":
    print("🚀 Şövalye Kedi ile Lenovo 240Hz Monitör yayını başlatılıyor...")
    res = run_autopilot_deal_cycle(
        dry_run=False,
        slot_name="Akşam Kuşağı (Şövalye Kedi & Lenovo 240Hz)",
        force=True,
        custom_deal=deal
    )
    print("\nSONUÇ:", res.get("success"), res.get("platforms"))
