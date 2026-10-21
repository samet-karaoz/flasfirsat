import sys, os
sys.path.insert(0, '.')
import json
from product_verifier import verify_amazon_product
from deal_hunter import parse_price_to_float

with open('data/deals.json', encoding='utf-8') as f:
    deals = json.load(f)

test_titles = ['Stanley Aerolight 0.47L', 'Logitech G305', 'James Donkey', 'Razer BlackShark']

for d in deals:
    title = d.get('title', '')
    if any(t in title for t in test_titles):
        url = d.get('store_url', '')
        v_res = verify_amazon_product(url)
        live_price = v_res.get('live_price_val', 0.0)
        orig_price = parse_price_to_float(d.get('new_price', ''))
        in_stock = v_res.get('in_stock', True)
        success = v_res.get('success', False)
        is_exp = d.get('is_expired', False)
        reason = d.get('expired_reason', '')
        print(f"Title: {title}")
        print(f"  URL: {url}")
        print(f"  success: {success}, in_stock: {in_stock}")
        print(f"  live_price: {live_price}, orig_price: {orig_price}")
        print(f"  is_expired: {is_exp}, reason: {reason}")
        print("-" * 50)
