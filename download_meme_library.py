import os
import subprocess
import glob

MEMES_DIR = os.path.join(os.path.dirname(__file__), "assets", "memes")
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(MEMES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

TARGET_MEMES = [
    {
        "name": "bateman_walk",
        "query": "patrick bateman walking headphones meme template",
        "max_duration": 12
    },
    {
        "name": "homelander_stare",
        "query": "homelander smile fading meme template",
        "max_duration": 10
    },
    {
        "name": "vince_mcmahon",
        "query": "vince mcmahon smelling money meme template",
        "max_duration": 10
    },
    {
        "name": "walter_white",
        "query": "walter white falling to the ground meme template",
        "max_duration": 10
    },
    {
        "name": "the_rock",
        "query": "the rock eyebrow raise meme template",
        "max_duration": 8
    },
    {
        "name": "shocked_cat",
        "query": "shocked cat meme template green screen",
        "max_duration": 10
    },
    {
        "name": "cillian_murphy",
        "query": "cillian murphy stare meme template",
        "max_duration": 10
    },
    {
        "name": "bale_nod",
        "query": "christian bale nod american psycho meme template",
        "max_duration": 8
    }
]

def download_and_format_meme(name: str, query: str, max_duration: int = 10):
    dest_path = os.path.join(MEMES_DIR, f"{name}.mp4")
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f"[{name}] Zaten mevcut, atlanıyor.")
        return True

    print(f"\n[{name}] İndiriliyor: '{query}'...")
    raw_pattern = os.path.join(TEMP_DIR, f"raw_{name}.%(ext)s")
    
    # 1. yt-dlp ile en iyi mp4 indir
    dl_cmd = [
        "yt-dlp", "--force-ipv4", "--no-playlist",
        "-f", "mp4/best[ext=mp4]/best",
        f"ytsearch1:{query}",
        "-o", raw_pattern
    ]
    res = subprocess.run(dl_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[{name}] İndirme hatası: {res.stderr[:200]}")
        return False

    # İndirilen dosyayı bul
    matched = glob.glob(os.path.join(TEMP_DIR, f"raw_{name}.*"))
    if not matched:
        print(f"[{name}] Dosya bulunamadı!")
        return False
    
    raw_file = matched[0]
    print(f"[{name}] İndirildi: {raw_file}. 1080x960 formatına dönüştürülüyor...")

    # 2. ffmpeg ile 1080x960 kırp/ölçekle ve max süreye kes
    convert_cmd = [
        "ffmpeg", "-y", "-i", raw_file,
        "-t", str(max_duration),
        "-vf", "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-an",
        dest_path
    ]
    c_res = subprocess.run(convert_cmd, capture_output=True, text=True)
    if c_res.returncode == 0 and os.path.exists(dest_path):
        print(f"[{name}] Başarıyla hazırlandı: {dest_path} ({os.path.getsize(dest_path)} bytes)")
        try:
            os.remove(raw_file)
        except:
            pass
        return True
    else:
        print(f"[{name}] FFmpeg dönüştürme hatası: {c_res.stderr[-200:]}")
        return False

if __name__ == "__main__":
    for item in TARGET_MEMES:
        download_and_format_meme(item["name"], item["query"], item["max_duration"])
    
    memes = os.listdir(MEMES_DIR)
    print("\n--- MEVCUT MEME KÜTÜPHANESİ ---")
    for m in memes:
        p = os.path.join(MEMES_DIR, m)
        print(f"- {m} ({os.path.getsize(p)//1024} KB)")
