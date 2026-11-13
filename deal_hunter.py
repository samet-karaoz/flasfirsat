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
    "gemini-2.5-flash",
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


BEAUTY_MAKEUP_KEYWORDS = [
    "maskara", "rimel", "gloss", "lip gloss", "dudak", "ruj", "allık", "blush",
    "glotion", "kapatıcı", "concealer", "fondöten", "foundation", "bb krem", "cc krem",
    "eyeliner", "göz kalemi", "kaş", "far paleti", "parfüm", "edt", "edp", "body mist",
    "serum", "nemlendirici", "cilt", "tonik", "şampuan", "saç bakım", "saç kremi",
    "oje", "manikür", "epilatör", "ağda", "pudra", "powder", "bronzer", "highlighter",
    "kontür", "primer", "makyaj", "makeup", "lipstick", "lipliner", "lip liner", "lash",
    "maybelline", "l'oreal", "golden rose", "kiko", "flormar", "revolution", "nyx",
    "essence", "pastel", "beaulis", "vichy", "cerave", "bioderma", "la roche", "dercos",
    "true match", "fit me", "sky high", "infaillible", "lifter gloss",
    "yüz temizleme", "güneş kremi", "el kremi", "vücut losyonu", "peeling"
]

def is_beauty_product(title: str) -> bool:
    """Verilen ürünün makyaj, kozmetik, cilt/saç bakımı veya kadın güzellik ürünü olduğunu doğrular."""
    t = (title or "").lower()
    return any(k in t for k in BEAUTY_MAKEUP_KEYWORDS)

