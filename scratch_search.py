import urllib.request
import json
import re
from config import get_curl_cmd, safe_run_subprocess

# Let's search Amazon TR for a popular product
search_queries = [
    "cosori airfryer",
    "philips airfryer",
    "delonghi espresso makinesi",
    "karaca kahve makinesi barista",
    "soundcore q30",
    "anker soundcore motion",
    "logitech mx master 3s",
    "steelseries apex 3 tkl"
]

results = []
for q in search_queries[:4]:
    url = f"https://www.amazon.com.tr/s?k={urllib.parse.quote(q)}"
    cmd = get_curl_cmd(["-s", "-L", url])
    res = safe_run_subprocess(cmd, capture_output=True, text=True, timeout=10)
    html = res.stdout
    # find asin, title, price
    items = re.findall(r'data-asin="([B0-9A-Z]{10})".*?class="a-size-base-plus a-color-base a-text-normal">([^<]+)<.*?class="a-price-whole">([^<]+)<span class="a-price-fraction">([^<]+)<', html, re.DOTALL)
    for asin, title, whole, frac in items[:2]:
        price_str = f"{whole},{frac} TL"
        # look for basis/strike price
        basis_match = re.search(rf'data-asin="{asin}".*?class="a-price a-text-price".*?class="a-offscreen">([^<]+)<', html, re.DOTALL)
        old_price = basis_match.group(1) if basis_match else ""
        results.append({
            "asin": asin,
            "title": title.strip(),
            "price": price_str,
            "old_price": old_price,
            "url": f"https://www.amazon.com.tr/dp/{asin}"
        })

print(f"Found {len(results)} items:")
for r in results:
    print(r)
