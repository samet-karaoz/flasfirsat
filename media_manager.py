import os
import json
import subprocess
from config import PEXELS_API_KEY, TEMP_DIR, safe_run_subprocess

def get_cinematic_clips(query: str = "sunset calm sea silhouette", count: int = 3) -> list:
    """
    Pexels API'den verilen konuya göre dikey (portrait), yüksek çözünürlüklü
    sinematik videoları bulup temp klasörüne indirir.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    clean_query = query.replace(" ", "+")
    url = f"https://api.pexels.com/videos/search?query={clean_query}&orientation=portrait&per_page=6"
    
    cmd_search = ["curl.exe", "--ssl-no-revoke", "-s", "-H", f"Authorization: {PEXELS_API_KEY}", url]
    res = safe_run_subprocess(cmd_search, capture_output=True, text=True, encoding="utf-8")
    
    downloaded_files = []
    try:
        data = json.loads(res.stdout)
        videos = data.get("videos", [])
        print(f"[Media] Pexels'te '{query}' aramasıyla {len(videos)} video bulundu.")
        
        for idx, v in enumerate(videos):
            if len(downloaded_files) >= count:
                break
            # Dikey dosyaları filtrele
            files = [f for f in v.get("video_files", []) if f.get("width", 0) <= f.get("height", 0)]
            if not files:
                files = v.get("video_files", [])
            # En az 720p veya en yüksek çözünürlüğü seç
            best = sorted(files, key=lambda x: x.get("width", 0), reverse=True)[0]
            link = best["link"]
            out_path = os.path.join(TEMP_DIR, f"pex_clip_{len(downloaded_files)}.mp4")
            
            print(f"[Media] Video {len(downloaded_files)+1}/{count} indiriliyor ({best.get('width')}x{best.get('height')})...")
            cmd_dl = ["curl.exe", "--ssl-no-revoke", "-L", "-s", "-A", "Mozilla/5.0", link, "-o", out_path]
            safe_run_subprocess(cmd_dl)
            
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100000:
                downloaded_files.append(out_path)
    except Exception as e:
        print("[Media] Pexels indirme hatası:", e)

    # Eğer eksik kalırsa hazır indirdiğimiz real_broll kliplerini kullan
    if len(downloaded_files) < count:
        for i in range(count):
            bk = os.path.join(TEMP_DIR, f"real_broll_{i}.mp4")
            if os.path.exists(bk) and bk not in downloaded_files:
                downloaded_files.append(bk)
                if len(downloaded_files) >= count:
                    break

    return downloaded_files

if __name__ == "__main__":
    c = get_cinematic_clips("sunset sea", count=2)
    print("Downloaded clips:", c)
