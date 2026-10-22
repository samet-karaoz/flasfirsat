import os
import re
import json
import subprocess
import imageio_ffmpeg
from config import BASE_DIR, ASSETS_DIR, TEMP_DIR

CACHE_FILE = os.path.join(BASE_DIR, "data", "brand_video_cache.json")
BRAND_VIDEOS_DIR = os.path.join(ASSETS_DIR, "brand_videos")
os.makedirs(BRAND_VIDEOS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

KNOWN_BRANDS = [
    "apple", "samsung", "sony", "asus", "rog", "tuf", "msi", "dell", "alienware", "lg", "lenovo", "hp", "victus",
    "acer", "nitro", "benq", "viewsonic", "aoc", "gigabyte", "logitech", "razer", "steelseries", "hyperx", "corsair",
    "jbl", "anker", "soundcore", "sennheiser", "marshall", "bose", "edifier", "nothing", "philips", "dyson",
    "stanley", "delonghi", "nespresso", "xiaomi", "roborock", "dreame", "bosch", "einhell", "lego", "braun",
    "oral-b", "spigen", "baseus", "ugreen", "belkin", "tp-link", "sandisk", "kingston", "crucial", "wd", "seagate",
    "nintendo", "playstation", "dualsense", "xbox", "casio", "garmin", "huawei", "honor", "north bayou",
    "karaca", "tefal", "arçelik", "arcelik", "beko", "vestel", "korkmaz", "fakir", "sinbo", "arzum", "cosori",
    "ninja", "ninjafoodi", "nescafe", "tassimo", "russell hobbs", "grundig", "electrolux", "kumtel", "braun"
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
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BrandVideoEngine] Önbellek yazma hatası: {e}")

def extract_brand_and_model(title: str):
    """Ürün başlığından ana marka ve aranabilir model kelimelerini çıkarır."""
    t_clean = re.sub(r'[^\w\s\-\.]', ' ', title)
    words = t_clean.split()
    
    found_brand = ""
    t_low = title.lower()
    for b in KNOWN_BRANDS:
        if re.search(r"\b" + re.escape(b) + r"\b", t_low):
            found_brand = b.capitalize()
            break
            
    if not found_brand and words:
        found_brand = words[0]
        
    junk_words = {
        "ve", "ile", "için", "orijinal", "garantili", "türkiye", "yeni", "özel", "fırsatı",
        "indirimli", "kampanyalı", "inox", "siyah", "beyaz", "gri", "kırmızı", "mavi",
        "dilim", "watt", "2000w", "litre", "kapasite", "mekanik", "kablosuz", "wireless",
        "bluetooth", "pro", "max", "mini", "plus"
    }
    
    model_words = []
    for w in words:
        wl = w.lower()
        if wl == found_brand.lower():
            continue
        if wl in junk_words:
            continue
        model_words.append(w)
        if len(model_words) >= 4:
            break
            
    model_str = " ".join(model_words)
    return found_brand, model_str

def search_official_brand_video(brand: str, model: str) -> dict:
    """
    YouTube üzerinde yt-dlp ile arama yaparak doğrudan markanın resmi kanalından
    veya doğrulanmış lansman/tanıtım videosunu bulur.
    """
    queries = [
        f"ytsearch3:{brand} {model} official product video",
        f"ytsearch3:{brand} {model} commercial trailer",
        f"ytsearch3:{brand} {model} tanıtım filmi"
    ]
    
    for q in queries:
        try:
            cmd = [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android",
                "--print", "%(id)s | %(channel)s | %(duration)s | %(title)s",
                q
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode != 0 or not res.stdout.strip():
                continue
                
            lines = res.stdout.strip().split("\n")
            for line in lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    vid_id = parts[0]
                    channel = parts[1]
                    try:
                        dur = float(parts[2])
                    except:
                        dur = 60.0
                    vid_title = parts[3]
                    
                    # Marka Doğrulama Kalkanı (Brand Verification Guard):
                    # 1. Kanal adında marka geçiyor mu? VEYA başlıkta marka + (official / commercial / tanıtım) var mı?
                    ch_low = channel.lower()
                    vt_low = vid_title.lower()
                    b_low = brand.lower()
                    
                    is_official_channel = (b_low in ch_low) or ("official" in ch_low) or ("türkiye" in ch_low and b_low in vt_low)
                    has_official_title = (b_low in vt_low) and any(w in vt_low for w in ["official", "tanıtım", "commercial", "trailer", "product video", "unboxed"])
                    
                    # 5 dakikadan uzun videoları (podcast vs) atla, B-roll için ideali 15s - 180s
                    if (is_official_channel or has_official_title) and dur <= 300:
                        return {
                            "video_id": vid_id,
                            "channel": channel,
                            "duration": dur,
                            "title": vid_title
                        }
        except Exception as e:
            print(f"[BrandVideoEngine] Arama sorgu hatası ({q}): {e}")
            
    return None

def download_and_cut_official_broll(video_id: str, output_path: str, duration: float = 8.0) -> bool:
    """
    Seçilen resmi videoyu indirip 8.0 saniyelik en şık B-Roll bölümünü keser.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    temp_full = os.path.join(TEMP_DIR, f"yt_raw_{video_id}.mp4")
    
    try:
        # İndirme: 1080p veya 720p tercih edilir
        cmd_dl = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "-o", temp_full,
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        res_dl = subprocess.run(cmd_dl, capture_output=True, text=True, timeout=60)
        if not os.path.exists(temp_full):
            print(f"[BrandVideoEngine] İndirme başarısız: {res_dl.stderr[:300]}")
            return False
            
        # Segment Başlangıç Belirleme:
        # Reklam videolarında ilk 3-5 saniye genellikle logo veya animasyondur.
        # Ürünün en dinamik göründüğü saniyeler genellikle 6. saniye ile 30. saniye arasıdır.
        start_sec = "00:00:06.000"
        
        cmd_cut = [
            ffmpeg, "-y",
            "-ss", start_sec,
            "-i", temp_full,
            "-t", str(duration),
            "-c:v", "libx264",
            "-crf", "18",
            "-an",
            output_path
        ]
        res_cut = subprocess.run(cmd_cut, capture_output=True, text=True, timeout=30)
        
        # Temizlik
        if os.path.exists(temp_full):
            try:
                os.remove(temp_full)
            except:
                pass
                
        return os.path.exists(output_path) and os.path.getsize(output_path) > 50000
    except Exception as e:
        print(f"[BrandVideoEngine] Video indirme/kesme hatası: {e}")
        return False

def generate_studio_broll(image_path: str, output_path: str, duration: float = 8.0) -> bool:
    """
    Resmi YouTube tanıtımı bulunamayan ürünler için yüksek çözünürlüklü ürün görselinden
    1080x1080 lüks stüdyo sinematik hareketli (Ken Burns zoom/pan) B-Roll oluşturur.
    """
    if not image_path or not os.path.exists(image_path):
        return False
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    flt = (
        "[0:v]split=2[bg_raw][fg_raw];"
        "[bg_raw]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=30:5,eq=brightness=-0.35[bg];"
        "[fg_raw]scale=840:840:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(1080-w)/2:(1080-h)/2,zoompan=z='min(zoom+0.0006,1.08)':d=200:s=1080x1080:fps=25[out]"
    )
    cmd = [
        ffmpeg, "-y",
        "-loop", "1",
        "-i", image_path,
        "-filter_complex", flt,
        "-map", "[out]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 10000
    except Exception as e:
        print(f"[BrandVideoEngine] Stüdyo B-Roll oluşturma hatası: {e}")
        return False

def get_deal_brand_video(deal: dict) -> str:
    """
    Ana fonksiyon: Verilen fırsat için resmi marka B-Roll videosunu döndürür.
    Öncelikle önbelleğe bakar; yoksa arar, indirir, keser ve önbelleğe kaydeder.
    Resmi video bulunamazsa None döner.
    """
    asin = deal.get("asin") or deal.get("product_id") or ""
    if not asin and deal.get("store_url"):
        m_asin = re.search(r'/dp/([A-Z0-9]{10})', deal["store_url"])
        if m_asin:
            asin = m_asin.group(1)
    title = deal.get("title", "")
    
    cache = load_cache()
    
    # 1. Önbellek kontrolü
    if asin and asin in cache:
        cached_file = cache[asin].get("file_path")
        if cached_file and os.path.exists(cached_file):
            print(f"[BrandVideoEngine] 🎯 Önbellekten resmi marka videosu alındı: {cached_file}")
            return cached_file
            
    # 2. Marka ve Model Tespiti
    brand, model = extract_brand_and_model(title)
    print(f"[BrandVideoEngine] 🔎 Resmi marka videosu aranıyor: Marka=[{brand}], Model=[{model}]")
    
    # Özel vaka: Mevcut Karaca Gastro Gourmet için hazır kurgulanmış B-Roll varsa doğrudan kullan
    if "gastro gourmet" in title.lower() and os.path.exists(os.path.join(TEMP_DIR, "karaca_broll_8s.mp4")):
        final_dest = os.path.join(BRAND_VIDEOS_DIR, "karaca_gastro_gourmet_8s.mp4")
        if not os.path.exists(final_dest):
            import shutil
            shutil.copy(os.path.join(TEMP_DIR, "karaca_broll_8s.mp4"), final_dest)
        if asin:
            cache[asin] = {"brand": brand, "model": model, "file_path": final_dest}
            save_cache(cache)
        return final_dest

    # 3. YouTube Resmi Arama
    res = search_official_brand_video(brand, model)
    if res:
        vid_id = res["video_id"]
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', f"{brand}_{model}")[:40]
        out_file = os.path.join(BRAND_VIDEOS_DIR, f"{safe_name}_{vid_id}.mp4")
        
        if os.path.exists(out_file) and os.path.getsize(out_file) > 50000:
            if asin:
                cache[asin] = {"brand": brand, "model": model, "file_path": out_file}
                save_cache(cache)
            return out_file
            
        print(f"[BrandVideoEngine] 📥 Resmi video indiriliyor: [{res['channel']}] {res['title']} (ID: {vid_id})")
        success = download_and_cut_official_broll(vid_id, out_file, duration=8.0)
        
        if success:
            print(f"[BrandVideoEngine] ✅ Resmi marka B-Roll videosu hazır: {out_file}")
            if asin:
                cache[asin] = {"brand": brand, "model": model, "file_path": out_file}
                save_cache(cache)
            return out_file
        else:
            print(f"[BrandVideoEngine] ⚠️ Video indirme/kesme başarısız oldu, stüdyo moduna geçiliyor.")
    else:
        print(f"[BrandVideoEngine] ℹ️ '{brand} {model}' için resmi YouTube videosu bulunamadı, stüdyo moduna geçiliyor.")

    # 4. Fallback: Resmi video bulunamazsa yüksek kaliteli stüdyo B-Roll oluştur
    img_path = deal.get("image_path")
    if img_path and os.path.exists(img_path):
        print(f"[BrandVideoEngine] 🎨 Yüksek çözünürlüklü ürün görselinden lüks stüdyo B-Roll üretiliyor...")
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', f"{brand}_{model}")[:40]
        studio_out = os.path.join(BRAND_VIDEOS_DIR, f"studio_{safe_name}.mp4")
        if generate_studio_broll(img_path, studio_out, duration=8.0):
            print(f"[BrandVideoEngine] ✨ Stüdyo B-Roll başarıyla hazırlandı: {studio_out}")
            if asin:
                cache[asin] = {"brand": brand, "model": model, "file_path": studio_out, "type": "studio"}
                save_cache(cache)
            return studio_out

    print(f"[BrandVideoEngine] ❌ Ürün görseli veya resmi B-Roll bulunamadı.")
    return None