BORING_REGEX = re.compile(
    r"(şarj\s*kablosu|data\s*kablosu|şarj\s*kiti|oyun\s*ve\s*şarj|batarya\s*kiti|\bpuck\b|şarj\s*diski|şarj\s*yuvası|şarj\s*modülü|şarj\s*aleti|güç\s*adaptörü|duvar\s*şarj|range\s*extender|menzil\s*genişletici|bluetooth\s*5\.|usb\s*adaptör|\badaptör(ü)?\b|\bkablo(su)?\b(?!lu)|"
    r"kılıf[ıi]?|ekran\s*koruyucu|koruyucu\s*cam|temizleme\s*spreyi|temizleme\s*bezi|çorap|askı(lık)?|"
    r"(?<!monitör\s)(?<!laptop\s)stand[ıi]?|"
    r"çevirici|dönüştürücü|deterjan|bez|havlu|bulaşık\s*tableti|yumuşatıcı|mendil|pijama|(?<!sırt\s)(?<!omuz\s)(?<!spor\s)(?<!bel\s)çanta(sı)?|"
    r"tartı(sı)?|terazi(si)?|baskül|ölçüm|termometre|ateş\s*ölçer|"
    r"saklama\s*kabı|kavanoz|rende|süzgeç|açacak|maşa|spatula|kesme\s*tahtası|(?<!makyaj\s)sünger|"
    r"flaş\s*bellek|usb\s*bellek|flash\s*bellek|hafıza\s*kartı|sd\s*kart|microsd|flash\s*drive|usb\s*drive|kart\s*okuyucu|"
    r"bebek\s*maması|mama(sı)?|devam\s*sütü|vitamin|omega|balık\s*yağı|takviye|"
    r"bisküvi|kek|gofret|çikolata|cips|makarna|salça|bakliyat|kuruyemiş|çekirdek|ton\s*balığı|baharat|"
    r"motosiklet|lastik|kask(ı)?|disk\s*kilidi|sabun|"
    r"yastık|çarşaf|nevresim|terlik|kolonya|"
    r"tişört|pantolon|gömlek|\bkahve\b(?!\s*makine)|\bpil\b|kalem\s*pil|alkalin|şarj\s*edilebilir\s*pil|"
    r"kartuş|toner|koli|kutu|folyo|termal\s*macun|vida|dübel|somun|aparat[ıi]?|"
    r"musluk|duş\s*başlığı|hortum|gider|paspas|mandal|priz|uzatma\s*kablosu|ampul|duy|bant|yapıştırıcı|silikon|"
    r"defter|(?<!göz\s)(?<!dudak\s)(?<!kaş\s)\bkalem(i)?\b|dosya|klasör|zarf|\bkitap\b|roman|dergi|kedi\s*kumu|köpek|tasma|külot|boxer|atlet|eldiven|bere|şemsiye|"
    r"oto\s*kokusu|silecek|bijon|kordon|kayış|"
    r"filtre(si)?|kireç|su\s*arıtma|aquaclean|maxtra|toz\s*torbası|yedek\s*filtre|yedek\s*parça|yedek\s*bıçak|"
    r"tıraş\s*başlığı|fırça\s*başlığı|yedek\s*başlık|diş\s*fırçası\s*başlığı|şarj\s*kiti|oyun\s*ve\s*şarj|"
    r"bilek\s*destek|monitör\s*tutucu|monitör\s*kolu|monitör\s*stand|laptop\s*stand|laptop\s*sehpa|notebook\s*soğutucu|"
    r"kahve|espresso|moka\s*pot|bialetti|lattego|nespresso|çay\s*makine|çaycı|tost\s*makine|blender|mutfak\s*robotu|"
    r"terlik|sandalet|çorap|iç\s*çamaşır|\bslip\b|lohusa|emzirme|sütyen|çakmak\s*sıvısı|cam\s*şişe\s*su|maskot\s*su|"
    r"kolonya|bidon|aseton|makyaj\s*pamuğu|kulak\s*çubuğu|tıraş\s*köpüğü|tıraş\s*jeli|"
    r"conta|temizleme\s*tableti|kireç\s*çözücü|sarf\s*malzeme)",
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
    "keychron", "epomaker", "ajazz", "attack shark", "wraith", "aula", "fifine", "elgato", "rode", "shure",
    "adidas", "puma", "nike", "under armour", "skechers", "new balance", "vans", "reebok", "salomon", "columbia", "asics",
    "levi's", "jack & jones", "tommy hilfiger", "guess", "eastpak", "herschel", "lorus", "seiko", "g-shock",
    "qcy", "soundpeats", "klasse", "royal kludge", "gamesir", "8bitdo",
    "calvin klein", "versace", "davidoff", "burberry", "hugo boss", "armani", "victoria's secret", "slazenger", "privacy", "jagler", "bargello", "rebul", "nyx", "kiko", "pastel", "flormar", "golden rose", "vichy",
    "the purest solutions", "l'oreal", "maybelline", "cerave", "bioderma", "la roche-posay", "garnier", "nivea", "bioxcin", "opalescence", "marvis"
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

# 1. TEMEL KURAL: GENİŞ KİTLEYE HİTAP EDEN ÜRÜNLER (MASS-APPEAL DIRECTIVE)
BROAD_AUDIENCE_KEYWORDS = [
    "kulaklık", "headset", "airpods", "buds", "earbuds", "soundcore", "anc",
    "hoparlör", "speaker", "soundbar", "powerbank", "power bank", "akıllı saat", "smart watch", "smartwatch", "akıllı bileklik",
    "kahve makinesi", "espresso", "airfryer", "fritöz", "termos", "quencher", "iceflow", "matara",
    "tost makinesi", "blender", "robot süpürge", "dikey süpürge", "şarjlı süpürge",
    "monitör", "monitor", "mouse", "fare", "klavye", "keyboard", "oyun kolu", "gamepad",
    "dualsense", "wireless controller", "oyuncu kulaklığı", "gaming laptop", "laptop", "mousepad", "mouse pad",
    "tıraş makinesi", "oneblade", "diş fırçası", "oral-b", "sonicare", "airwrap",
    "serum", "nemlendirici", "güneş kremi", "şampuan", "saç kurutma", "saç düzleştirici", "epilatör"
]

MASS_APPEAL_PRODUCT_REGEX = re.compile(
    r"(kulaklık|headset|airpods|earbuds|\bbuds\b|soundcore|"
    r"hoparlör|speaker|soundbar|"
    r"akıllı\s*saat|smart\s*watch|smartwatch|akıllı\s*bileklik|galaxy\s*watch|apple\s*watch|watch\s*fit|mi\s*band|"
    r"powerbank|power\s*bank|taşınabilir\s*şarj|"
    r"ayakkabı|sneaker|koşu\s*ayakkabısı|spor\s*ayakkabı|yürüyüş\s*ayakkabısı|basketbol\s*ayakkabısı|tenis\s*ayakkabısı|outdoor\s*ayakkabı|"
    r"kol\s*saati|erkek\s*saat|kadın\s*saat|dijital\s*saat|\bcasio\b|g-shock|edifice|"
    r"sırt\s*çantası|omuz\s*çantası|spor\s*çanta|\bduffle\b|bel\s*çantası|\bcüzdan(ı)?\b|\bkartlık\b|"
    r"sweatshirt|\bhoodie\b|kapüşonlu|\bpolar\b|eşofman|\bjogger\b|"
    r"projektör|projeksiyon|monitör\s*lambası|ekran\s*lambası|ambiyans\s*aydınlatma|rgb\s*şerit|"
    r"\btermos\b|quencher|iceflow|\bmatara\b|termos\s*bardak|"
    r"robot\s*süpürge|dikey\s*süpürge|şarjlı\s*süpürge|kablosuz\s*süpürge|"
    r"\bmouse\b|\bfare(si)?\b|\bklavye(si)?\b|\bkeyboard\b|mouse\s*pad|mousepad|"
    r"\bmonitör(ü)?\b|\bmonitor\b|"
    r"oyun\s*kolu|\bgamepad\b|\bdualsense\b|wireless\s*controller|oyun\s*kontrolcü|direksiyon\s*seti|"
    r"\blaptop\b|\bnotebook\b|taşınabilir\s*ssd|nvme\s*ssd|"
    r"\bserum(u)?\b|yüz\s*kremi|nemlendirici|güneş\s*kremi|yüz\s*temizleme|\btonik\b|\bpeeling\b|\bşampuan(ı)?\b|saç\s*bakım|saç\s*maskesi|cilt\s*bakım|"
    r"parfüm|eau\s*de\s*parfum|eau\s*de\s*toilette|\bedp\b|\bedt\b|vücut\s*spreyi|body\s*mist|deodorant\s*set|"
    r"maskara|rimel|\bruj\b|\bgloss\b|lip\s*gloss|dudak\s*parlatıcı|dudak\s*yağı|dudak\s*kalemi|kapatıcı|concealer|fondöten|\ballık\b|likit\s*allık|\bblush\b|aydınlatıcı|highlighter|\bglotion\b|eyeliner|göz\s*kalemi|kaş\s*maskara|kaş\s*sabitleyici|sabitleme\s*spreyi|makyaj\s*bazı|bb\s*krem|cc\s*krem|\bpudra\b|far\s*paleti|tint\b|lip\s*tint|lip\s*balm|"
    r"diş\s*fırçası|oral-b|sonicare|"
    r"tıraş\s*makine|traş\s*makine|\boneblade\b|saç\s*kesme\s*makine|sakal\s*kesme|\bepilatör\b|\bipl\b|"
    r"saç\s*kurutma|fön\s*makine|saç\s*düzleştirici|saç\s*şekillendirici|\bairwrap\b|saç\s*maşası)",
    re.IGNORECASE
)

def is_mass_appeal_product(title: str) -> bool:
    """AGENTS.md Kural 1: Ürünün dar/niş aksesuar veya sarf malzemesi olmadığını, doğrudan geniş kitleye hitap eden ana ürün kategorilerinden biri olduğunu doğrular."""
    t = (title or "").strip()
    if not t or len(t) < 5:
        return False
    if BORING_REGEX.search(t) or VAGUE_TITLE_REGEX.search(t):
        return False
    return bool(MASS_APPEAL_PRODUCT_REGEX.search(t))

KNOWN_BRANDS = [
    "stanley", "logitech", "steelseries", "razer", "gamesir", "philips", "karaca",
    "the purest solutions", "delonghi", "de'longhi", "anker", "jbl", "sony", "apple",
    "cosori", "xiaomi", "roborock", "dreame", "dyson", "hyperx", "corsair", "asus", "msi",
    "lenovo", "dell", "samsung", "huawei", "oral-b", "braun", "cerave", "bioderma",
    "adidas", "puma", "nike", "under armour", "skechers", "new balance", "vans", "reebok", "columbia", "salomon", "kingston", "sandisk", "spigen", "baseus", "ugreen", "viewsonic", "aoc",
    "maybelline", "l'oreal", "golden rose", "kiko", "flormar", "revolution", "nyx", "essence", "pastel", "beaulis",
    "calvin klein", "versace", "davidoff", "slazenger", "privacy", "casio", "g-shock", "eastpak"
]

def extract_brand(title: str) -> str:
    """Ürün başlığından ana markayı tespit eder (Marka yorgunluğu ve anti-tekrar koruması)."""
    t = (title or "").lower()
    for b in KNOWN_BRANDS:
        if b in t:
            return "delonghi" if b == "de'longhi" else b
    return ""

def get_recent_subtypes_from_history(limit: int = 2, target_platform: str = None) -> set:
    """Son başarılı paylaşımlardaki alt kategorileri döner (Çeşitlilik koruması)."""
    subtypes = set()
    from config import DATA_DIR
    history_file = os.path.join(DATA_DIR, "autopilot_history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                items = json.load(f)
                count = 0
                for it in reversed(items):
                    if it.get("success") and not it.get("dry_run") and not it.get("skipped"):
                        platforms = it.get("platforms", {})
                        if target_platform and target_platform not in ("auto", "all"):
                            if target_platform not in platforms or platforms.get(target_platform, {}).get("status") != "ok":
                                continue
                        deal_info = it.get("deal")
                        t = deal_info.get("title", "") if isinstance(deal_info, dict) else str(deal_info or "")
                        sub = get_product_subtype(t)
                        if sub and sub != "general":
                            subtypes.add(sub)
                            count += 1
                            if count >= limit:
                                break
        except Exception:
            pass
    return subtypes

def get_recent_brands_from_history(limit: int = 2, target_platform: str = None) -> set:
    """Son başarılı paylaşımlardaki markaları döner (Stanley, Logitech vb. marka yorgunluğu koruması)."""
    brands = set()
    from config import DATA_DIR
    history_file = os.path.join(DATA_DIR, "autopilot_history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                items = json.load(f)
                count = 0
                for it in reversed(items):
                    if it.get("success") and not it.get("dry_run") and not it.get("skipped"):
                        platforms = it.get("platforms", {})
                        if target_platform and target_platform not in ("auto", "all"):
                            if target_platform not in platforms or platforms.get(target_platform, {}).get("status") != "ok":
                                continue
                        deal_info = it.get("deal")
                        t = deal_info.get("title", "") if isinstance(deal_info, dict) else str(deal_info or "")
                        b = extract_brand(t)
                        if b:
                            brands.add(b)
                            count += 1
                            if count >= limit:
                                break
        except Exception:
            pass
    return brands

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
    if any(k in t for k in ["stanley", "termos", "matara", "mug", "quencher", "iceflow"]):
        return "thermos"
    if any(k in t for k in ["ayakkabı", "sneaker"]):
        return "shoes"
    if any(k in t for k in ["airfryer", "fritöz"]):
        return "airfryer"
    if any(k in t for k in ["tıraş", "traş", "oneblade", "epilasyon"]):
        return "grooming"
    if any(k in t for k in ["diş fırçası", "oral-b", "sonicare"]):
        return "dental"
    if any(k in t for k in ["akıllı saat", "smartwatch", "bileklik", "watch"]):
        return "smartwatch"
    if any(k in t for k in ["powerbank", "hızlı şarj", "şarj aleti"]):
        return "powerbank"
    if any(k in t for k in ["serum", "nemlendirici", "cilt", "tonik", "güneş kremi", "leke karşıtı"]):
        return "skincare"
    if any(k in t for k in ["parfüm", "edt", "edp", "eau de", "body mist", "vücut spreyi"]):
        return "perfume"
    if any(k in t for k in ["maskara", "rimel"]):
        return "mascara"
    if any(k in t for k in ["gloss", "lip gloss", "ruj", "dudak yağı", "dudak parlatıcı", "dudak kalemi", "lip tint"]):
        return "lip_makeup"
    if any(k in t for k in ["allık", "blush", "glotion", "aydınlatıcı", "highlighter"]):
        return "blush_highlighter"
    if any(k in t for k in ["kapatıcı", "concealer", "fondöten", "bb krem", "cc krem", "pudra", "makyaj bazı"]):
        return "face_makeup"
    if any(k in t for k in ["eyeliner", "göz kalemi", "far paleti", "kaş maskara", "kaş sabitleyici"]):
        return "eye_makeup"
    if any(k in t for k in ["şampuan", "saç bakım", "saç kremi", "düzleştirici", "airwrap"]):
        return "haircare"
    if any(k in t for k in ["epilatör", "yüz epilatörü", "ipl"]):
        return "epilator"
    if any(k in t for k in ["ssd", "nvme", "disk"]):
        return "storage"
    return "general"

ARCHETYPE_PRICE_GLITCH = "price_glitch"
ARCHETYPE_VIRAL_GADGET = "viral_gadget"
ARCHETYPE_EXPENSIVE_DUPE = "expensive_dupe"
ARCHETYPE_VERIFIED_DEAL = "verified_deal"
ARCHETYPE_BESTSELLER_RADAR = "bestseller_radar"

def detect_deal_archetype(deal: dict) -> dict:
    """
    3'lü Viral Motor + Çok Satan Radarı:
    1. BESTSELLER_RADAR: Amazon #1 Çok Satan ve Viral Trend Ürünler
    2. EXPENSIVE_DUPE: Pahalı Markaların Birebir Muadilleri / Kazıklanma Rehberi
    3. VIRAL_GADGET: Hayat Kurtaran Problem Çözen Trend Ürünler
    4. PRICE_GLITCH: Fiyat Hatası & Kupon Açığı / Sepet Çökertme
    """
    title = str(deal.get("title") or "").lower()
    details = str(deal.get("hook") or deal.get("feature_pill") or deal.get("market_highlight") or "").lower()
    combined = f"{title} {details}"

    if deal.get("is_bestseller") or "çok satan" in str(deal.get("badge") or "").lower():
        is_beauty = is_beauty_product(title)
        hook_msg = "Kızların sepetleri doldurduğu o viral çok satan:" if is_beauty else "Amazon'da herkesin kapış kapış aldığı 1 numaralı o ürün:"
        return {
            "archetype": ARCHETYPE_BESTSELLER_RADAR,
            "badge_text": "🔥 #1 ÇOK SATAN",
            "killer_pill": "TÜRKİYE'DE EN ÇOK SATAN #1!",
            "reaction_hook": hook_msg,
            "style_prompt": "Amazon'da rekor kıran çok satan ürün radarı, viral sosyal kanıt ve kapış kapış giden popülerlik kancası"
        }
    
    coupon = str(deal.get("coupon_info") or deal.get("coupon_text") or "").strip()
    pct = get_deal_discount_pct(deal)
    savings = get_deal_savings_tl(deal)

    # 1. HAYAT KURTARAN İLGİNÇ GADGET / TREND ÜRÜN KONTROLÜ
    gadget_regex = re.compile(
        r"(yazıcı|printer|termal\s*yaz|etiket\s*makine|"
        r"temizleme\s*jel|toz\s*üfleyi|hava\s*kompresör|mini\s*süpürge|"
        r"manyetik|anti-gravity|havada\s*duran|rgb\s*ışık|neon\s*lamba|masa\s*lamba|"
        r"şarj\s*istasyon|kablo\s*düzenleyi|kablo\s*toplayı|usb\s*hub|docking|"
        r"lazer\s*metre|akıllı\s*tornavida|dijital\s*ölçer|"
        r"bardak\s*ısıtıcı|akıllı\s*matara|katlanabilir\s*klavye)",
        re.IGNORECASE
    )
    if gadget_regex.search(combined):
        return {
            "archetype": ARCHETYPE_VIRAL_GADGET,
            "badge_text": "HAYAT KURTARAN BULUŞ",
            "killer_pill": "BUNU TÜRKİYE'DE KİMSE BİLMİYOR!",
            "reaction_hook": "Gördüğüm an siparişi patlattığım o hayat kurtaran alet:",
            "style_prompt": "insanın görünce 'bunu hemen almam lazım' dediği ilginç, problem çözen gadget kancası (Merak / Arzu)"
        }

    # 2. PAHALI MARKA MUADİLİ / KAZIKLANMA REHBERİ KONTROLÜ
    dupe_indicators = [
        "muadil", "alternatif", "benzeri", "muadili", "çakma değil",
        "qcy", "soundpeats", "soundcore", "redmi buds", "buds fe",
        "gamesir", "8bitdo", "flydigi", "gulikit",
        "watch fit", "redmi watch", "xiaomi band", "galaxy fit",
        "dyson muadil", "airwrap muadil", "saç şekillendirici",
        "klasse", "attack shark", "ajazz", "aula", "royal kludge",
        "stanley muadil", "contigo"
    ]
    if any(k in combined for k in dupe_indicators):
        if any(b in combined for b in ["qcy", "soundpeats", "soundcore", "buds"]):
            pill = "AIRPODS'A SERVET ÖDEMEYİN!"
            hook_msg = "Aynı ses kalitesini veren 5'te 1 fiyatına canavar:"
        elif any(b in combined for b in ["gamesir", "8bitdo", "flydigi"]):
            pill = "PAHALI OYUN KOLLARINA SON!"
            hook_msg = "DualSense'e 4.000 TL vermek yerine profesyonellerin tercihi:"
        elif any(b in combined for b in ["watch", "band"]):
            pill = "APPLE WATCH ULTRA MUADİLİ!"
            hook_msg = "Pahalı akıllı saatlere binlerce lira bağlamayın:"
        elif any(b in combined for b in ["dyson", "şekillendirici", "airwrap"]):
            pill = "DYSON AIRWRAP MUADİLİ!"
            hook_msg = "30.000 TL vermek yerine aynı işi gören bu alet:"
        else:
            pill = "PAHALI MARKAYA SERVET ÖDEMEYİN!"
            hook_msg = "Aynı işi gören 5'te 1 fiyatına F/P canavarı:"

        return {
            "archetype": ARCHETYPE_EXPENSIVE_DUPE,
            "badge_text": "KAZIKLANMA REHBERİ",
            "killer_pill": pill,
            "reaction_hook": hook_msg,
            "style_prompt": "pahalı lüks markalara gereksiz servet ödemek istemeyen akıllı tüketici kancası (Muadil / Kazıklanmama)"
        }

    # 3. GERÇEK FİYAT HATASI & SİSTEM ANOMALİSİ (YALNIZCA GERÇEK ŞOK DÜŞÜŞLER!)
    # Gerçek Fiyat Hatası Kriterleri (deal-truthfulness Kuralı):
    # - İndirim oranı %48 ve üzeri (Örn: %50, %60, %72)
    # - VEYA Net tasarruf 2.000 TL ve üzeri olup indirim %40+ olan dev düşüşler
    # - VEYA Açıkça başlık/açıklamada 'fiyat hatası' / 'glitch' tespiti
    is_real_price_glitch = (
        pct >= 48 or 
        (savings >= 2000.0 and pct >= 40) or 
        any(k in combined for k in ["fiyat hatası", "glitch", "fiyatı yanlış", "kupon açığı"])
    )

    if is_real_price_glitch:
        pill = "FİYAT DÜZELTİLMEDEN YAKALA!"
        hook_msg = "Satıcı fiyatı resmen yanlış girmiş, fark etmeden yetişin:" if not coupon else "Sepetteki kupon açığıyla fiyat resmen çöktü, düzeltilmeden koşun:"
        return {
            "archetype": ARCHETYPE_PRICE_GLITCH,
            "badge_text": "GERÇEK FİYAT HATASI",
            "killer_pill": pill,
            "reaction_hook": hook_msg,
            "style_prompt": "satıcı fiyatı yanlış girmiş veya sistem hatasıyla dip fiyata çökmüş acil fırsat kancası (Panik / FOMO)"
        }

    # 4. DOĞRULANMIŞ DİP FİYAT FIRSATI (VERIFIED DEAL - DÜRÜSTLÜK & GERÇEKÇİLİK İLKESİ)
    # Sahte fiyat hatası iddiası yerine güven inşa eden, dürüst ve güçlü fırsat dili
    if coupon:
        pill = "SEPETTE EK İNDİRİMİ KAP!"
        hook_msg = "Sepetteki kuponu aktif edince son zamanların en dip fiyatına indi:"
        badge = "SEPETTE EK KUPON"
    elif pct >= 30:
        pill = "SON ZAMANLARIN EN DİP FİYATI!"
        hook_msg = "Son zamanların en dip fiyatına indi, stok erimeden koşun:"
        badge = "DİP FİYAT FIRSATI"
    else:
        pill = "BEKLENEN BÜYÜK İNDİRİM GELDİ!"
        hook_msg = "Bu fiyata bir daha zor düşer, ihtiyacı olan kaçırmasın:"
        badge = "DİP FİYAT FIRSATI"

    return {
        "archetype": ARCHETYPE_VERIFIED_DEAL,
        "badge_text": badge,
        "killer_pill": pill,
        "reaction_hook": hook_msg,
        "style_prompt": "doğrulanmış dürüst dip fiyat indirimi, orijinal ürün ve stok erimeden yakalama kancası (Güven / Kalite)"
    }


def parse_price_to_float(price_str: str) -> float:
    """Türkçe para birimi metinlerini ('1.949,00 TL' veya çift tekrarlı '1.567,00TL1.567,00TL' vb.) floata dönüştürür."""
    if not price_str:
        return 0.0
    m = re.search(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})|\d+(?:\.\d{1,2})?", str(price_str))
    cleaned = m.group(0).strip() if m else re.sub(r"[^\d,.]", "", str(price_str)).strip()
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

def calculate_deal_viral_score(deal: dict, target_platform: str = 'auto') -> float:
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
    plat = (target_platform or deal.get("target_platform") or "auto").lower()

    # 🛑 YOUTUBE KESİN GÜVENLİK FİLTRESİ:
    # YouTube hedefli paylaşımlarda güzellik, makyaj, dudak, ruj, şampuan vb. ürünler KESİNLİKLE YASAKTIR!
    if plat == "youtube" and is_beauty_product(title):
        return -999.0

    score = 0.0

    # 0. 1. ÖNCELİK: Geniş Kitleye Hitap (Mass-Appeal Directive) Bonusu & Niş Ürün Cezası
    is_broad = any(kw in title for kw in BROAD_AUDIENCE_KEYWORDS)
    if is_broad:
        score += 40.0
    if BORING_REGEX.search(title):
        score -= 120.0

    # Amazon #1 Çok Satan / Viral Sosyal Kanıt Bonusu
    if deal.get("is_bestseller") or "çok satan" in str(deal.get("badge") or "").lower():
        score += 35.0

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
        "ayakkabı", "sneaker", "adidas", "puma", "nike", "under armour", "skechers",
        "parfüm", "edp", "edt", "body mist", "calvin klein", "versace", "davidoff", "slazenger", "privacy",
        "casio", "g-shock", "edifice", "saat",
        "çanta", "sırt çantası", "cüzdan", "eastpak", "herschel",
        "hoodie", "sweatshirt", "polar", "columbia", "jack & jones", "levi's",
        "projektör", "projeksiyon", "monitör lambası", "maskara", "lip gloss",
        "anker", "jbl", "sony", "marshall",
        "lenovo", "legion", "msi", "acer nitro", "hp victus"
    ]
    if any(k in title for k in VIRAL_KEYWORDS):
        score += 30

    # TikTok Viral Makyaj & Kozmetik Dünyası Bonusu (+35 Puan - Gloss, Maskara, Allık, Kapatıcı)
    is_viral_beauty = any(k in title for k in [
        "maskara", "rimel", "sky high", "lash sensational", "telescopic", "panorama",
        "gloss", "lip gloss", "dudak yağı", "dudak parlatıcı", "ruj", "dudak kalemi", "lip tint",
        "allık", "blush", "glotion", "aydınlatıcı", "highlighter", "kapatıcı", "concealer",
        "fondöten", "eyeliner", "göz kalemi", "kaş maskarası",
        "maybelline", "l'oreal", "golden rose", "kiko", "flormar", "essence", "nyx", "revolution", "pastel"
    ])
    if is_viral_beauty:
        score += 35.0

    # 4. Hızlı Satın Alma (Impulse Buy) Fiyat Puanlaması (Altın Nokta: 100 TL - 1.500 TL, Tavan: 2.250 TL)
    # Kozmetikte (gloss, maskara, dudak kalemi) 100-450 TL arası izleyicinin düşünmeden anında sepete attığı altın banddır
    if 100 <= new_p <= 1500:
        score += 45.0  # Altın Dürtüsel Satın Alma Bandı (+45 Puan)
    elif 1500 < new_p <= 2250:
        score += 15.0  # Makul orta bütçe (Sneaker / Klavye / Kulaklık tavanı)
    elif new_p > 2250:
        score -= 80.0  # Pahalı ürün cezası (2.250 TL üzeri ürünler sosyal medyada anlık satılmaz)
    elif new_p < 100:
        score -= 40.0  # Çok ucuz sarf malzemesi/vida cezası

    # Stanley / Termos Yorgunluğu Koruması (Aynı markanın farklı litre varyasyonlarının sürekli çıkmasını engelle)
    if "stanley" in title:
        score -= 25.0

    return score

MIN_PRODUCT_PRICE_TL = 100   # 100 TL alt sınır (Viral Gloss/Makyaj ve F/P ürünler için ideal)
MAX_PRODUCT_PRICE_TL = 2250  # 2.250 TL kesin üst sınır (Kimse Shorts/TikTok kaydırırken 3.000 TL+ ürün almaz)

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

_GEMINI_COOLDOWN_UNTIL = 0.0

def call_gemini(prompt: str, json_mode: bool = True, image_path: str = None) -> dict:
    """
    Gemini modellerine sorgu atar, çoklu model fallback ve güvenli JSON ayrıştırma uygular.
    Kota aşımı (429) durumunda otomatik soğuma (cooldown) uygulayarak sistemi bekletmez.
    """
    import time as _time
    global _GEMINI_COOLDOWN_UNTIL
    if _time.time() < _GEMINI_COOLDOWN_UNTIL:
        return None

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

    quota_errors = 0
    for model in MODEL_CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY.strip()}"
        data = None
        # Doğrudan curl -4 ile tek seferde güvenli çağrı (Windows SSL ve Bulut IPv6 hatalarını %100 önler)
        cmd = get_curl_cmd(["--max-time", "12", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", f"@{req_file}", url])
        res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            data = json.loads(res.stdout)
            if isinstance(data, dict) and "error" in data:
                err_code = data["error"].get("code")
                if err_code in (429, 503):
                    quota_errors += 1
                continue
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

    if quota_errors > 0:
        _GEMINI_COOLDOWN_UNTIL = _time.time() + 180.0
    return None

def _build_short_clean_title(raw_title: str) -> str:
    """Uzun e-ticaret başlığından maksimum 28 karakterlik net marka + model başlığı üretir."""
    clean = re.split(r"[,|–—\(\[]| - ", raw_title)[0].strip()
    clean = re.sub(r"\s+", " ", clean)
    words = clean.split()
    if len(clean) <= 28:
        return clean
    out = []
    for w in words:
        if len(" ".join(out + [w])) <= 28:
            out.append(w)
        else:
            break
    return " ".join(out) if out else clean[:28].strip()

def _deterministic_analyze_amazon_deal(raw_title: str, raw_price: str, prod_url: str, rating_val: float = 0.0, review_count: int = 0) -> dict:
    """
    Gemini API kotası (429/503) dolu olduğunda devreye giren Sıfır-Kota Akıllı Fırsat Analizcisi.
    Yalnızca A-Sınıfı (Tier-1) markaları veya Geniş Kitle (Mass-Appeal) ürünlerini kabul eder,
    canlı Amazon sayfasından veya piyasa verisinden gerçek fiyat/indirim hesabını yapar.
    """
    t_low = (raw_title or "").lower()
    is_t1 = has_tier1_brand(raw_title)
    is_broad = any(kw in t_low for kw in BROAD_AUDIENCE_KEYWORDS)
    is_high_demand = any(kw in t_low for kw in HIGH_DEMAND_KEYWORDS)

    # AGENTS.md Kural 1: Geniş kitleye hitap eden ana ürün kategorisinde olmayan ürünleri kesinlikle ele
    if not is_mass_appeal_product(raw_title):
        return None

    new_p_val = parse_price_to_float(raw_price)
    if new_p_val < MIN_PRODUCT_PRICE_TL or new_p_val > MAX_PRODUCT_PRICE_TL:
        return None

    short_title = _build_short_clean_title(raw_title)
    old_p_val = 0.0

    # Canlı ürün sayfasından gerçek üstü çizili fiyatı (basisPrice) veya kuponu sorgula
    coupon_amount = 0.0
    try:
        from product_verifier import verify_amazon_product
        v_live = verify_amazon_product(prod_url)
        if v_live.get("success") and not v_live.get("in_stock", True):
            return None
        strike = float(v_live.get("real_strike_val") or 0.0)
        live_p = float(v_live.get("live_price_val") or 0.0)
        coupon_amount = float(v_live.get("coupon_amount_tl") or 0.0)
        if live_p > 0:
            new_p_val = live_p
            raw_price = f"{int(new_p_val):,} TL".replace(",", ".")
        if strike >= new_p_val * 1.10:
            old_p_val = strike
        elif coupon_amount > 0:
            old_p_val = new_p_val + coupon_amount
    except Exception:
        pass

    # DÜRÜSTLÜK İLKESİ (deal-truthfulness): Sayfada gerçek indirim veya kupon yoksa sahte liste fiyatı uydurma!
    if old_p_val < new_p_val * 1.10 and coupon_amount <= 0:
        return None

    pct = int(round(((old_p_val - new_p_val) / old_p_val) * 100)) if old_p_val > new_p_val else 0
    if pct < 15 and coupon_amount <= 0:
        return None

    old_price_str = f"{int(old_p_val):,} TL".replace(",", ".")
    new_price_str = f"{int(new_p_val):,} TL".replace(",", ".")
    des_score = 9 if (is_t1 and (is_broad or is_high_demand)) else 8
    badge = "DİP FİYAT" if pct >= 45 else ("DEV İNDİRİM" if pct >= 35 else "AMAZON FIRSATI")

    return {
        "title": short_title,
        "old_price": old_price_str,
        "new_price": new_price_str,
        "discount_pct": f"-{pct}%",
        "desirability_score": des_score,
        "badge": badge,
        "hook": f"{short_title} şimdi Amazon TR'de özel indirimle!"
    }

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
    ("KULAKLIKLAR", "https://www.amazon.com.tr/gp/bestsellers/electronics/17471820031"),
    ("KLAVYELER_VE_FARELER", "https://www.amazon.com.tr/gp/bestsellers/computers/12601919031"),
    ("PC_OYUN_DONANIM", "https://www.amazon.com.tr/gp/bestsellers/computers/12601923031"),
    ("HOPARLÖRLER", "https://www.amazon.com.tr/gp/bestsellers/electronics/13709886031"),
    ("KLAVYE_MOUSE_AKSESUAR", "https://www.amazon.com.tr/gp/bestsellers/computers/12601894031"),
    ("MONİTÖRLER", "https://www.amazon.com.tr/gp/bestsellers/computers/12601904031"),
    ("GAMING", "https://www.amazon.com.tr/gp/bestsellers/videogames"),
    ("PATLAYAN_GAMING", "https://www.amazon.com.tr/gp/movers-and-shakers/videogames"),
    ("BİLGİSAYAR", "https://www.amazon.com.tr/gp/bestsellers/computers"),
    ("PATLAYAN_BİLGİSAYAR", "https://www.amazon.com.tr/gp/movers-and-shakers/computers"),
    ("ELEKTRONİK", "https://www.amazon.com.tr/gp/bestsellers/electronics"),
    ("PATLAYAN_ELEKTRONİK", "https://www.amazon.com.tr/gp/movers-and-shakers/electronics"),
    ("SPOR_AYAKKABI_SNEAKER", "https://www.amazon.com.tr/gp/bestsellers/fashion/69339631031"),
    ("MODA_CANTA_SAAT_HOODIE", "https://www.amazon.com.tr/gp/bestsellers/fashion/69340196031"),
    ("SPOR_OUTDOOR_CANTA", "https://www.amazon.com.tr/gp/bestsellers/sporting-goods"),
    ("PATLAYAN_AYAKKABI", "https://www.amazon.com.tr/gp/movers-and-shakers/fashion/69339631031"),
    ("GÖZ_MAKYAJI_MASKARA", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571758031"),
    ("DUDAK_LIP_GLOSS", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571757031"),
    ("YÜZ_MAKYAJI_ALLIK", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571763031"),
    ("CİLT_BAKIMI", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571730031"),
    ("PARFÜMLER", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571733031"),
    ("MAKYAJ", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571731031"),
    ("SAÇ_BAKIMI", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571734031")
]

CAT_ROTATION_FILE = os.path.join(TEMP_DIR, "amazon_cat_rot.txt")

def get_rotated_amazon_catalogs():
    # Bulut (stateless) çalışmalarda her saat kuşağının farklı kategoriden başlaması için saat bazlı ofset
    idx = (datetime.now().hour * 2 + (1 if datetime.now().minute >= 25 else 0)) % len(AMAZON_CATALOG_SOURCES)
    try:
        if os.path.exists(CAT_ROTATION_FILE):
            with open(CAT_ROTATION_FILE, "r") as f:
                idx = int(f.read().strip()) % len(AMAZON_CATALOG_SOURCES)
    except Exception:
        pass
    
    rotated = AMAZON_CATALOG_SOURCES[idx:] + AMAZON_CATALOG_SOURCES[:idx]
    next_idx = (idx + 1) % len(AMAZON_CATALOG_SOURCES)
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(CAT_ROTATION_FILE, "w") as f:
            f.write(str(next_idx))
    except Exception:
        pass
    return rotated

def hunt_amazon_deals(limit: int = 3, category: str = "all", exclude_urls: set = None, exclude_subtypes: set = None, exclude_brands: set = None, min_discount: int = 25) -> list:
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
    elif category in ("beauty", "cosmetics", "care", "skincare"):
        _top_makeup = [
            ("GÖZ_MAKYAJI_MASKARA", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571758031"),
            ("DUDAK_LIP_GLOSS", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571757031"),
            ("YÜZ_MAKYAJI_ALLIK", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571763031"),
            ("MAKYAJ", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571731031"),
        ]
        _other_beauty = [
            ("PARFÜMLER", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571733031"),
            ("CİLT_BAKIMI", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571730031"),
            ("PATLAYAN_GÜZELLİK", "https://www.amazon.com.tr/gp/movers-and-shakers/beauty"),
            ("SAÇ_BAKIMI", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571734031")
        ]
        # TikTok ve kadın fırsatlarında 1. öncelik her zaman viral makyajdır (Göz, Dudak/Gloss, Allık)
        _m_idx = (datetime.now().hour * 2 + (1 if datetime.now().minute >= 25 else 0)) % len(_top_makeup)
        url_categories = (_top_makeup[_m_idx:] + _top_makeup[:_m_idx]) + _other_beauty
    elif category in ("tech", "gaming_tech"):
        _tech_list = [
            ("FIRSAT_KULAKLIK", "https://www.amazon.com.tr/s?k=kulakl%C4%B1k&rh=p_n_deal_type%3A26901188031"),
            ("FIRSAT_GAMING", "https://www.amazon.com.tr/s?k=oyuncu&rh=p_n_deal_type%3A26901188031"),
            ("FIRSAT_SNEAKER", "https://www.amazon.com.tr/s?k=spor+ayakkab%C4%B1&rh=p_n_deal_type%3A26901188031"),
            ("FIRSAT_KLAVYE", "https://www.amazon.com.tr/s?k=klavye&rh=p_n_deal_type%3A26901188031"),
            ("KULAKLIKLAR", "https://www.amazon.com.tr/gp/bestsellers/electronics/17471820031"),
            ("KLAVYELER_VE_FARELER", "https://www.amazon.com.tr/gp/bestsellers/computers/12601919031"),
            ("PC_OYUN_DONANIM", "https://www.amazon.com.tr/gp/bestsellers/computers/12601923031"),
            ("KLAVYE_MOUSE_AKSESUAR", "https://www.amazon.com.tr/gp/bestsellers/computers/12601894031"),
            ("HOPARLÖRLER", "https://www.amazon.com.tr/gp/bestsellers/electronics/13709886031"),
            ("GAMING", "https://www.amazon.com.tr/gp/bestsellers/videogames"),
            ("MONİTÖRLER", "https://www.amazon.com.tr/gp/bestsellers/computers/12601904031"),
            ("BİLGİSAYAR", "https://www.amazon.com.tr/gp/bestsellers/computers"),
            ("PATLAYAN_GAMING", "https://www.amazon.com.tr/gp/movers-and-shakers/videogames"),
            ("PATLAYAN_BİLGİSAYAR", "https://www.amazon.com.tr/gp/movers-and-shakers/computers"),
            ("SPOR_AYAKKABI_SNEAKER", "https://www.amazon.com.tr/gp/bestsellers/fashion/69339631031"),
            ("MODA_CANTA_SAAT_HOODIE", "https://www.amazon.com.tr/gp/bestsellers/fashion/69340196031"),
            ("SPOR_OUTDOOR_CANTA", "https://www.amazon.com.tr/gp/bestsellers/sporting-goods"),
            ("PATLAYAN_AYAKKABI", "https://www.amazon.com.tr/gp/movers-and-shakers/fashion/69339631031")
        ]
        _t_idx = (datetime.now().hour * 2 + (1 if datetime.now().minute >= 25 else 0)) % len(_tech_list)
        url_categories = _tech_list[_t_idx:] + _tech_list[:_t_idx]
    else:
        url_categories = get_rotated_amazon_catalogs()

    deals = []
    seen_subtypes = set(exclude_subtypes) if exclude_subtypes else set()
    seen_brands = set(exclude_brands) if exclude_brands else set()

    for cat_name, target_url in url_categories:
        if len(deals) >= limit:
            break

        print(f"[Deal Hunter] Doğrudan Amazon TR ({cat_name}) taranıyor: {target_url}...")
        _ua_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        ]
        res = None
        for _ua in _ua_pool:
            cmd = get_curl_cmd([
                "--compressed", "-s", "-L",
                "-H", f"User-Agent: {_ua}",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
                target_url
            ])
            res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if res.returncode == 0 and len(res.stdout) > 20000 and "validatecaptcha" not in res.stdout.lower():
                break
        if not res or res.returncode != 0 or len(res.stdout) < 10000:
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

        # 2. Standart HTML ürün kartlarını tara (Modern Amazon DOM + Legacy Destekli)
        soup = BeautifulSoup(res.stdout, "html.parser")
        items = soup.select("div[data-component-type='s-search-result'], div[id*='gridItemRoot'], .p13n-grid-content, .zg-grid-general-faceout, .p13n-sc-uncoverable-faceout, div[data-asin]")

        for it in items:
            title_el = it.select_one("div[class*='line-clamp-'], h2, div._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y, div._cDEzb_p13n-sc-css-line-clamp-2_EWgt-") or it.find("h2") or it.find("span")
            price_el = it.select_one(".a-price .a-offscreen, span[class*='price'], .p13n-sc-price") or it.find("span", class_=lambda c: c and "price" in c)
            img_el = it.find("img")
            link_el = it.select_one("a[href*='/dp/']") or it.find("a", href=re.compile(r"/dp/"))

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
            strike_el = it.select_one("span.a-price.a-text-price span.a-offscreen, .basisPrice .a-offscreen, span[class*='basisPrice']")
            h_strike_price = strike_el.text.strip() if strike_el else ""
            h_discount_pct = ""
            h_discount_val = 0
            if h_strike_price and h_price:
                s_f = parse_price_to_float(h_strike_price)
                p_f = parse_price_to_float(h_price)
                if s_f > p_f > 0:
                    h_discount_val = round(((s_f - p_f) / s_f) * 100)
                    h_discount_pct = f"-{h_discount_val}%"
            if not h_discount_pct:
                pct_m = re.search(r"-\s*(\d+)%", h_card_text)
                if pct_m:
                    h_discount_val = int(pct_m.group(1))
                    h_discount_pct = f"-{h_discount_val}%"

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
                "raw_strike_price": h_strike_price,
                "discount_pct": h_discount_pct,
                "discount_val": h_discount_val,
                "big_img": h_big_img,
                "raw_img": h_img,
                "prod_url": h_url,
                "asin": h_asin,
                "rating_val": h_rating,
                "review_count": h_reviews
            })

        # Adayları ASIN / URL bazında tekilleştir (Mükerrer DOM taramalarını önle)
        seen_cand_sigs = set()
        unique_cands = []
        for cand in parsed_candidates:
            cand_sig = cand.get("asin") or cand.get("prod_url") or cand.get("raw_title")
            if cand_sig and cand_sig not in seen_cand_sigs:
                seen_cand_sigs.add(cand_sig)
                unique_cands.append(cand)
        parsed_candidates = unique_cands

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

            # 2. Alt tip ve marka anti-tekrar koruması (örn: peş peşe 2 kol/gamepad gelmez, aynı marka sürekli tekrar etmez)
            raw_subtype = get_product_subtype(raw_title)
            raw_brand = extract_brand(raw_title)

            if raw_subtype != "general" and raw_subtype in seen_subtypes:
                print(f"[Deal Hunter] ⏭️ Çeşitlilik Koruması (Alt Kategori '{raw_subtype}' beklemede): {raw_title[:38]}")
                continue

            if raw_brand and raw_brand in seen_brands:
                print(f"[Deal Hunter] ⏭️ Marka Koruması ('{raw_brand.upper()}' yakın zamanda paylaşıldı): {raw_title[:38]}")
                continue

            # Stanley & Termos Özel Koruması (Farklı litre/modellerin üst üste gelmesini %100 engeller)
            if "stanley" in raw_title.lower() and ("stanley" in seen_brands or "thermos" in seen_subtypes):
                print(f"[Deal Hunter] ⏭️ Stanley Termos Koruması (Yakın zamanda Stanley paylaşıldı): {raw_title[:38]}")
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

            # Ön Filtre (AGENTS.md Kural 1): Yalnızca geniş kitleye hitap eden ana ürünleri kabul et (aksesuar/kit/parça elenir)!
            if not is_mass_appeal_product(raw_title):
                continue

            print(f"[Deal Hunter] Aday Ürün Analiz Ediliyor ({cat_name}): {raw_title[:45]} | {raw_price}")

            prompt = f"""Şu popüler Amazon Türkiye ürününün başlığını temizle ve sosyal medyada satın alınma cazibesini puanla:
Ürün: {raw_title}
Amazon Satış Fiyatı: {raw_price}

GÖREV:
1. Ürünün maksimum 28 karakterlik, net ve temiz marka + model başlığını yaz (Asla uzun e-ticaret metni bırakma!).
2. DÜRÜSTLÜK KURALI (deal-truthfulness): Sayfada gerçek indirim yoksa kafadan eski piyasa fiyatı uydurma!
3. VİTRİN & ARZU TESTİ (desirability_score: 1-10): Bu ürün Shorts ve TikTok'ta paylaşıldığında insanların "Bu fiyata kaçmaz!" deyip sepete atacağı popüler bir ürün mü? (Gerçekten cazip ürünlere 8-10, sıradan/ilgisiz ürünlere 1-6 ver).

Şu JSON formatında döndür:
{{
  "title": "Ürünün kısa, vurucu ve net adı (maksimum 28 karakter, örn: Adidas Advantage Sneaker, Casio Retro Saat, JBL Wave Flex vb.)",
  "old_price": "",
  "new_price": "{raw_price}",
  "discount_pct": "",
  "desirability_score": 9,
  "badge": "AMAZON FIRSATI",
  "hook": "Kullanıcıların bu ürünü neden kaçırmaması gerektiğini anlatan tek cümle"
}}
"""
            deal_data = call_gemini(prompt, json_mode=True)
            if not deal_data or not deal_data.get("title"):
                deal_data = _deterministic_analyze_amazon_deal(raw_title, raw_price, prod_url, rating_val, review_count)
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

            if cand.get("raw_strike_price") and not deal_data.get("old_price"):
                deal_data["old_price"] = cand["raw_strike_price"]
            if cand.get("discount_pct") and not deal_data.get("discount_pct"):
                deal_data["discount_pct"] = cand["discount_pct"]

            # Minimum İndirim Oranı Kontrolü
            pct_val = get_deal_discount_pct(deal_data)
            if pct_val < min_discount and ("FIRSAT" in cat_name or "deals" in target_url):
                try:
                    from product_verifier import verify_amazon_product
                    quick_v = verify_amazon_product(prod_url, expected_title=deal_data.get("title", raw_title))
                    if quick_v.get("success") and quick_v.get("real_strike_val", 0) > 0:
                        live_p = quick_v.get("live_price_val") or parse_price_to_float(raw_price)
                        real_s = quick_v["real_strike_val"]
                        if real_s > live_p > 0:
                            calc_pct = round(((real_s - live_p) / real_s) * 100)
                            deal_data["old_price"] = f"{int(real_s):,} TL".replace(',', '.')
                            deal_data["discount_pct"] = f"-{calc_pct}%"
                            pct_val = calc_pct
                except Exception:
                    pass

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
    tokens = [w for w in s.split() if (len(w) >= 2 or w.isdigit()) and w not in stop_words]
    return " ".join(tokens[:3])

def is_deal_already_shared(title: str, url: str, exclude_urls: set) -> bool:
    """Ürünün URL, ASIN veya marka+model başlığı bazında daha önce paylaşılıp paylaşılmadığını denetler."""
    if not exclude_urls:
        return False
    url_clean = (url or "").split("?")[0].strip().lower()
    asin_m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url or "", re.IGNORECASE)
    asin = asin_m.group(1).upper() if asin_m else ""
    norm_cand = _normalize_title_tokens(title)
    cand_words = norm_cand.split() if norm_cand else []

    for ex in exclude_urls:
        if not ex:
            continue
        ex_str = str(ex).strip()
        ex_low = ex_str.lower()
        if url_clean and len(url_clean) > 12 and (url_clean in ex_low or ex_low.split("?")[0] == url_clean):
            return True
        if asin and asin.lower() in ex_low:
            return True
        if not ex_str.startswith("http") and len(cand_words) >= 2:
            norm_ex = _normalize_title_tokens(ex_str)
            ex_words = norm_ex.split() if norm_ex else []
            if len(ex_words) >= 2 and norm_cand == norm_ex:
                return True
    return False

def hunt_online_deals(limit: int = 5, channels: list = None, exclude_urls: set = None, min_discount: int = 25, platform: str = "all") -> list:
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

            # Mağaza tespit et (Amazon TR, Trendyol, Hepsiburada) - AI çağrısından önce filtrele!
            store_name = detect_store(store_url, raw_text)
            if platform == "amazon" and store_name != "Amazon TR":
                continue
            if platform == "trendyol" and store_name != "Trendyol":
                continue
            if platform == "hepsiburada" and store_name != "Hepsiburada":
                continue

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

            if is_vague_deal(deal_data.get("title", ""), raw_text) or not (is_mass_appeal_product(deal_data.get("title", "")) or is_mass_appeal_product(raw_text)):
                print(f"[Deal Hunter] ⏭️ Geniş Kitle Dışı / Niş Ürün Elendi: {deal_data.get('title')}")
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

def hunt_best_deals(limit: int = 3, platform: str = "amazon", category: str = "all", exclude_urls: set = None, exclude_subtypes: set = None, exclude_brands: set = None, min_discount: int = 25) -> list:
    """
    Amazon TR, Hepsiburada ve Trendyol üzerindeki EN ARZU EDİLEN ve EN YÜKSEK İNDİRİMLİ fırsatları avlar.
    6 Katmanlı Akıllı Keşif Motoru ile saçma/fason ürünleri eler, A-Sınıfı marka ve çok satan fırsatları zirveye taşır.
    """
    candidates = []
    print(f"\n[Deal Hunter] 🔍 6 Katmanlı Akıllı İndirim Avı Başlatıldı (Öncelikli Mağaza: AMAZON TR, Mod: {platform.upper()}, Min İndirim: %{min_discount})...")

    # 1. Amazon TR Kataloglarından Çek (Movers & Shakers + Çok Satanlar + Fırsatlar rotasyonlu)
    if platform in ("all", "amazon"):
        amz_deals = hunt_amazon_deals(limit=min(limit, 4), category=category, exclude_urls=exclude_urls, exclude_subtypes=exclude_subtypes, exclude_brands=exclude_brands, min_discount=min_discount)
        for d in amz_deals:
            d["store_name"] = "Amazon TR"
            candidates.append(d)

    # 2. Sıcak Fırsat Kanallarından Taze Fırsatları Çek (Yalnızca Amazon taraması yeterli aday bulamadıysa çalışır -> Bulut hızını 5x artırır!)
    if len(candidates) < 2:
        online_deals = hunt_online_deals(limit=limit + 2, exclude_urls=exclude_urls, min_discount=min_discount, platform=platform)
        for d in online_deals:
            st = d.get("store_name", "Fırsat")
            if platform == "amazon" and st != "Amazon TR":
                continue
            if platform == "trendyol" and st != "Trendyol":
                continue
            if platform == "hepsiburada" and st != "Hepsiburada":
                continue
            sub = get_product_subtype(d.get("title", ""))
            b = extract_brand(d.get("title", ""))
            if exclude_subtypes and sub in exclude_subtypes and sub != "general":
                continue
            if exclude_brands and b and b in exclude_brands:
                continue
            if "stanley" in d.get("title", "").lower() and ("stanley" in (exclude_brands or set()) or "thermos" in (exclude_subtypes or set())):
                continue
            # YouTube / Tech kategorisi için kozmetik/makyaj filtresi
            if category in ("tech", "gaming", "computers", "electronics", "monitors") and is_beauty_product(d.get("title", "")):
                print(f"[Deal Hunter] 🛡️ YouTube/Tech Filtresi: Online kanaldan gelen kozmetik ürünü elendi -> {d.get('title')}")
                continue
            candidates.append(d)

    # Eğer ilk taramada aday bulunamadıysa eşiği %15'e indirip çeşitlilik kısıtını gevşeterek TEK SEFERLİK genel tarama yap (Sonsuz döngü ve çift tarama korumalı!)
    if not candidates and (min_discount > 15 or exclude_subtypes or exclude_brands):
        print("[Deal Hunter] ⚠️ İlk turda uygun ürün bulunamadı. İndirim eşiği %15'e ve çeşitlilik filtresi esnetilerek tek seferlik genel tarama yapılıyor...")
        return hunt_best_deals(limit=limit, platform=platform, category=category, exclude_urls=exclude_urls, exclude_subtypes=None, exclude_brands=None, min_discount=15)

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

        # 1. ÖNCELİK: Geniş Kitleye Hitap Eden Ürün (Mass-Appeal Directive)
        # Herkesin evinde, masasında, cebinde isteyeceği kitlesel tüketici ürünlerine dev öncelik (+85 puan)
        # Dar niş, teknik aparat, yedek parça ve sarf malzemelerine anında eleme cezası (-200 puan)
        is_broad = any(kw in title for kw in BROAD_AUDIENCE_KEYWORDS)
        if is_broad:
            score += 85.0
        elif BORING_REGEX.search(title):
            score -= 200.0

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

    if category in ("tech", "gaming", "computers", "electronics", "monitors"):
        candidates = [c for c in candidates if not is_beauty_product(c.get("title", ""))]

    candidates.sort(key=score_deal, reverse=True)

    # Çeşitlilik süzgeci: Tek bir listede aynı ürün tipinden veya markadan birden fazla olmasın
    best_deals = []
    seen_types = set(exclude_subtypes) if exclude_subtypes else set()
    seen_b = set(exclude_brands) if exclude_brands else set()
    for d in candidates:
        if len(best_deals) >= limit:
            break
        st = get_product_subtype(d.get("title", ""))
        b = extract_brand(d.get("title", ""))
        if st != "general" and st in seen_types:
            continue
        if b and b in seen_b:
            continue
        if "stanley" in d.get("title", "").lower() and ("stanley" in seen_b or "thermos" in seen_types):
            continue
        best_deals.append(d)
        if st != "general":
            seen_types.add(st)
        if b:
            seen_b.add(b)

    # Eğer çeşitlilik kuralı nedeniyle limit dolmadıysa kalan adaylardan tamamla (Stanley hariç)
    if len(best_deals) < limit:
        for d in candidates:
            if len(best_deals) >= limit:
                break
            if d not in best_deals:
                if "stanley" in d.get("title", "").lower() and ("stanley" in seen_b or "thermos" in seen_types):
                    continue
                best_deals.append(d)

    if category in ("tech", "gaming", "computers", "electronics", "monitors"):
        best_deals = [c for c in best_deals if not is_beauty_product(c.get("title", ""))]

    print(f"\n[Deal Hunter] 🏆 EN YÜKSEK İNDİRİMLİ {len(best_deals)} FIRSAT SEÇİLDİ:")
    for i, d in enumerate(best_deals, 1):
        pct = get_deal_discount_pct(d)
        savings = get_deal_savings_tl(d)
        print(f"  {i}. [{d.get('store_name', 'Fırsat')}] {d.get('title')} | {d.get('new_price')} (İndirim: -%{pct} | Tasarruf: {int(savings)} TL)")

    return best_deals

def hunt_bestseller_deals(limit: int = 3, category: str = "tech", exclude_urls: list = None) -> list:
    """
    Normal indirim bulunamadığında devreye giren Emniyet Sibopu:
    Amazon TR'deki resmi Çok Satanlar (Best Sellers) sayfalarını tarar ve
    en yüksek puanlı, en popüler 1 numaralı kahraman ürünleri getirir.
    Sahte indirim üretmez, '🔥 #1 ÇOK SATAN' şablonuyla dürüstçe sunar.
    """
    if exclude_urls is None:
        exclude_urls = []

    cat_low = (category or "tech").lower()
    if cat_low in ("beauty", "cosmetics", "skincare"):
        bestseller_catalogs = [
            ("MAKYAJ_ALLIK_KAPATICI", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571763031"),
            ("GOZ_MAKYAJI_MASKARA", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571764031"),
            ("DUDAK_GLOSS", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571765031"),
            ("PARFUM", "https://www.amazon.com.tr/gp/bestsellers/beauty/12571766031"),
            ("GENEL_GUZELLIK", "https://www.amazon.com.tr/gp/bestsellers/beauty")
        ]
    elif cat_low in ("fashion", "sneaker"):
        bestseller_catalogs = [
            ("SPOR_AYAKKABI_SNEAKER", "https://www.amazon.com.tr/gp/bestsellers/fashion/69339631031"),
            ("MODA_CANTA", "https://www.amazon.com.tr/gp/bestsellers/fashion/69340196031")
        ]
    else: # tech / gaming
        bestseller_catalogs = [
            ("KULAKLIKLAR", "https://www.amazon.com.tr/gp/bestsellers/electronics/17471820031"),
            ("KLAVYELER_VE_FARELER", "https://www.amazon.com.tr/gp/bestsellers/computers/12601919031"),
            ("PC_OYUN_DONANIM", "https://www.amazon.com.tr/gp/bestsellers/computers/12601923031"),
            ("HOPARLÖRLER", "https://www.amazon.com.tr/gp/bestsellers/electronics/13709886031"),
            ("GAMING", "https://www.amazon.com.tr/gp/bestsellers/videogames"),
            ("SPOR_AYAKKABI_SNEAKER", "https://www.amazon.com.tr/gp/bestsellers/fashion/69339631031")
        ]

    deals = []
    seen_asins = set()
    _ua_pool = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    ]

    for cat_name, target_url in bestseller_catalogs:
        if len(deals) >= limit:
            break

        print(f"[Bestseller Radar] 🏆 Amazon TR ({cat_name}) Çok Satanlar taranıyor: {target_url}...")
        res = None
        for _ua in _ua_pool:
            cmd = get_curl_cmd([
                "--compressed", "-s", "-L",
                "-H", f"User-Agent: {_ua}",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: tr-TR,tr;q=0.9,en-US;q=0.8",
                target_url
            ])
            res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if res.returncode == 0 and len(res.stdout) > 20000 and "validatecaptcha" not in res.stdout.lower():
                break

        if not res or res.returncode != 0 or len(res.stdout) < 10000:
            continue

        soup = BeautifulSoup(res.stdout, "html.parser")
        items = soup.select("div[data-component-type='s-search-result'], div[id*='gridItemRoot'], .p13n-grid-content, .zg-grid-general-faceout, .p13n-sc-uncoverable-faceout, div[data-asin]")

        for it in items:
            if len(deals) >= limit:
                break

            title_el = it.select_one("div[class*='line-clamp-'], h2, div._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y, div._cDEzb_p13n-sc-css-line-clamp-2_EWgt-") or it.find("h2") or it.find("span")
            price_el = it.select_one(".a-price .a-offscreen, span[class*='price'], .p13n-sc-price") or it.find("span", class_=lambda c: c and "price" in c)
            img_el = it.find("img")
            link_el = it.select_one("a[href*='/dp/']") or it.find("a", href=re.compile(r"/dp/"))

            if not (title_el and price_el and img_el and link_el):
                continue

            raw_title = title_el.text.strip()
            raw_price = price_el.text.strip()
            raw_img = img_el.get("src", "")
            big_img = re.sub(r'\._AC_.*?_\.', '._AC_SL1000_.', raw_img)
            href = link_el.get("href", "")
            asin_m = re.search(r"/dp/([A-Z0-9]{10})", href, re.IGNORECASE)
            asin = asin_m.group(1).upper() if asin_m else None
            if asin and asin in seen_asins:
                continue
            prod_url = f"https://www.amazon.com.tr/dp/{asin}" if asin else ("https://www.amazon.com.tr" + href.split("?")[0])

            if BORING_REGEX.search(raw_title):
                continue
            if not is_mass_appeal_product(raw_title):
                continue
            if cat_low in ("tech", "gaming_tech") and is_beauty_product(raw_title):
                continue
            if is_deal_already_shared(raw_title, prod_url, exclude_urls):
                continue

            try:
                p_clean = re.sub(r"[^\d]", "", raw_price.split(",")[0])
                if p_clean:
                    p_num = int(p_clean)
                    min_p = 100 if cat_low == "beauty" else 300
                    max_p = 2500 if cat_low == "beauty" else 8500
                    if p_num < min_p or p_num > max_p:
                        continue
            except Exception:
                pass

            strike_el = it.select_one("span.a-price.a-text-price span.a-offscreen, .basisPrice .a-offscreen")
            raw_strike = strike_el.text.strip() if strike_el else ""
            disc_pct = ""
            if raw_strike and raw_price:
                s_f = parse_price_to_float(raw_strike)
                p_f = parse_price_to_float(raw_price)
                if s_f > p_f > 0:
                    pct_calc = round(((s_f - p_f) / s_f) * 100)
                    disc_pct = f"-{pct_calc}%"

            clean_title = raw_title[:34]
            prompt = f"Şu ürünün başlığını temizle. Sadece net marka ve model adını yaz, başka hiçbir açıklama, yorum veya parantez içi not yazma (Örnek: Apple EarPods USB-C): {raw_title}"
            ai_title = call_gemini(prompt, json_mode=False)
            if isinstance(ai_title, str) and ai_title.strip():
                clean_title = ai_title.strip().replace('"', '').replace("'", "")
            clean_title = re.sub(r"\(\s*\d+\s*karakter.*?\)", "", clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r"[\*\"\'`]", "", clean_title).strip()
            if len(clean_title) > 34:
                parts = clean_title[:34].rsplit(' ', 1)
                clean_title = parts[0].strip() if len(parts) > 1 else clean_title[:34].strip()

            if asin:
                seen_asins.add(asin)

            prod_id = asin or f"bs_{len(deals)+1}_{int(datetime.now().timestamp())}"
            img_path = os.path.join(TEMP_DIR, f"amz_{prod_id}.jpg")
            if not download_file(big_img, img_path):
                if not download_file(raw_img, img_path):
                    continue

            from campaign_calculator import calculate_campaign_and_net_cost
            camp = calculate_campaign_and_net_cost(raw_price, "Amazon TR")

            deal_obj = {
                "title": clean_title,
                "old_price": raw_strike if disc_pct else "",
                "new_price": raw_price,
                "discount_pct": disc_pct if disc_pct else "🔥 #1 ÇOK SATAN",
                "badge": "🔥 #1 ÇOK SATAN",
                "badge_text": "🔥 #1 ÇOK SATAN",
                "archetype": "bestseller_radar",
                "is_bestseller": True,
                "has_verified_old_price": bool(disc_pct),
                "image_path": img_path,
                "store_name": "Amazon TR",
                "store_url": prod_url,
                "asin": asin,
                "bank_campaign": camp["bank_campaign"],
                "net_cost": camp["net_cost"],
                "installment": camp["installment"],
                "source_channel": f"Amazon Bestsellers ({cat_name})",
                "killer_hook": "AMAZON #1 ÇOK SATAN!" if not disc_pct else "",
                "feature_pill": "AMAZON #1 ÇOK SATAN!" if not disc_pct else ""
            }
            deals.append(deal_obj)
            print(f"[Bestseller Radar] 🌟 #1 Çok Satan Adayı Eklendi: {clean_title} | {raw_price} | {prod_url}")

    return deals

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
