import os
import re
import json
import time
import subprocess
from config import BASE_DIR, ASSETS_DIR, TEMP_DIR, safe_run_subprocess

UNBOXING_DIR = os.path.join(ASSETS_DIR, "unboxing_library")
CACHE_FILE = os.path.join(BASE_DIR, "data", "unboxing_cache.json")

# Kutu açılışı / Deneyim videosu aranmayacak (doğrudan Meme'e düşecek) kategoriler
INELIGIBLE_KEYWORDS = [
    "şampuan", "krem", "deterjan", "yumuşatıcı", "diş macunu", "peçete", "tuvalet kağıdı",
    "bebek bezi", "sabun", "sıvı sabun", "zeytinyağı", "ayçiçek", "makarna", "pirinç",
    "çay", "kahve çekirdeği", "deterjanı", "çamaşır", "bulaşık", "ıslak mendil", "deodorant",
    "duş jeli", "parfüm", "çorap", "atlet", "boxer", "havlu", "çarşaf", "yastık kılıfı",
    "temizlik bezi", "çöp torbası", "çikolata", "bisküvi", "gofret", "cips", "kolonya",
    "nemlendirici", "losyon", "roll-on", "ped", "temizleme suyu", "pamuk"
]

# Kutu açılışı / ASMR / Donanım incelemesi son derece etkili olan kategoriler
ELIGIBLE_KEYWORDS = [
    "klavye", "keyboard", "mouse", "fare", "kulaklık", "headset", "earbuds", "tws",
    "monitör", "monitor", "ekran kartı", "gpu", "işlemci", "cpu", "anakart",
    "ram", "ssd", "kasa", "soğutucu", "güç kaynağı", "psu", "laptop", "dizüstü",
    "tablet", "ipad", "telefon", "akıllı telefon", "smartphone", "iphone", "galaxy",
    "saat", "akıllı saat", "smartwatch", "kol saati", "gamepad", "kol", "controller",
    "direksiyon", "hoparlör", "speaker", "soundbar", "mikrofon", "microphone",
    "şarj aleti", "charger", "powerbank", "adaptör", "dock", "hub", "kablo",
    "airfryer", "hava fritözü", "kahve makinesi", "robot süpürge", "dikey süpürge",
    "tıraş makinesi", "shaver", "saç kurutma", "fön", "projektör", "projeksiyon",
    "termos", "stanley", "matara", "çanta", "oyuncu koltuğu", "webcam", "kamera"
]

CLEANUP_WORDS = [
    "fırsatı", "indirimli", "orijinal", "kampanya", "hediyeli", "kaçırma", "en ucuz",
    "taksitli", "türkiye garantili", "resmi satıcı", "kampanyası", "özel fiyat",
    "yeni", "süper", "efsane", "rgb", "siyah", "beyaz", "gri", "mavi", "kırmızı",
    "kablosuz", "wireless", "bluetooth", "oyuncu", "gaming", "mekanik"
]


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[UnboxingManager] Önbellek yazma hatası: {e}")


def is_unboxing_eligible(deal: dict) -> bool:
    """
    Ürünün kutu açılış / ASMR inceleme videosuna uygun olup olmadığını denetler.
    Deterjan, gıda, şampuan gibi ürünlerde False dönerek doğrudan Meme formatına yönlendirir.
    """
    title = (deal.get("title") or "").lower()
    
    # 1. Hariç tutulan kelime var mı?
    for bad_kw in INELIGIBLE_KEYWORDS:
        if bad_kw in title:
            return False

    # 2. Uygun kelime var mı?
    for good_kw in ELIGIBLE_KEYWORDS:
        if good_kw in title:
            return True

    # 3. Belirtilmemişse ve fiyatı yüksek teknolojik ürün izlenimi veriyorsa
    try:
        price_val = float(str(deal.get("new_price", "0")).replace("TL", "").replace(".", "").replace(",", ".").strip())
        if price_val > 500:
            return True
    except Exception:
        pass

    return False


def extract_search_query(title: str) -> str:
    """
    Ürün başlığından temiz marka ve model ismini çıkarır.
    Örnek: 'Aula F75 RGB Kablosuz Mekanik Klavye' -> 'Aula F75 unboxing'
    """
    cleaned = title.lower()
    for w in CLEANUP_WORDS:
        cleaned = re.sub(rf"\b{re.escape(w)}\b", " ", cleaned)
    
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    words = [w for w in cleaned.split() if len(w) > 1]
    
    # İlk 2-3 vurucu kelimeyi al (Genelde Marka + Model Kodu)
    core = " ".join(words[:3]) if len(words) >= 3 else " ".join(words)
    return core.strip()


def get_smart_reaction_hook(title: str) -> str:
    """
    Ürünün kategorisine özel yüksek etkileşim kancası (Reaction Hook) üretir.
    """
    t = title.lower()
    if any(k in t for k in ["klavye", "keyboard"]):
        return "SESİ VE HİSSİYATI ŞAKA MI? 🔥✨"
    elif any(k in t for k in ["mouse", "fare"]):
        return "TASARIMI VE AKICILIĞI EFSANE! 🖱️⚡"
    elif any(k in t for k in ["kulaklık", "headset", "earbuds", "tws"]):
        return "SES KALİTESİ VE BASLAR ŞAKA MI? 🎧🔥"
    elif any(k in t for k in ["kol", "controller", "gamepad", "dualsense"]):
        return "HİSSİYATI VE TEPKİ SÜRESİ EFSANE! 🎮🔥"
    elif any(k in t for k in ["saat", "smartwatch"]):
        return "KOLDA DURUŞU VE TASARIMI ÇOK İYİ! ⌚✨"
    elif any(k in t for k in ["airfryer", "kahve", "termos", "stanley"]):
        return "KULLANIMI VE KALİTESİ ŞAKA MI? ✨🔥"
    elif any(k in t for k in ["monitör", "ekran"]):
        return "RENK CANLILIĞI VE AKICILIK EFSANE! 🖥️⚡"
    else:
        return "KUTU AÇILIŞI VE DETAYLAR ŞAHANE! ✨🔥"


