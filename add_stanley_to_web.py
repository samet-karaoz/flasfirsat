import os
from web_showcase import add_deal_to_web, load_deals

deal = {
    "title": "Stanley Quencher H2.0 FlowState 1.18L Pipetli Termos",
    "old_price": "2.499 TL",
    "new_price": "1.311 TL",
    "discount_pct": "-%48",
    "store_name": "Amazon TR",
    "store_url": "https://www.amazon.com.tr/dp/B0CNTV815Y?tag=flasfirsat04-21",
    "affiliate_url": "https://www.amazon.com.tr/dp/B0CNTV815Y?tag=flasfirsat04-21",
    "deal_code": "#143",
    "image_path": "assets/products/stanley_quencher_h2_0_flo_395102b3.jpg",
    "installment": "Peşin Fiyatına 3 Taksit x 437 TL",
    "badge": "DEV İNDİRİM",
    "is_lowest_30d": True
}

print("Adding deal to web...")
add_deal_to_web(deal)

deals = load_deals()
top_deal = deals[0]
print(f"Top deal now: Code: {top_deal.get('deal_code')} | Title: {top_deal.get('title')} | Price: {top_deal.get('new_price')}")
