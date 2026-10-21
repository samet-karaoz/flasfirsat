from deal_hunter import get_curl_cmd, safe_run_subprocess
import re

queries = [
    "kahve makinesi",
    "espresso makinesi",
    "philips kahve makinesi",
    "delonghi espresso",
    "karaca hatir barista"
]

asins = set()
for q in queries:
    url = f"https://www.amazon.com.tr/s?k={q.replace(' ', '+')}"
    cmd = get_curl_cmd([
        "--compressed", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        url
    ])
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    found = re.findall(r'data-asin="(B0[0-9A-Z]{8})"', res.stdout)
    for a in found:
        if a not in asins:
            asins.add(a)

print(f"Total ASINs found: {len(asins)}")
from product_verifier import verify_amazon_product
for a in list(asins)[:10]:
    v = verify_amazon_product(a)
    if v.get("success") and v.get("in_stock") and v.get("live_price_val", 0) > 800:
        print(f"ASIN: {a} | Price: {v.get('live_price_str')} | Pill: {v.get('feature_pill')} | SoldByAmz: {v.get('is_sold_by_amazon')}")
