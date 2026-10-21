import urllib.request
import re
from product_verifier import verify_amazon_product
from deal_hunter import get_curl_cmd, safe_run_subprocess

# Let's search for in-stock espresso / coffee machines on Amazon TR
url = "https://www.amazon.com.tr/s?k=espresso+makinesi&rh=p_6%3AA1UNQM1SR2CHM%2Cp_n_deal_type%3A26901202031" # Amazon TR satıcılı indirimli
cmd = get_curl_cmd([
    "-s", "-L",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    url
])
res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
asins = re.findall(r'data-asin="(B0[0-9A-Z]{8})"', res.stdout)
print("Found ASINs on Amazon TR deals:", asins[:8])

for asin in asins[:6]:
    v = verify_amazon_product(asin)
    if v.get("success") and v.get("in_stock") and v.get("live_price_val", 0) > 1000:
        print(f"VALID DEAL -> ASIN: {asin} | Price: {v.get('live_price_str')} | Strike: {v.get('real_strike_val')} | Pill: {v.get('feature_pill')}")
