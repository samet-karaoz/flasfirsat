import os
import re
import json
import base64
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
from config import BASE_DIR, TEMP_DIR, GEMINI_API_KEY, get_curl_cmd

MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest"
]

DEFAULT_CHANNELS = [
    "dh_sicakfirsatlar",
    "firsatalemi",
    "firsatpaylasim",
    "indirimkaplani",
    "teknolojifirsatlari",
    "firsatkulubu"
]

BORING_REGEX = re.compile(
    r"(şarj\s*aleti|şarj\s*cihazı|şarj\s*kablosu|şarj\s*kiti|şarj\s*istasyonu|\bşarj\b|\bkablo(su)?\b(?!lu)|"
    r"adaptör[üu]?|kılıf[ıi]?|ekran\s*koruyucu|koruyucu\s*cam|temizleme|temizleyici|çorap|askı|tutucu|"
    r"(?<!monitör\s)(?<!laptop\s)stand[ıi]?|"
    r"çevirici|dönüştürücü|deterjan|bez|havlu|bulaşık|yumuşatıcı|şampuan|diş\s*fırçası|mendil|pijama|çanta(sı)?|"
    r"tartı(sı)?|terazi(si)?|baskül|ölçüm|termometre|ateş\s*ölçer|"
    r"saklama\s*kabı|kavanoz|rende|süzgeç|açacak|maşa|spatula|kesme\s*tahtası|bulaşık|sünger|"
    r"flaş\s*bellek|usb\s*bellek|flash\s*bellek|hafıza\s*kartı|sd\s*kart|microsd|flash\s*drive|usb\s*drive|kart\s*okuyucu|"
    r"bebek|mama(sı)?|süt[üu]?|devam\s*sütü|vitamin|omega|balık\s*yağı|takviye|"
    r"bisküvi|kek|gofret|çikolata|cips|makarna|salça|bakliyat|kuruyemiş|çekirdek|ton\s*balığı|baharat|"
    r"motosiklet|lastik|kask(ı)?|disk\s*kilidi|saç\s*toniği|sabun|"
    r"tencere|tava|yastık|çarşaf|nevresim|ayakkabı|terlik|bot|parfüm|kolonya|güneş\s*kremi|serum|makyaj|"
    r"tişört|pantolon|gömlek|\bkahve\b(?!\s*makine)|\bpil\b|kalem\s*pil|alkalin|şarj\s*edilebilir\s*pil|"
    r"kartuş|toner|koli|kutu|folyo|termal|termal\s*macun|vida|aparat[ıi]?|"
    r"filtre(si)?|kireç|su\s*arıtma|aquaclean|maxtra|toz\s*torbası|yedek\s*filtre|yedek\s*parça|yedek\s*bıçak|"
    r"tıraş\s*başlığı|conta|temizleme\s*tableti|kireç\s*çözücü|sarf\s*malzeme)",
    re.IGNORECASE
)

VAGUE_TITLE_REGEX = re.compile(
    r"(ürünleri|modelleri|çeşitleri|fırsatları|indirimleri|kampanyası|seçili\s*ürünler|"
    r"\bpetshop\b|evcil\s*hayvan|köpek\s*mam|kedi\s*mam|"
    r"günün\s*(fırsatı|indirimi)|süper\s*fırsat|büyük\s*indirim|fırsat\s*ürünü|"
    r"kadın\s*giyim|erkek\s*giyim|çocuk\s*giyim|ayakkabı\s*modelleri|"
    r"yüz\s*nemlendirici|şampuan\s*çeşit|bebek\s*bezi)",
    re.IGNORECASE
)

def is_vague_deal(title: str, text: str = "") -> bool:
    """
    Belirli tek bir somut ürüne ait olmayan, genel kategori/kampanya duyurusu
    olan belirsiz fırsatları eler (Örn: 'Petshop Ürünü', 'Columbia Ürünleri', 'Televizyon Modelleri').
    """
    t = (title or "").strip()
    if not t or len(t) < 4:
        return True

    if VAGUE_TITLE_REGEX.search(t) or BORING_REGEX.search(t):
        return True

    single_brands = ["columbia", "adidas", "nike", "puma", "zara", "mango", "defacto", "koton", "mavi", "lcw"]
    if t.lower() in single_brands or any(t.lower() == f"{b} ürünleri" or t.lower() == f"{b} ürünü" for b in single_brands):
        return True

    if text:
        text_low = text.lower()
        if any(phrase in text_low for phrase in ["tüm ürünlerde", "seçili ürünlerde", "koleksiyonunda", "kategorisinde indirim"]):
            tech_indicators = ["pro", "max", "ultra", "plus", "gb", "hz", "inch", "inç", "v2", "v3", "rgb", "anc", "gen"]
            if not any(k in t.lower() for k in tech_indicators):
                return True

    return False

