import os
import sys
import time

sys.path.append('.')
from deal_bot import process_deal_to_reel

deal = {
    "title": "Dell 24\" 200Hz 1ms IPS Gaming Monitör",
    "old_price": "5.999 TL",
    "new_price": "4.449 TL",
    "discount_pct": "-26%",
    "discount_val": 26,
    "store_name": "Amazon TR",
    "store_url": "https://www.amazon.com.tr/dp/B0FHHVD75B?tag=flasfirsat04-21",
    "seller_badge": "AMAZON TR RESMİ SATICI",
    "image_path": "assets/products/dell_200hz_gaming_monitor.jpg",
    "installment": "Peşin Fiyatına 3 Taksit x 1.483 TL",
    "killer_hook": "⚡ 4.449 TL'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ! ⚡",
    "feature_pill": "4.449 TL'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ!",
    "has_verified_old_price": True,
    "is_lowest_30d": True,
    "market_badge": "SON 30 GÜNÜN EN DÜŞÜĞÜ",
    "reaction_text": "200Hz IPS MONİTÖRÜ 4.449 TL'YE GÖREN BİZİM TAYFA:"
}

print("🚀 Dell 200Hz Gaming Monitör fırsat paketi üretiliyor...")
res = process_deal_to_reel(
    deal,
    upload=True,
    require_approval=True,
    meme_choice="cat_vibing.mp4"
)
print("SONUÇ:", res)
