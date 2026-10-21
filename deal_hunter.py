import os
import re
import json
import base64
import subprocess
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import BASE_DIR, TEMP_DIR, GEMINI_API_KEY, get_curl_cmd, safe_run_subprocess

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
    r"adaptör[üu]?|kılıf[ıi]?|ekran\s*koruyucu|koruyucu\s*cam|temizleme|temizleyici|çorap|askı(lık)?|tutucu|"
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
    r"kartuş|toner|koli|kutu|folyo|termal|termal\s*macun|vida|dübel|somun|aparat[ıi]?|"
    r"musluk|duş\s*başlığı|hortum|gider|paspas|fırça|mandal|priz|uzatma\s*kablosu|ampul|duy|bant|yapıştırıcı|silikon|"
    r"defter|kalem|dosya|klasör|zarf|\bkitap\b|roman|dergi|kedi\s*kumu|köpek|tasma|külot|boxer|atlet|eldiven|bere|şemsiye|"
    r"oto\s*kokusu|silecek|bijon|kordon|kayış|"
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

# Türkiye'de insanların görünce tereddütsüz tıkladığı A-Sınıfı Dev Markalar (Brand Authority Whitelist)
TIER_1_BRANDS = [
    "apple", "samsung", "sony", "asus", "rog", "tuf", "msi", "dell", "alienware", "lg", "lenovo", "hp", "victus",
    "acer", "nitro", "benq", "viewsonic", "aoc", "gigabyte", "logitech", "razer", "steelseries", "hyperx", "corsair",
    "jbl", "anker", "soundcore", "sennheiser", "marshall", "bose", "edifier", "nothing", "philips", "dyson",
    "stanley", "delonghi", "nespresso", "xiaomi", "roborock", "dreame", "bosch", "einhell", "lego", "braun",
    "oral-b", "spigen", "baseus", "ugreen", "belkin", "tp-link", "sandisk", "kingston", "crucial", "wd", "seagate",
    "nintendo", "playstation", "dualsense", "xbox", "casio", "garmin", "huawei", "honor", "anker", "north bayou",
    "keychron", "epomaker", "ajazz", "attack shark", "wraith", "aula", "fifine", "elgato", "rode", "shure"
]

def has_tier1_brand(title: str) -> bool:
    """Ürünün Türkiye'de yüksek güven ve talep gören A-sınıfı bir markaya ait olup olmadığını kontrol eder."""
    t_low = (title or "").lower()
    for b in TIER_1_BRANDS:
        if re.search(r"\b" + re.escape(b) + r"\b", t_low):
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
    "stanley", "termos", "airfryer", "kahve makinesi", "oneblade", "tıraş", "lego", "projeksiyon", "robot süpürge",
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
    if any(k in t for k in ["monitör kolu", "f80", "north bayou", "nb f80", "amortisörlü kol"]):
        return "monitor_arm"
    if any(k in t for k in ["stanley", "termos", "matara", "mug"]):
        return "thermos"
    if any(k in t for k in ["kahve makinesi", "filtre kahve", "espresso", "lattego"]):
        return "coffee"
    if any(k in t for k in ["airfryer", "fritöz"]):
        return "airfryer"
    if any(k in t for k in ["tıraş", "traş", "oneblade", "epilasyon"]):
        return "grooming"
    if any(k in t for k in ["diş fırçası", "oral-b", "sonicare"]):
        return "dental"
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