HIGH_DEMAND_KEYWORDS = [
    # Konsol & Gaming Donanım
    "playstation", "ps5", "ps4", "xbox", "nintendo", "switch",
    "dualsense", "controller", "oyun kolu", "gamepad", "direksiyon", "g29", "g923",
    # Ses & Kulaklıklar
    "kulaklık", "headset", "airpods", "buds", "earbuds", "soundcore", "anc", "bluetooth kulaklık", "hoparlör",
    # Oyuncu Çevre Birimleri
    "mouse", "oyuncu faresi", "klavye", "keyboard", "mekanik klavye", "mousepad",
    # Bilgisayar & Ekran
    "monitör", "monitor", "curved", "gaming laptop", "laptop", "bilgisayar", "ssd", "nvme",
    # Yaşam, Mutfak & Trend Teknolojiler
    "stanley", "termos", "airfryer", "kahve makinesi", "oneblade", "tıraş",
    # Güçlü Markalar
    "apple", "razer", "logitech", "steelseries", "hyperx", "asus", "rog", "msi", "sony", "samsung", "jbl", "corsair", "anker", "philips"
]

def get_product_subtype(title: str) -> str:
    """
    Ürünün alt kategorisini tespit eder.
    Aynı alt kategorinin (örneğin arka arkaya kol/gamepad veya fare) tekrarlanmasını engeller.
    """
    t = (title or "").lower()
    if any(k in t for k in ["gamepad", "controller", "dualsense", "joycon", "oyun kolu"]) or re.search(r"\bkol(u)?\b", t):
        return "gamepad"
    if any(k in t for k in ["kulaklık", "headset", "earbuds", "airpods", "buds"]):
        return "headset"
    if any(k in t for k in ["mousepad", "mouse pad"]):
        return "mousepad"
    if any(k in t for k in ["mouse", "fare"]):
        return "mouse"
    if any(k in t for k in ["klavye", "keyboard"]):
        return "keyboard"
    if any(k in t for k in ["monitör", "monitor", "ekran"]):
        return "monitor"
    if any(k in t for k in ["hoparlör", "speaker", "soundbar"]):
        return "speaker"
    if any(k in t for k in ["termos", "airfryer", "fritöz", "kahve makinesi"]):
        return "lifestyle"
    if any(k in t for k in ["tıraş", "oneblade", "epilasyon"]):
        return "grooming"
    if any(k in t for k in ["ssd", "nvme", "disk"]):
        return "storage"
    return "general"

