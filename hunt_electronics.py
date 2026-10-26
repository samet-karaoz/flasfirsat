import os
from deal_hunter import hunt_amazon_deals

print("Hunting live Amazon TR deals in Consumer Electronics...")
deals = hunt_amazon_deals(limit=8, category="audio", min_discount=20)
print(f"Found {len(deals)} audio deals:")
for i, d in enumerate(deals):
    print(f"{i+1}. {d.get('title')} | Old: {d.get('old_price')} | New: {d.get('new_price')} | Disc: {d.get('discount_pct')} | URL: {d.get('store_url')}")