def get_deal_unboxing_video(deal: dict, target_duration: float = 6.8) -> tuple[str, str] | None:
    """
    Format B (Hibrit Model) için ürünün gerçek kutu açılış/ASMR klibini bulur ve döner.
    - Uygun değilse veya video bulunamazsa -> None döner (Meme formatına otomatik fallback).
    - Bulunursa -> (video_path, reaction_text) tuple'ı döner.
    """
    if not is_unboxing_eligible(deal):
        return None

    os.makedirs(UNBOXING_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    title = deal.get("title", "")
    core_query = extract_search_query(title)
    if not core_query:
        return None

    slug = re.sub(r"[^\w]", "_", core_query.lower())[:30].strip("_")
    cached_video = os.path.join(UNBOXING_DIR, f"{slug}.mp4")
    smart_hook = get_smart_reaction_hook(title)

    # 1. Önbellekte var mı?
    if os.path.exists(cached_video) and os.path.getsize(cached_video) > 50000:
        print(f"📦 [UnboxingManager] Önbellekten bulundu: {cached_video}")
        return cached_video, smart_hook

    # 2. YouTube Shorts üzerinde arama yap
    search_term = f"{core_query} unboxing review"
    print(f"🔍 [UnboxingManager] YouTube üzerinde kutu açılış aranıyor: '{search_term}'...")

    try:
        cmd_search = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android",
            "--print", "%(id)s | %(duration)s | %(title)s",
            f"ytsearch3:{search_term}"
        ]
        res = safe_run_subprocess(cmd_search, capture_output=True, text=True, timeout=15)
        lines = [l.strip() for l in res.stdout.split("\n") if "|" in l]
        
        if not lines:
            print(f"⚠️ [UnboxingManager] Uygun kutu açılış videosu bulunamadı, Meme formatına dönülüyor.")
            return None

        chosen_id = None
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                vid_id, dur_str, vid_title = parts[0], parts[1], parts[2]
                try:
                    dur = float(dur_str)
                    if dur >= 8.0:
                        chosen_id = vid_id
                        print(f"🎯 [UnboxingManager] Seçilen video: {vid_title} (Süre: {dur}s, ID: {chosen_id})")
                        break
                except Exception:
                    chosen_id = vid_id
                    break

        if not chosen_id:
            return None

        # 3. Videonun en dinamik 8-10 saniyelik kısmını indir
        temp_raw = os.path.join(TEMP_DIR, f"raw_unbox_{chosen_id}.mp4")
        # 12. saniyeden 22. saniyeye (kutu açılışının tepe noktası)
        cmd_download = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android",
            "-f", "best[ext=mp4]/best",
            "--download-sections", "*00:00:12-00:00:22",
            "-o", temp_raw,
            f"https://www.youtube.com/watch?v={chosen_id}"
        ]
        dl_res = safe_run_subprocess(cmd_download, capture_output=True, text=True, timeout=25)
        
        # Eğer indirme başarısızsa ya da dosya oluşmadıysa baştan 00:00-00:10 indir
        if not os.path.exists(temp_raw) or os.path.getsize(temp_raw) < 10000:
            cmd_fallback_dl = [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android",
                "-f", "best[ext=mp4]/best",
                "--download-sections", "*00:00:00-00:00:10",
                "-o", temp_raw,
                f"https://www.youtube.com/watch?v={chosen_id}"
            ]
            safe_run_subprocess(cmd_fallback_dl, capture_output=True, text=True, timeout=20)

        if not os.path.exists(temp_raw) or os.path.getsize(temp_raw) < 10000:
            print(f"⚠️ [UnboxingManager] Video indirilemedi, Meme formatına dönülüyor.")
            return None

        # 4. ffmpeg ile tam target_duration (6.8s), 30fps ve SESSİZ STEREO SES İLE normalize et
        # Yabancı konuşmayı tamamen susturur; Instagram/Shorts içinde Trending Müzik eklenmesi için tertemiz zemin hazırlar
        cmd_trim = [
            "ffmpeg",
            "-ss", "00:00:00.5",
            "-i", temp_raw,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(target_duration),
            "-r", "30",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-avoid_negative_ts", "make_zero",
            cached_video,
            "-y"
        ]
        safe_run_subprocess(cmd_trim, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)

        if os.path.exists(cached_video) and os.path.getsize(cached_video) > 50000:
            print(f"✅ [UnboxingManager] Kutu açılış klibi başarıyla hazırlandı ve arşivlendi: {cached_video}")
            cache = load_cache()
            cache[core_query] = {
                "video_path": cached_video,
                "video_id": chosen_id,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_cache(cache)
            return cached_video, smart_hook
        else:
            return None

    except Exception as e:
        print(f"⚠️ [UnboxingManager] Kutu açılış motoru istisnası: {e}. Meme formatına dönülüyor.")
        return None