MIN_PRODUCT_PRICE_TL = 450   # 450 TL altındaki küçük filtre, kablo, ıvır zıvır ürünleri ele
MAX_PRODUCT_PRICE_TL = 4500  # 4.500 TL üstündeki kimsenin anında alamayacağı aşırı pahalı ürünleri ele (Altın Fiyat Bandı)

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
        data = None
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                data = r.json()
        except Exception:
            pass

        # Fallback: curl subprocess (arka planda sessiz)
        if not data:
            cmd = get_curl_cmd(["--max-time", "15", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", f"@{req_file}", url])
            res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
            try:
                data = json.loads(res.stdout)
            except Exception:
                continue
        
        try:
            if data and "candidates" in data and len(data["candidates"]) > 0:
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
    """Doğrudan Python requests ile dosya indirir (sıfır CMD penceresi)."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    cmd = get_curl_cmd(["--max-time", "15", "-s", "-L", url, "-o", output_path])
    res = safe_run_subprocess(cmd)
    return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000

AMAZON_CATALOG_SOURCES = [
    ("FIRSATLAR_DEALS", "https://www.amazon.com.tr/deals"),
    ("PATLAYAN_ELEKTRONİK", "https://www.amazon.com.tr/gp/movers-and-shakers/electronics"),
    ("PATLAYAN_BİLGİSAYAR", "https://www.amazon.com.tr/gp/movers-and-shakers/computers"),
    ("PATLAYAN_GAMING", "https://www.amazon.com.tr/gp/movers-and-shakers/videogames"),
    ("GAMING", "https://www.amazon.com.tr/gp/bestsellers/videogames"),
    ("ELEKTRONİK", "https://www.amazon.com.tr/gp/bestsellers/electronics"),
    ("BİLGİSAYAR", "https://www.amazon.com.tr/gp/bestsellers/computers"),
    ("MONİTÖR", "https://www.amazon.com.tr/gp/bestsellers/computers/12601904031"),
    ("KULAKLIK_SES", "https://www.amazon.com.tr/gp/bestsellers/electronics/13709880031"),
    ("PATLAYAN_MUTFAK", "https://www.amazon.com.tr/gp/movers-and-shakers/kitchen"),
    ("MUTFAK_YAŞAM", "https://www.amazon.com.tr/gp/bestsellers/kitchen"),
    ("STANLEY_TERMOS_OUTDOOR", "https://www.amazon.com.tr/gp/bestsellers/sports"),
    ("KİŞİSEL_BAKIM_TIRAŞ", "https://www.amazon.com.tr/gp/bestsellers/personal-care"),
    ("OFİS_ERGONOMİ_MASA", "https://www.amazon.com.tr/gp/bestsellers/office"),
    ("PATLAYAN_KİŞİSEL_BAKIM", "https://www.amazon.com.tr/gp/movers-and-shakers/personal-care")
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
    Sadece belirlenen minimum indirim oranını (min_discount) ve AI Arzu Testini (8+/10) karşılayan ürünleri seçer.
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
            "-H", "User-Agent: Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
            target_url
        ])
        res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            continue

        parsed_candidates = []

        # 1. /deals sayfası için gömülü JSON ürün verilerini çıkar (React/AUI Deals widget)
        if "deals" in target_url:
            idx = res.stdout.find('"productSearchResponse"')
            if idx != -1:
                brace_start = res.stdout.find('{', idx)
                try:
                    obj, _ = json.JSONDecoder().raw_decode(res.stdout[brace_start:])
                    for p in obj.get("products", []):
                        p_title = p.get("title", "").strip()
                        p_pay = p.get("price", {}).get("priceToPay", {})
                        if not p_pay or not p_pay.get("price") or not p_title:
                            continue
                        try:
                            p_price_f = float(p_pay["price"])
                            p_price_str = f"{p_price_f:,.0f} TL"
                        except Exception:
                            continue
                        p_asin = p.get("asin", "")
                        p_link = p.get("link", "")
                        p_url = f"https://www.amazon.com.tr/dp/{p_asin}" if p_asin else (f"https://www.amazon.com.tr{p_link}" if p_link.startswith("/") else p_link)
                        p_hires = p.get("image", {}).get("hiRes", {})
                        if p_hires and p_hires.get("baseUrl"):
                            p_img = f"{p_hires['baseUrl']}.{p_hires.get('extension', 'jpg')}"
                        else:
                            p_img = p.get("image", {}).get("lowRes", {}).get("baseUrl", "")

                        parsed_candidates.append({
                            "raw_title": p_title,
                            "raw_price": p_price_str,
                            "big_img": p_img,
                            "raw_img": p_img,
                            "prod_url": p_url,
                            "asin": p_asin,
                            "rating_val": 4.5,
                            "review_count": 50
                        })
                except Exception:
                    pass

        # 2. Standart HTML ürün kartlarını tara
        soup = BeautifulSoup(res.stdout, "html.parser")
        items = soup.find_all("div", class_="p13n-sc-uncoverable-faceout")
        if not items:
            items = soup.select("div[data-asin]")

        for it in items:
            title_el = it.find("h2") or it.find("div", class_=lambda c: c and "line-clamp" in c) or it.find("span")
            price_el = it.select_one(".a-price .a-offscreen") or it.find("span", class_=lambda c: c and "price" in c)
            img_el = it.find("img")
            link_el = it.find("a", href=re.compile(r"/dp/"))

            if not (title_el and price_el and img_el and link_el):
                continue

            h_title = title_el.text.strip()
            h_price = price_el.text.strip()
            h_img = img_el.get("src", "")
            h_big_img = re.sub(r'\._AC_.*?_\.', '._AC_SL1000_.', h_img)
            h_href = link_el.get("href", "")
            h_asin_m = re.search(r"/dp/([A-Z0-9]{10})", h_href, re.IGNORECASE)
            if h_asin_m:
                h_asin = h_asin_m.group(1).upper()
                h_url = f"https://www.amazon.com.tr/dp/{h_asin}"
            else:
                h_asin = None
                h_url = "https://www.amazon.com.tr" + h_href.split("?")[0]

            h_card_text = it.get_text(" ", strip=True)
            h_rating = 0.0
            h_reviews = 0
            r_match = re.search(r"([12345][.,]\d)\s*(?:/\s*5|yıldız)", h_card_text)
            if r_match:
                try:
                    h_rating = float(r_match.group(1).replace(",", "."))
                except Exception:
                    pass
            rev_el = it.find("span", class_=re.compile(r"a-size-small"))
            if rev_el:
                rev_digits = re.sub(r"[^\d]", "", rev_el.text)
                if rev_digits:
                    try:
                        h_reviews = int(rev_digits)
                    except Exception:
                        pass

            parsed_candidates.append({
                "raw_title": h_title,
                "raw_price": h_price,
                "big_img": h_big_img,
                "raw_img": h_img,
                "prod_url": h_url,
                "asin": h_asin,
                "rating_val": h_rating,
                "review_count": h_reviews
            })

        for cand in parsed_candidates:
            if len(deals) >= limit:
                break

            raw_title = cand["raw_title"]
            raw_price = cand["raw_price"]
            big_img = cand["big_img"]
            raw_img = cand["raw_img"]
            prod_url = cand["prod_url"]
            rating_val = cand["rating_val"]
            review_count = cand["review_count"]
            asin_from_cand = cand.get("asin")

            # 1. Sıkıcı veya düşük ilgi gören aksesuarları ele
            if BORING_REGEX.search(raw_title):
                continue

            # 1.5 Halk Onayı (Social Proof): Yıldız Puanı ve Yorum Sayısı Kontrolü
            if rating_val > 0 and rating_val < 4.1:
                print(f"[Deal Hunter] ⏭️ Düşük Yıldız Puanı Elendi ({rating_val}⭐ < 4.1): {raw_title[:38]}")
                continue
            if 0 < review_count < 20 and not has_tier1_brand(raw_title):
                print(f"[Deal Hunter] ⏭️ Yetersiz Yorumlu Fason Ürün Elendi ({review_count} yorum): {raw_title[:38]}")
                continue

            # 2. Alt tip anti-tekrar koruması (örn: peş peşe 2 kol/gamepad veya 2 fare gelmez)
            raw_subtype = get_product_subtype(raw_title)
            if raw_subtype != "general" and raw_subtype in seen_subtypes:
                print(f"[Deal Hunter] ⏭️ Çeşitlilik Koruması ({raw_subtype} zaten var/yasaklı): {raw_title[:38]}")
                continue

            # 3. Minimum Fiyat Kontrolü (350 TL altındaki küçük ıvır zıvırları atla)
            try:
                price_clean = re.sub(r"[^\d]", "", raw_price.split(",")[0])
                if price_clean:
                    p_val = int(price_clean)
                    if p_val < MIN_PRODUCT_PRICE_TL or p_val > MAX_PRODUCT_PRICE_TL:
                        continue
            except Exception:
                pass

            # Daha önce üretilmişse pas geç
            if is_deal_already_shared(raw_title, prod_url, exclude_urls):
                print(f"[Deal Hunter] ⏭️ Mükerrer Ürün Koruması (Daha önce paylaşıldı): {raw_title[:45]}")
                continue

            if len(raw_title) < 6 or "TL" not in raw_price:
                continue

            print(f"[Deal Hunter] Aday Ürün Analiz Ediliyor ({cat_name}): {raw_title[:45]} | {raw_price}")

            prompt = f"""Şu popüler Amazon Türkiye ürününün gerçek piyasa değerini, indirimini ve sosyal medyada satın alınma cazibesini analiz et:
Ürün: {raw_title}
Amazon Satış Fiyatı: {raw_price}

GÖREV:
1. Bu ürünün Türkiye teknoloji/perakende pazarındaki gerçek piyasa / tavsiye edilen liste satış fiyatını (MSRP) belirle.
2. Amazon fiyatı ({raw_price}) ile piyasa liste fiyatı arasındaki indirim oranını gerçekçi hesapla.
3. VİTRİN & ARZU TESTİ (desirability_score: 1-10): Bu ürün Instagram Reels'te paylaşıldığında insanların "Oha çok iyi ürün/marka, bu fiyata kaçmaz!" deyip satın almak isteyeceği arzu edilen, havalı ve popüler bir ürün mü? Yoksa kimsenin heyecanlanmayacağı sıkıcı, tuhaf, niş veya sıradan bir ürün mü? (Sadece gerçek anlamda ilgi çekici, insanların görünce almak isteyeceği ürünlere 8, 9 veya 10 puan ver; sıradan/saçma ürünlere 1-6 ver!)

Şu JSON formatında döndür:
{{
  "title": "Ürünün kısa, vurucu ve net adı (maksimum 30 karakter, örn: Asus TUF Monitör, Stanley Termos, Razer Basilisk Mouse vb.)",
  "old_price": "Türkiye piyasa/liste fiyatı (örn: 2.499 TL)",
  "new_price": "{raw_price}",
  "discount_pct": "Hesaplanan indirim yüzdesi (örn: -38% veya -45%)",
  "desirability_score": 9,
  "badge": "İndirim %45 üzeriyse 'DİP FİYAT', %35 üzeriyse 'DEV İNDİRİM', diğerinde 'AMAZON FIRSATI'",
  "hook": "Kullanıcıların neden bu ürüne akın ettiğini anlatan tek cümle"
}}
"""
            deal_data = call_gemini(prompt, json_mode=True)
            if not deal_data or not deal_data.get("title"):
                continue

            desirability = 8
            try:
                desirability = int(deal_data.get("desirability_score", 8))
            except Exception:
                desirability = 8
            deal_data["desirability_score"] = desirability
            deal_data["rating"] = rating_val
            deal_data["review_count"] = review_count
            deal_data["is_mover_shaker"] = ("PATLAYAN" in cat_name)

            if desirability < 8:
                print(f"[Deal Hunter] ⏭️ Yapay Zeka Vitrin Testinden Geçemedi (Arzu Puanı: {desirability}/10 < 8): {deal_data.get('title')}")
                continue

            if is_deal_already_shared(deal_data.get("title", ""), prod_url, exclude_urls):
                print(f"[Deal Hunter] ⏭️ Mükerrer Ürün Koruması (Başlık eşleşmesi): {deal_data.get('title')}")
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

            asin = asin_from_cand
            if not asin:
                asin_m = re.search(r"/dp/([A-Z0-9]{10})", prod_url, re.IGNORECASE)
                if asin_m:
                    asin = asin_m.group(1).upper()
            prod_id = asin if asin else f"{len(deals)+1}_{int(datetime.now().timestamp())}"
            if asin:
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

def _normalize_title_tokens(t: str) -> str:
    if not t:
        return ""
    tr_map = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iiggüüssoocc")
    s = t.translate(tr_map).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    stop_words = {"oyuncu", "gaming", "kablosuz", "wireless", "kablolu", "siyah", "beyaz", "orijinal", "yeni", "nesil", "model", "turkiye", "garantili", "mouse", "klavye", "kulaklik", "kulakligi", "monitor", "termos", "filtre", "bellek"}
    tokens = [w for w in s.split() if len(w) >= 2 and w not in stop_words]
    return " ".join(tokens[:3])

def is_deal_already_shared(title: str, url: str, exclude_urls: set) -> bool:
    """Ürünün URL, ASIN veya marka/model başlığı bazında daha önce paylaşılıp paylaşılmadığını denetler."""
    if not exclude_urls:
        return False
    url_clean = (url or "").split("?")[0].strip().lower()
    asin_m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url or "", re.IGNORECASE)
    asin = asin_m.group(1).upper() if asin_m else ""
    norm_cand = _normalize_title_tokens(title)

    for ex in exclude_urls:
        if not ex:
            continue
        ex_str = str(ex).strip()
        ex_low = ex_str.lower()
        if url_clean and len(url_clean) > 12 and (url_clean in ex_low or ex_low.split("?")[0] == url_clean):
            return True
        if asin and asin.lower() in ex_low:
            return True
        if not ex_str.startswith("http") and norm_cand and len(norm_cand) >= 5:
            norm_ex = _normalize_title_tokens(ex_str)
            if norm_ex and len(norm_ex) >= 5 and (norm_cand == norm_ex or norm_cand in norm_ex or norm_ex in norm_cand):
                return True
    return False

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
        res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
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

            if is_deal_already_shared("", store_url, exclude_urls):
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
4. Eğer mesajda kupon indirimi, kupon kodu veya sepette kupon şartı belirtilmişse "coupon_info" alanına kısa ve net yaz (örn: "200 TL Kuponu Aktif Et", "Kupon Kodu: FIRSAT100"). Kupon yoksa "" bırak.
5. "desirability_score" (1 ile 10 arası tam sayı): Bu ürün Instagram Reels'te karşısına çıkan birinin HEYECANLANIP ALMAK İSTEYECEĞİ, popüler, arzu edilen ve bilinen bir ürün mü?
   - Oyuncu ekipmanı, kulaklık, monitör, akıllı saat, kahve makinesi, termos, airfryer, Lego, güçlü powerbank/şarj, bilinen marka elektronik veya çok popüler ev aleti ise 8-10 ver.
   - Kimsenin bilmediği fason marka, yedek parça, tesisat malzemesi, kırtasiye, basit kablo/kılıf veya sıkıcı/alakasız bir ürünse 1-5 ver.

Şu JSON formatında döndür:
{{
  "is_specific_product": true,
  "desirability_score": 9,
  "title": "Ürünün net marka ve model adı (Örn: Razer DeathAdder V2)",
  "old_price": "Varsa eski veya normal piyasa fiyatı (örn: 1.499 TL)",
  "new_price": "İndirimli satış fiyatı (örn: 799 TL)",
  "discount_pct": "İndirim yüzdesi (örn: -47%)",
  "coupon_info": "Varsa kupon bilgisi (örn: '150 TL Kupon İndirimi'), yoksa ''",
  "badge": "İndirim %45 üzeriyse 'DİP FİYAT', %35 üzeriyse 'DEV İNDİRİM', diğerinde '{store_name.upper()} FIRSATI'",
  "hook": "Neden kaçırılmaması gerektiğini özetleyen tek cümlelik detay"
}}
"""
            deal_data = call_gemini(prompt, json_mode=True)
            if isinstance(deal_data, list) and len(deal_data) > 0 and isinstance(deal_data[0], dict):
                deal_data = deal_data[0]
            if not isinstance(deal_data, dict) or not deal_data.get("title") or not deal_data.get("new_price"):
                continue

            if is_deal_already_shared(deal_data.get("title", ""), store_url, exclude_urls):
                print(f"[Deal Hunter] ⏭️ Mükerrer Ürün Koruması (Daha önce paylaşıldı): {deal_data.get('title')}")
                continue

            # Genel kategori veya belirsiz başlık filtresi
            if not deal_data.get("is_specific_product", True):
                print(f"[Deal Hunter] ⏭️ Genel/Belirsiz Kategori Duyurusu Elendi: {deal_data.get('title')}")
                continue

            # AI Arzu Edilebilirlik (Desirability) Barajı (En az 8/10 olmalı)
            try:
                des_score = int(deal_data.get("desirability_score", 8))
            except Exception:
                des_score = 8
            deal_data["desirability_score"] = des_score
            if des_score < 8:
                print(f"[Deal Hunter] ⏭️ Düşük Cazibe / Sıradan Ürün Elendi (Puan: {des_score}/10): {deal_data.get('title')}")
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

            # Fiyat bandı kontrolü (450 TL - 4.500 TL arası tatlı nokta)
            try:
                p_digits = re.sub(r"[^\d]", "", deal_data.get("new_price", "").split(",")[0])
                if p_digits:
                    p_val = int(p_digits)
                    if p_val < MIN_PRODUCT_PRICE_TL or p_val > MAX_PRODUCT_PRICE_TL:
                        continue
            except Exception:
                pass

            # Görseli indir (Her ürün için benzersiz dosya adı)
            import hashlib
            url_hash = hashlib.md5(photo_url.encode("utf-8", errors="ignore")).hexdigest()[:10]
            img_filename = f"hunt_prod_{url_hash}.jpg"
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
            deal_data["is_tier1_brand"] = has_tier1_brand(deal_data.get("title", "")) or has_tier1_brand(raw_text)

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
            print(f"[Deal Hunter] 🔥 [{store_name}] Fırsat Yakalandı: {deal_data['title']} | {deal_data['new_price']} (-%{pct_val}, Cazibe: {des_score}/10, Net: {camp['net_cost']})")

    return collected_deals

def hunt_best_deals(limit: int = 3, platform: str = "amazon", category: str = "all", exclude_urls: set = None, exclude_subtypes: set = None, min_discount: int = 25) -> list:
    """
    Amazon TR, Hepsiburada ve Trendyol üzerindeki EN ARZU EDİLEN ve EN YÜKSEK İNDİRİMLİ fırsatları avlar.
    6 Katmanlı Akıllı Keşif Motoru ile saçma/fason ürünleri eler, A-Sınıfı marka ve çok satan fırsatları zirveye taşır.
    """
    candidates = []
    print(f"\n[Deal Hunter] 🔍 6 Katmanlı Akıllı İndirim Avı Başlatıldı (Öncelikli Mağaza: AMAZON TR, Mod: {platform.upper()}, Min İndirim: %{min_discount})...")

    # 1. Amazon TR Kataloglarından Çek (Movers & Shakers + Çok Satanlar + Fırsatlar rotasyonlu)
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

    # 3. 6 Katmanlı Dengeli Cazibe & İndirim Puanlama Motoru
    # Saçma/fason ürünlerin şişirme %70 indirimle üste çıkmasını engeller;
    # gerçek marka, yüksek yorum/yıldız ve yüksek satın alma arzusunu gerçek indirimle birleştirir.
    def score_deal(deal):
        title = deal.get("title", "").lower()
        score = 0.0

        # A. Dengeli İndirim Puanı (Tavan: %48! Böylece fason ürünlerin sahte %75 indirimi haksız avantaj sağlamaz)
        pct_val = get_deal_discount_pct(deal)
        capped_pct = min(pct_val, 48)
        score += capped_pct * 3.5

        # Gerçek marka + yüksek indirim sinerjisi:
        is_tier1 = deal.get("is_tier1_brand") or has_tier1_brand(title)
        if is_tier1:
            score += 65.0  # A-Sınıfı Dev Marka Otorite Bonusu
            if pct_val >= 35:
                score += 45.0  # Bilinen markada %35+ indirim = Gerçek Fırsat!
            elif pct_val >= 25:
                score += 25.0
        else:
            # Tier-1 marka değilse ve cazibe puanı 9'un altındaysa ağır ceza uygula
            if int(deal.get("desirability_score", 8)) < 9:
                score -= 80.0

        # B. AI Arzu Edilebilirlik (Desirability) Puanı (8..10 -> +96..+120 Puan)
        des_score = int(deal.get("desirability_score", 8))
        score += des_score * 12.0

        # C. Sosyal Kanıt (Yorum Sayısı & Yıldız Puanı) Bonusu
        rev_count = int(deal.get("review_count", 0))
        rating_val = float(deal.get("rating", 0.0))
        if rev_count >= 500:
            score += 45.0
        elif rev_count >= 100:
            score += 30.0
        elif rev_count >= 30:
            score += 15.0

        if rating_val >= 4.6:
            score += 25.0
        elif rating_val >= 4.3:
            score += 15.0

        # D. Amazon Movers & Shakers (Son 24 Saatte Satışı Patlayanlar) Bonusu
        if deal.get("is_mover_shaker"):
            score += 35.0

        # E. Net TL Tasarruf Miktarı
        savings = get_deal_savings_tl(deal)
        if savings >= 2000:
            score += 45.0
        elif savings >= 1000:
            score += 30.0
        elif savings >= 500:
            score += 15.0

        # F. Yüksek Talep & Viral Tartışma Bonusu (Reels'te en çok kaydedilen/tartışılan ürünler)
        for kw in HIGH_DEMAND_KEYWORDS:
            if kw in title:
                score += 25.0
                break

        viral_engagement_kw = [
            "monitör", "monitor", "klavye", "mouse", "kulaklık", "gaming", "oyuncu", "gamepad",
            "stanley", "termos", "kahve", "airfryer", "lego", "apple", "samsung", "logitech",
            "steelseries", "razer", "philips", "sony", "dyson", "north bayou", "dualsense",
            "powerbank", "şarj", "projeksiyon", "akıllı saat", "ssd", "robot süpürge"
        ]
        if any(v in title for v in viral_engagement_kw):
            score += 25.0

        # G. Kupon İndirimi & Amazon TR Affiliate Önceliği
        if deal.get("coupon_info"):
            score += 15.0
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
    safe_run_subprocess(cmd)

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