def parse_price_to_float(price_str: str) -> float:
    """Türkçe para birimi metinlerini ('1.949,00 TL' vb.) floata dönüştürür."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r"[^\d,.]", "", str(price_str)).strip()
    if not cleaned:
        return 0.0
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 1 and len(parts[-1]) == 3:
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except Exception:
        return 0.0

def get_deal_discount_pct(deal: dict) -> int:
    """Fırsatın gerçek indirim oranını (%) hesaplar veya ayıklar."""
    raw_pct = str(deal.get("discount_pct") or "")
    m = re.search(r"(\d+)", raw_pct)
    if m:
        pct = int(m.group(1))
        if 5 <= pct <= 95:
            return pct
            
    old_p = parse_price_to_float(deal.get("old_price", ""))
    new_p = parse_price_to_float(deal.get("new_price", ""))
    if old_p > 0 and new_p > 0 and old_p > new_p:
        calc_pct = round(((old_p - new_p) / old_p) * 100)
        if 5 <= calc_pct <= 95:
            return calc_pct
    return 0

def get_deal_savings_tl(deal: dict) -> float:
    """Eski fiyat ile yeni fiyat arasındaki TL cinsinden net tasarrufu hesaplar."""
    old_p = parse_price_to_float(deal.get("old_price", ""))
    new_p = parse_price_to_float(deal.get("new_price", ""))
    return max(0.0, old_p - new_p)

def calculate_deal_viral_score(deal: dict) -> float:
    """
    Fırsat Puanlama (Deal Scoring) Motoru:
    Sosyal medyada (Reels/Shorts) viral olma ve satışa dönüşme potansiyelini 0-100 puan üzerinden hesaplar:
    1. Net TL Tasarrufu (%40 ağırlık): 1.000 TL+ ve 2.500 TL+ gibi dev tasarruflara dev öncelik verir.
    2. İndirim Yüzdesi (%30 ağırlık): %30-%50 arası yüksek oranlar.
    3. Viral / Talep Gören Kategori ve Marka Bonusu (%30 ağırlık): Monitör, Gaming, Apple, Kulaklık, Mouse vb.
    4. Düşük Bütçeli Sarf Malzemesi Cezası: Fiyatı < 500 TL ve kârı < 300 TL olan sönük ürünleri geriye atar.
    """
    pct = get_deal_discount_pct(deal)
    savings_tl = get_deal_savings_tl(deal)
    new_p = parse_price_to_float(deal.get("new_price", ""))
    title = str(deal.get("title") or "").lower()

    score = 0.0

    # 1. Net TL Tasarruf Puanı (Maks 40 puan)
    if savings_tl >= 2500:
        score += 40
    elif savings_tl >= 1500:
        score += 35
    elif savings_tl >= 800:
        score += 28
    elif savings_tl >= 400:
        score += 20
    elif savings_tl >= 200:
        score += 10
    else:
        score += 2

    # 2. İndirim Yüzdesi Puanı (Maks 30 puan)
    if pct >= 45:
        score += 30
    elif pct >= 35:
        score += 25
    elif pct >= 25:
        score += 18
    elif pct >= 15:
        score += 10
    else:
        score += 5

    # 3. Viral / Yüksek Talep Kategori ve Marka Bonusu (Maks 30 puan)
    VIRAL_KEYWORDS = [
        "monitör", "monitor", "gaming", "oyuncu", "240hz", "165hz", "144hz", "ips", "oled",
        "apple", "airtag", "airpods", "iphone", "ipad", "macbook",
        "playstation", "ps5", "xbox", "gamepad", "kolu",
        "razer", "logitech", "steelseries", "hyperx", "corsair", "asus rog",
        "kulaklık", "headset", "mouse", "klavye",
        "kahve", "espresso", "delonghi", "philips", "nespresso",
        "robot", "süpürge", "dyson", "roborock", "dreame",
        "anker", "jbl", "sony", "marshall",
        "lenovo", "legion", "msi", "acer nitro", "hp victus"
    ]
    if any(k in title for k in VIRAL_KEYWORDS):
        score += 30

    # 4. Düşük Bütçeli / Heyecansız Ürün Cezası
    # 500 TL altı ve tasarrufu 300 TL'den az olan ürünler Reels için heyecan yaratmaz
    if new_p < 500 and savings_tl < 300:
        score -= 40

    return score

MIN_PRODUCT_PRICE_TL = 350  # 350 TL altındaki küçük kırtasiye/ıvır zıvır ürünleri ele

def detect_store(url: str, text: str = "") -> str:
    """Ürün linkinden veya metninden mağazayı (Trendyol, Hepsiburada, Amazon TR) tespit eder."""
    url_low = (url or "").lower()
    text_low = (text or "").lower()
    if "amazon.com.tr" in url_low or "amzn.to" in url_low or "amzn.eu" in url_low or "fenom.io" in url_low or "amazon" in text_low:
        return "Amazon TR"
    elif "trendyol.com" in url_low or "ty.gl" in url_low or "trendyol" in text_low:
        return "Trendyol"
    elif "hepsiburada.com" in url_low or "app.hb.biz" in url_low or "hepsiburada" in text_low:
        return "Hepsiburada"
    return "Fırsat Ürünü"

def call_gemini(prompt: str, json_mode: bool = True, image_path: str = None) -> dict:
    """
    Gemini modellerine sorgu atar, çoklu model fallback ve güvenli JSON ayrıştırma uygular.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    parts = [{"text": prompt}]
    if image_path and os.path.exists(image_path):
        mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})

    payload = {"contents": [{"parts": parts}]}
    req_file = os.path.join(TEMP_DIR, "gemini_hunter_req.json")
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    for model in MODEL_CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        cmd = get_curl_cmd(["--max-time", "15", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", f"@{req_file}", url])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        
        try:
            data = json.loads(res.stdout)
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if not json_mode:
                    return text
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text.strip())
        except Exception:
            continue

    return None

def download_file(url: str, output_path: str) -> bool:
    """curl ile dosya indirir."""
    cmd = get_curl_cmd(["--max-time", "15", "-s", "-L", url, "-o", output_path])
    res = subprocess.run(cmd)
    return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000

AMAZON_CATALOG_SOURCES = [
    ("GAMING", "https://www.amazon.com.tr/gp/bestsellers/videogames"),
    ("ELEKTRONİK", "https://www.amazon.com.tr/gp/bestsellers/electronics"),
    ("BİLGİSAYAR", "https://www.amazon.com.tr/gp/bestsellers/computers"),
    ("MONİTÖR", "https://www.amazon.com.tr/gp/bestsellers/computers/12601904031"),
    ("AKILLI_EV", "https://www.amazon.com.tr/gp/bestsellers/electronics/13735824031")
]

CAT_ROTATION_FILE = os.path.join(TEMP_DIR, "amazon_cat_rot.txt")

def get_rotated_amazon_catalogs():
    idx = 0
    try:
        if os.path.exists(CAT_ROTATION_FILE):
            with open(CAT_ROTATION_FILE, "r") as f:
                idx = int(f.read().strip())
    except Exception:
        idx = 0
    
    rotated = AMAZON_CATALOG_SOURCES[idx:] + AMAZON_CATALOG_SOURCES[:idx]
    next_idx = (idx + 1) % len(AMAZON_CATALOG_SOURCES)
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(CAT_ROTATION_FILE, "w") as f:
            f.write(str(next_idx))
    except Exception:
        pass
    return rotated

def hunt_amazon_deals(limit: int = 3, category: str = "all", exclude_urls: set = None, exclude_subtypes: set = None, min_discount: int = 25) -> list:
    """
    Doğrudan amazon.com.tr üzerinden yüksek talep gören viral Gaming, PC, Donanım, Ses ve Trend Yaşam ürünlerini çeker.
    Sıkıcı aksesuarları filtreler, ürünün gerçek Türkiye piyasa fiyatını ve indirimini analiz eder.
    Sadece belirlenen minimum indirim oranını (min_discount) karşılayan ürünleri seçer.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if category in ("all", "gaming", "auto"):
        url_categories = get_rotated_amazon_catalogs()
    elif category == "computers":
        url_categories = [("BİLGİSAYAR", "https://www.amazon.com.tr/gp/bestsellers/computers")]
    elif category == "monitors":
        url_categories = [("MONİTÖR", "https://www.amazon.com.tr/gp/bestsellers/computers/12601904031")]
    elif category == "electronics":
        url_categories = [("ELEKTRONİK", "https://www.amazon.com.tr/gp/bestsellers/electronics")]
    elif category == "kitchen":
        url_categories = [("MUTFAK_YAŞAM", "https://www.amazon.com.tr/gp/bestsellers/kitchen")]
    else:
        url_categories = get_rotated_amazon_catalogs()

    deals = []
    seen_subtypes = set(exclude_subtypes) if exclude_subtypes else set()

    for cat_name, target_url in url_categories:
        if len(deals) >= limit:
            break

        print(f"[Deal Hunter] Doğrudan Amazon TR ({cat_name}) taranıyor: {target_url}...")
        cmd = get_curl_cmd([
            "--compressed", "-s", "-L",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-H", "Accept-Language: tr-TR,tr;q=0.9", target_url
        ])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            continue

        soup = BeautifulSoup(res.stdout, "html.parser")
        items = soup.find_all("div", class_="p13n-sc-uncoverable-faceout")

        for it in items:
            if len(deals) >= limit:
                break

            title_el = it.find("div", class_=lambda c: c and "line-clamp" in c) or it.find("span")
            price_el = it.find("span", class_=lambda c: c and "price" in c)
            img_el = it.find("img")
            link_el = it.find("a", href=re.compile(r"/dp/"))

            if not (title_el and price_el and img_el and link_el):
                continue

            raw_title = title_el.text.strip()
            raw_price = price_el.text.strip()

            # 1. Sıkıcı veya düşük ilgi gören aksesuarları ele
            if BORING_REGEX.search(raw_title):
                continue

            # 2. Alt tip anti-tekrar koruması (örn: peş peşe 2 kol/gamepad veya 2 fare gelmez)
            raw_subtype = get_product_subtype(raw_title)
            if raw_subtype != "general" and raw_subtype in seen_subtypes:
                print(f"[Deal Hunter] ⏭️ Çeşitlilik Koruması ({raw_subtype} zaten var/yasaklı): {raw_title[:38]}")
                continue

            # 3. Minimum Fiyat Kontrolü (350 TL altındaki küçük ıvır zıvırları atla)
            try:
                price_clean = re.sub(r"[^\d]", "", raw_price.split(",")[0])
                if price_clean and int(price_clean) < MIN_PRODUCT_PRICE_TL:
                    continue
            except Exception:
                pass

            # 4. Temiz ve doğrudan tıklanabilir Amazon linki (/dp/ASIN)
            href = link_el.get("href", "")
            asin_match = re.search(r"/dp/([A-Z0-9]{10})", href, re.IGNORECASE)
            if asin_match:
                prod_url = f"https://www.amazon.com.tr/dp/{asin_match.group(1).upper()}"
            else:
                prod_url = "https://www.amazon.com.tr" + href.split("?")[0]

            # Daha önce üretilmişse pas geç
            if exclude_urls and any(prod_url in ex or (asin_match and asin_match.group(1) in ex) for ex in exclude_urls):
                continue

            raw_img = img_el.get("src", "")
            big_img = re.sub(r'\._AC_.*?_\.', '._AC_SL1000_.', raw_img)

            if len(raw_title) < 6 or "TL" not in raw_price:
                continue

            print(f"[Deal Hunter] Aday Ürün Analiz Ediliyor ({cat_name}): {raw_title[:45]} | {raw_price}")

            prompt = f"""Şu popüler Amazon Türkiye ürününün gerçek piyasa değerini ve indirimini analiz et:
Ürün: {raw_title}
Amazon Satış Fiyatı: {raw_price}

GÖREV:
1. Bu ürünün Türkiye teknoloji/perakende pazarındaki gerçek piyasa / tavsiye edilen liste satış fiyatını (MSRP) belirle.
2. Amazon fiyatı ({raw_price}) ile piyasa liste fiyatı arasındaki indirim oranını hesapla.
3. Gerçekçi hesapla (örn: Piyasa 2.499 TL, Amazon 1.499 TL ise -%40).

Şu JSON formatında döndür:
{{
  "title": "Ürünün kısa, vurucu ve net adı (maksimum 30 karakter, örn: Asus TUF Monitör, Stanley Termos, Razer Basilisk Mouse vb.)",
  "old_price": "Türkiye piyasa/liste fiyatı (örn: 2.499 TL)",
  "new_price": "{raw_price}",
  "discount_pct": "Hesaplanan indirim yüzdesi (örn: -38% veya -45%)",
  "badge": "İndirim %45 üzeriyse 'DİP FİYAT', %35 üzeriyse 'DEV İNDİRİM', diğerinde 'AMAZON FIRSATI'",
  "hook": "Kullanıcıların neden bu ürüne akın ettiğini anlatan tek cümle"
}}
"""
            deal_data = call_gemini(prompt, json_mode=True)
            if not deal_data or not deal_data.get("title"):
                continue

            # Minimum İndirim Oranı Kontrolü
            pct_val = get_deal_discount_pct(deal_data)
            deal_data["discount_val"] = pct_val
            if pct_val < min_discount:
                print(f"[Deal Hunter] ⏭️ Düşük İndirim Elendi (-%{pct_val} < -%{min_discount}): {deal_data.get('title')}")
                continue

            final_subtype = get_product_subtype(deal_data.get("title", raw_title))
            if final_subtype != "general":
                seen_subtypes.add(final_subtype)

            prod_id = asin_match.group(1) if asin_match else f"{len(deals)+1}_{int(datetime.now().timestamp())}"
            if asin_match:
                asin = asin_match.group(1).upper()
                deal_data["asin"] = asin
                try:
                    from price_tracker import record_price
                    price_f = parse_price_to_float(raw_price)
                    if price_f > 0:
                        record_price(asin, "Amazon TR", deal_data.get("title", raw_title), price_f)
                except Exception:
                    pass

            img_path = os.path.join(TEMP_DIR, f"amz_{prod_id}.jpg")
            if not download_file(big_img, img_path):
                if not download_file(raw_img, img_path):
                    continue

            from campaign_calculator import calculate_campaign_and_net_cost
            camp = calculate_campaign_and_net_cost(deal_data.get("new_price", ""), "Amazon TR")
            deal_data["bank_campaign"] = camp["bank_campaign"]
            deal_data["net_cost"] = camp["net_cost"]
            deal_data["installment"] = camp["installment"]

            deal_data["image_path"] = img_path
            deal_data["source_channel"] = f"Amazon TR ({cat_name})"
            deal_data["store_name"] = "Amazon TR"
            deal_data["store_url"] = prod_url
            deals.append(deal_data)
            print(f"[Deal Hunter] 🔥 Yüksek İndirim Yakalandı: {deal_data['title']} | {deal_data['new_price']} (-%{pct_val}, Net: {camp['net_cost']}) | Link: {prod_url}")

    return deals

def hunt_online_deals(limit: int = 5, channels: list = None, exclude_urls: set = None, min_discount: int = 25) -> list:
    """
    Doğrudan Amazon TR ve sıcak fırsat kanallarından gerçek zamanlı indirimleri tarar,
    ürün görsellerini indirir ve sadece belirlenen indirim eşiğini (min_discount) geçenleri listeler.
    """
    if channels is None:
        channels = DEFAULT_CHANNELS

    os.makedirs(TEMP_DIR, exist_ok=True)
    collected_deals = []

    print(f"[Deal Hunter] {len(channels)} kanaldan taze indirimler taranıyor (Min İndirim: %{min_discount})...")

    for ch in channels:
        if len(collected_deals) >= limit:
            break

        url = f"https://t.me/s/{ch}"
        cmd = get_curl_cmd(["-s", url])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            continue

        soup = BeautifulSoup(res.stdout, "html.parser")
        msgs = soup.select("div.tgme_widget_message_wrap")

        # En yeni mesajlardan geriye doğru tara (en taze 20 mesaj)
        for m in list(reversed(msgs))[:20]:
            if len(collected_deals) >= limit:
                break

            text_el = m.select_one("div.tgme_widget_message_text")
            photo_el = m.select_one("a.tgme_widget_message_photo_wrap")

            if not text_el or not photo_el:
                continue

            raw_text = text_el.text.strip()
            # Sıkıcı ürünleri ele
            if BORING_REGEX.search(raw_text):
                continue

            # Fiyat içeren mesajları seç
            if "TL" not in raw_text and "tl" not in raw_text and "%" not in raw_text:
                continue

            # Foto URL çıkar
            style = photo_el.get("style", "")
            photo_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if not photo_match:
                continue
            photo_url = photo_match.group(1)

            # Link çıkar: Hem metinden hem de mesaj altındaki buton linklerinden topla
            all_links = [a.get("href") for a in m.select("a") if a.get("href") and "t.me" not in a.get("href")]
            link_match = re.search(r"(https?://\S+)", raw_text)
            if link_match and link_match.group(1) not in all_links:
                all_links.append(link_match.group(1))

            store_url = all_links[0] if all_links else ""
            if not store_url:
                continue

            if exclude_urls and any(store_url in ex for ex in exclude_urls):
                continue

            # Mağaza tespit et (Amazon TR, Trendyol, Hepsiburada)
            store_name = detect_store(store_url, raw_text)

            # AI ile analiz et
            prompt = f"""Şu Türkçe fırsat/indirim mesajından ürün bilgilerini JSON olarak çıkar:
\"\"\"{raw_text}\"\"\"

ÖNEMLİ KURALLAR:
1. Bu mesaj tek bir somut ve belirli bir ürüne mi ait (örn: 'Sony WH-1000XM4 Kulaklık', 'Lenovo R25f-30 Monitör')?
   Yoksa birden fazla ürünü kapsayan genel bir kategori/marka duyurusu mu (örn: 'Columbia Ürünleri', 'Petshop Ürünü', 'Televizyon Modelleri')?
2. Eğer genel bir kategori, birden fazla ürün veya belirsiz bir kampanya ise "is_specific_product" alanını false yap!
3. Belirli tek bir ürünse "title" alanına NET marka ve model adını yaz (maksimum 30 karakter).

Şu JSON formatında döndür:
{{
  "is_specific_product": true,
  "title": "Ürünün net marka ve model adı (Örn: Razer DeathAdder V2)",
  "old_price": "Varsa eski veya normal piyasa fiyatı (örn: 1.499 TL)",
  "new_price": "İndirimli satış fiyatı (örn: 799 TL)",
  "discount_pct": "İndirim yüzdesi (örn: -47%)",
  "badge": "İndirim %45 üzeriyse 'DİP FİYAT', %35 üzeriyse 'DEV İNDİRİM', diğerinde '{store_name.upper()} FIRSATI'",
  "hook": "Neden kaçırılmaması gerektiğini özetleyen tek cümlelik detay"
}}
"""
            deal_data = call_gemini(prompt, json_mode=True)
            if isinstance(deal_data, list) and len(deal_data) > 0 and isinstance(deal_data[0], dict):
                deal_data = deal_data[0]
            if not isinstance(deal_data, dict) or not deal_data.get("title") or not deal_data.get("new_price"):
                continue

            # Genel kategori veya belirsiz başlık filtresi
            if not deal_data.get("is_specific_product", True):
                print(f"[Deal Hunter] ⏭️ Genel/Belirsiz Kategori Duyurusu Elendi: {deal_data.get('title')}")
                continue

            if is_vague_deal(deal_data.get("title", ""), raw_text):
                print(f"[Deal Hunter] ⏭️ Belirsiz Başlık Elendi: {deal_data.get('title')}")
                continue

            # Minimum indirim kontrolü
            pct_val = get_deal_discount_pct(deal_data)
            deal_data["discount_val"] = pct_val
            if pct_val < min_discount:
                print(f"[Deal Hunter] ⏭️ Düşük İndirim Elendi ({store_name} -%{pct_val} < -%{min_discount}): {deal_data.get('title')}")
                continue

            # Minimum fiyat kontrolü (350 TL altı ürünleri ele)
            try:
                p_digits = re.sub(r"[^\d]", "", deal_data.get("new_price", "").split(",")[0])
                if p_digits and int(p_digits) < MIN_PRODUCT_PRICE_TL:
                    continue
            except Exception:
                pass

            # Görseli indir
            img_filename = f"hunt_prod_{len(collected_deals) + 1}.jpg"
            img_path = os.path.join(TEMP_DIR, img_filename)
            if not download_file(photo_url, img_path):
                continue

            from campaign_calculator import calculate_campaign_and_net_cost
            camp = calculate_campaign_and_net_cost(deal_data.get("new_price", ""), store_name)
            deal_data["bank_campaign"] = camp["bank_campaign"]
            deal_data["net_cost"] = camp["net_cost"]
            deal_data["installment"] = camp["installment"]

            deal_data["image_path"] = img_path
            deal_data["source_channel"] = ch
            deal_data["store_url"] = store_url
            deal_data["store_name"] = store_name

            # Amazon linki ise ASIN çıkar ve fiyat geçmişine kaydet
            asin_m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", store_url, re.IGNORECASE)
            if asin_m:
                asin = asin_m.group(1).upper()
                deal_data["asin"] = asin
                try:
                    from price_tracker import record_price
                    price_f = parse_price_to_float(deal_data.get("new_price", ""))
                    if price_f > 0:
                        record_price(asin, store_name, deal_data.get("title", ""), price_f)
                except Exception:
                    pass

            if pct_val >= 45:
                deal_data["badge"] = "DİP FİYAT"
            elif pct_val >= 35:
                deal_data["badge"] = "DEV İNDİRİM"
            elif not deal_data.get("badge"):
                deal_data["badge"] = f"{store_name.upper()} FIRSATI"

            collected_deals.append(deal_data)
            print(f"[Deal Hunter] 🔥 [{store_name}] Fırsat Yakalandı: {deal_data['title']} | {deal_data['new_price']} (-%{pct_val}, Net: {camp['net_cost']})")

    return collected_deals

def hunt_best_deals(limit: int = 3, platform: str = "amazon", category: str = "all", exclude_urls: set = None, exclude_subtypes: set = None, min_discount: int = 25) -> list:
    """
    Amazon TR, Hepsiburada ve Trendyol üzerindeki EN YÜKSEK İNDİRİMLİ fırsatları avlar.
    Hem Amazon kataloglarını hem de Telegram sıcak fırsat kanallarını eş zamanlı tarar.
    Tüm adayları indirim oranına ve net TL tasarrufuna göre puanlayıp en yüksek indirimi en tepeye koyar.
    """
    candidates = []
    print(f"\n[Deal Hunter] 🔍 En Yüksek İndirim Avı Başlatıldı (Öncelikli Mağaza: AMAZON TR, Mod: {platform.upper()}, Min İndirim: %{min_discount})...")

    # 1. Amazon TR Kataloglarından Çek (Kategoriler arası rotasyonlu)
    if platform in ("all", "amazon"):
        amz_deals = hunt_amazon_deals(limit=limit + 5, category=category, exclude_urls=exclude_urls, exclude_subtypes=exclude_subtypes, min_discount=min_discount)
        for d in amz_deals:
            d["store_name"] = "Amazon TR"
            candidates.append(d)

    # 2. Sıcak Fırsat Kanallarından Taze Fırsatları Çek (Topluluk tarafından doğrulanmış dip fiyatlar)
    online_deals = hunt_online_deals(limit=limit + 6, exclude_urls=exclude_urls, min_discount=min_discount)
    for d in online_deals:
        st = d.get("store_name", "Fırsat")
        if platform == "amazon" and st != "Amazon TR":
            continue
        if platform == "trendyol" and st != "Trendyol":
            continue
        if platform == "hepsiburada" and st != "Hepsiburada":
            continue
        sub = get_product_subtype(d.get("title", ""))
        if exclude_subtypes and sub in exclude_subtypes and sub != "general":
            continue
        candidates.append(d)

    # Eğer belirlenen min_discount ile hiç ürün bulunamadıysa eşiği %15'e gevşet
    if not candidates and min_discount > 15:
        print(f"[Deal Hunter] ⚠️ %{min_discount} ve üzeri indirim bulunamadı, eşik %15'e gevşetiliyor...")
        return hunt_best_deals(limit=limit, platform=platform, category=category, exclude_urls=exclude_urls, exclude_subtypes=exclude_subtypes, min_discount=15)

    if not candidates:
        return []

    # 3. İndirim Odaklı Puanlama Motoru (En yüksek indirimli ve karlı ürünü tepeye yerleştirir)
    def score_deal(deal):
        title = deal.get("title", "").lower()
        score = 0.0
        
        # A. Birincil Kriter: İndirim Oranı (%1 indirim = +5 puan!)
        pct_val = get_deal_discount_pct(deal)
        score += pct_val * 5.0

        # B. Süper İndirim & Çöküş Bonusu
        if pct_val >= 50:
            score += 100.0  # Fiyat hatası / %50+ dev indirim
        elif pct_val >= 40:
            score += 50.0   # %40+ çok büyük fırsat
        elif pct_val >= 30:
            score += 20.0   # %30+ iyi indirim

        # C. Net TL Tasarruf Miktarı
        savings = get_deal_savings_tl(deal)
        if savings >= 2000:
            score += 50.0
        elif savings >= 1000:
            score += 30.0
        elif savings >= 500:
            score += 15.0

        # D. Yüksek Talep Gören Marka & Donanım Bonusu
        for kw in HIGH_DEMAND_KEYWORDS:
            if kw in title:
                score += 25.0
                break

        # E. Mağaza Bonusu (Affiliate için Amazon TR önceliği)
        if deal.get("store_name") == "Amazon TR":
            score += 35.0

        return score

    candidates.sort(key=score_deal, reverse=True)

    # Çeşitlilik süzgeci: Tek bir listede aynı ürün tipinden birden fazla olmasın
    best_deals = []
    seen_types = set(exclude_subtypes) if exclude_subtypes else set()
    for d in candidates:
        if len(best_deals) >= limit:
            break
        st = get_product_subtype(d.get("title", ""))
        if st != "general" and st in seen_types:
            continue
        best_deals.append(d)
        if st != "general":
            seen_types.add(st)

    # Eğer çeşitlilik kuralı nedeniyle limit dolmadıysa kalan adaylardan tamamla
    if len(best_deals) < limit:
        for d in candidates:
            if len(best_deals) >= limit:
                break
            if d not in best_deals:
                best_deals.append(d)

    print(f"\n[Deal Hunter] 🏆 EN YÜKSEK İNDİRİMLİ {len(best_deals)} FIRSAT SEÇİLDİ:")
    for i, d in enumerate(best_deals, 1):
        pct = get_deal_discount_pct(d)
        savings = get_deal_savings_tl(d)
        print(f"  {i}. [{d.get('store_name', 'Fırsat')}] {d.get('title')} | {d.get('new_price')} (İndirim: -%{pct} | Tasarruf: {int(savings)} TL)")

    return best_deals

def parse_deal_from_image(image_path: str) -> dict:
    """
    Kullanıcının verdiği ürün ekran görüntüsünü (Amazon, Trendyol vb.)
    Gemini Vision ile analiz ederek tüm bilgileri otomatik doldurur.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

    print(f"[Deal Hunter] Görsel analiz ediliyor (Gemini Vision): {image_path}...")
    prompt = """Bu bir e-ticaret indirim/fırsat ekran görüntüsü.
Görseldeki ürün adını, eski fiyatını (üstü çizili olan), yeni indirimli fiyatını ve indirim yüzdesini tespit et.

Şu saf JSON formatında döndür:
{
  "title": "Kısa ve net ürün adı (maksimum 35 karakter)",
  "old_price": "Eski fiyat (örn: 1.499 TL)",
  "new_price": "Yeni fiyat (örn: 899 TL)",
  "discount_pct": "İndirim yüzdesi (örn: -40%)",
  "badge": "GÜNÜN FIRSATI",
  "hook": "Ürünün vurucu özelliği veya fırsat sebebi"
}
"""
    deal_data = call_gemini(prompt, json_mode=True, image_path=image_path)
    if not deal_data:
        deal_data = {
            "title": "Günün Özel Fırsat Ürünü",
            "old_price": "Piyasa Fiyatı",
            "new_price": "İndirimde",
            "discount_pct": "FIRSAT",
            "badge": "GÜNÜN FIRSATI",
            "hook": "Kaçırılmayacak süper fiyat!"
        }

    deal_data["image_path"] = image_path
    return deal_data

def parse_deal_from_url(url: str) -> dict:
    """
    Verilen ürün web sayfasından OpenGraph meta etiketleri ve metinle ürün bilgilerini çeker.
    """
    print(f"[Deal Hunter] URL taranıyor: {url}...")
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_html = os.path.join(TEMP_DIR, "page.html")
    
    cmd = get_curl_cmd(["-s", "-L", "-H", "User-Agent: Mozilla/5.0", url, "-o", temp_html])
    subprocess.run(cmd)

    og_title = ""
    og_image = ""
    og_desc = ""

    if os.path.exists(temp_html):
        with open(temp_html, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            
        t_el = soup.find("meta", property="og:title")
        if t_el: og_title = t_el.get("content", "")
        
        i_el = soup.find("meta", property="og:image")
        if i_el: og_image = i_el.get("content", "")
        
        d_el = soup.find("meta", property="og:description")
        if d_el: og_desc = d_el.get("content", "")

    img_path = os.path.join(TEMP_DIR, "url_product.jpg")
    if og_image:
        download_file(og_image, img_path)

    prompt = f"""Şu web sayfası bilgilerinden indirimli ürün bilgilerini JSON olarak çıkar:
Başlık: {og_title}
Açıklama: {og_desc}
URL: {url}

Şu JSON formatında döndür:
{{
  "title": "Kısa ve net ürün adı (maksimum 35 karakter)",
  "old_price": "Varsa eski fiyat (örn: 2.999 TL)",
  "new_price": "Yeni fiyat (örn: 1.899 TL)",
  "discount_pct": "İndirim yüzdesi (örn: -35%)",
  "badge": "GÜNÜN FIRSATI",
  "hook": "Vurucu fırsat açıklaması"
}}
"""
    deal_data = call_gemini(prompt, json_mode=True)
    if not deal_data:
        deal_data = {
            "title": og_title[:35] if og_title else "Günün İndirimi",
            "old_price": "Önceki Fiyat",
            "new_price": "İndirimli Fiyat",
            "discount_pct": "FIRSAT",
            "badge": "GÜNÜN FIRSATI",
            "hook": "Fırsatı kaçırma!"
        }

    deal_data["image_path"] = img_path if os.path.exists(img_path) else None
    deal_data["store_url"] = url
    return deal_data

if __name__ == "__main__":
    print("--- ONLINE DEAL HUNTING TEST ---")
    deals = hunt_online_deals(limit=2)
    print(f"\nToplam {len(deals)} fırsat bulundu:")
    for d in deals:
        print(json.dumps(d, indent=2, ensure_ascii=False))
