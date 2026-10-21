from config import get_curl_cmd, safe_run_subprocess, TEMP_DIR
import os
import re

url = "https://www.amazon.com.tr/dp/B06WGTZ874"
cmd = get_curl_cmd([
    "-s", "-L",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    url
])
res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = res.stdout

img_m = re.search(r'"hiRes":"([^"]+)"', html) or re.search(r'"large":"([^"]+)"', html)
img_url = img_m.group(1) if img_m else "https://m.media-amazon.com/images/I/71Ww2zF7k-L._AC_SL1500_.jpg"

print("Image URL:", img_url)
out_img = os.path.join(TEMP_DIR, "delonghi_dedica_prod.jpg")
dl_cmd = get_curl_cmd(["-s", "-L", img_url, "-o", out_img])
safe_run_subprocess(dl_cmd)
print("Saved image to:", out_img, "Exists:", os.path.exists(out_img), "Size:", os.path.getsize(out_img) if os.path.exists(out_img) else 0)
