import sys, os
sys.path.insert(0, '.')
from product_verifier import verify_amazon_product

url = 'https://www.amazon.com.tr/dp/B0F7RV2Y29?tag=flasfirsat04-21'
for i in range(3):
    res = verify_amazon_product(url)
    print(f"Attempt {i+1}: success={res.get('success')} live_price_val={res.get('live_price_val')} in_stock={res.get('in_stock')}")
