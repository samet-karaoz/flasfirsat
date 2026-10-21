import urllib.parse
from config import get_curl_cmd, safe_run_subprocess
import re
import json

asins = {
    "Delonghi_Dedica": "B06WGTZ874", # Delonghi Dedica EC685.M
    "Cosori_Airfryer": "B0936FGLQS", # Cosori 5.5L
    "Anker_Q30": "B08HMWZBXC",      # Anker Soundcore Q30
    "Philips_LatteGo": "B07MMS6WVD"  # Philips LatteGo EP2231
}

for name, asin in asins.items():
    url = f"https://www.amazon.com.tr/dp/{asin}"
    cmd = get_curl_cmd([
        "--compressed", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        url
    ])
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    html = res.stdout
    title_m = re.search(r'<span id="productTitle"[^>]*>([^<]+)</span>', html)
    title = title_m.group(1).strip() if title_m else "Not found"
    
    # price
    price_m = re.search(r'class="a-price-whole">([^<]+)<span class="a-price-fraction">([^<]+)<', html)
    price = f"{price_m.group(1)},{price_m.group(2)} TL" if price_m else "No price"
    
    basis_m = re.search(r'class="basisPrice".*?class="a-offscreen">([^<]+)<', html, re.DOTALL)
    basis = basis_m.group(1) if basis_m else "No basis"
    
    img_m = re.search(r'"hiRes":"([^"]+)"', html) or re.search(r'"large":"([^"]+)"', html)
    img = img_m.group(1) if img_m else "No img"
    
    print(f"[{name}] Title: {title[:40]} | Price: {price} | Basis: {basis} | ASIN: {asin} | Img: {img[:30] if img else 'None'}")
