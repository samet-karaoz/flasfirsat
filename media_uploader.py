import os
import requests

def upload_video_to_public_url(video_path: str, timeout: int = 60) -> str:
    """
    Yerel MP4 videosunu Meta (Instagram) sunucularının doğrudan indirip işleyebileceği
    hızlı ve güvenli bir genel HTTPS bağlantısına yükler.
    
    Yöntem:
    1. Catbox / Litterbox CDN üzerinden doğrudan dosya yükleme (200MB'a kadar destekler).
    2. Meta Graph API bu doğrudan MP4 linkini anında çekebilir.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video bulunamadı: {video_path}")

    print(f"[Media Uploader] 📤 Video genel bağlantıya yükleniyor: {os.path.basename(video_path)}...")

    try:
        with open(video_path, "rb") as vf:
            res = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": vf},
                timeout=timeout
            )
        if res.status_code == 200 and res.text.startswith("http"):
            url = res.text.strip()
            print(f"[Media Uploader] 🔗 Genel video linki hazır: {url}")
            return url
        else:
            raise RuntimeError(f"Yükleme servisi hata döndü ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"[Media Uploader] ❌ Video yükleme hatası: {e}")
        raise
