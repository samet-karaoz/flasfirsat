import os
import sys
import time
import json
import subprocess
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOKEN_PATH = os.path.join(DATA_DIR, "youtube_token.json")
CLIENT_SECRETS_PATH = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", os.path.join(BASE_DIR, "client_secrets.json"))
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip().lower()

def check_youtube_credentials() -> dict:
    """YouTube API kimlik ve yetkilendirme durumunu kontrol eder."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(CLIENT_SECRETS_PATH):
        return {
            "configured": False,
            "token_ready": False,
            "error": "client_secrets.json bulunamadı. Lütfen Google Cloud'dan indirip proje klasörüne koyun."
        }

    if not os.path.exists(TOKEN_PATH):
        return {
            "configured": True,
            "token_ready": False,
            "message": "client_secrets.json mevcut ancak oturum açma (youtube_auth.py) bekleniyor."
        }

    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            if t_data.get("refresh_token") or t_data.get("token"):
                return {"configured": True, "token_ready": True, "message": "YouTube oturumu hazır."}
    except Exception:
        pass

    return {"configured": True, "token_ready": False, "message": "Token geçersiz, yeniden yetkilendirme gerekli."}

def get_valid_access_token() -> str:
    """Aktif access_token döner; süresi dolduysa curl ile yeniler."""
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError("data/youtube_token.json bulunamadı. Lütfen önce 'python youtube_auth.py' çalıştırın.")

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        t_data = json.load(f)

    refresh_token = t_data.get("refresh_token")
    client_id = t_data.get("client_id")
    client_secret = t_data.get("client_secret")

    # Access token'ı curl ile doğrudan yenile (OpenSSL bug'ına takılmaz)
    refresh_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    cmd = [
        "curl.exe", "-4", "--ssl-no-revoke", "-s", "-X", "POST",
        "https://oauth2.googleapis.com/token",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-d", urllib.parse.urlencode(refresh_payload)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        ref_json = json.loads(res.stdout)
        if "access_token" in ref_json:
            t_data["token"] = ref_json["access_token"]
            with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump(t_data, f, ensure_ascii=False, indent=2)
            return ref_json["access_token"]
    except Exception as e:
        print(f"[YouTube Publisher] Token yenileme uyarısı: {e}")

    # Mevcut token'ı döndür
    return t_data.get("token", "")

def sanitize_youtube_text(text: str) -> str:
    """YouTube Data API başlık ve açıklamalarda < ve > karakterlerini kabul etmez (HTML/XSS koruması)."""
    if not text:
        return ""
    t = text.replace("->", "➔").replace("<-", "⬅").replace("-->", "➔").replace("<--", "⬅")
    t = t.replace("<", "").replace(">", "")
    return t.strip()

def publish_shorts_to_youtube(
    video_path: str,
    title: str,
    description: str,
    privacy_status: str = None,
    tags: list = None
) -> dict:
    """
    Hazırlanan MP4 dikey videosunu doğrudan YouTube Shorts olarak kanala yükler.
    
    Özellikler:
    - 9:16 format ve #Shorts etiketiyle otomatik YouTube Shorts sınıflandırması.
    - Windows Python 3.14 SSL bug'ından etkilenmeyen yüksek hızlı curl.exe Resumable Upload mimarisi.
    - 1080x1920 dikey video desteği.
    """
    if not video_path:
        return {"success": False, "error": "Video dosya yolu belirtilmedi."}

    if not os.path.exists(video_path):
        if video_path.startswith("http://") or video_path.startswith("https://"):
            temp_vid = os.path.join(DATA_DIR, "temp_yt_upload.mp4")
            cmd = ["curl.exe", "-4", "--ssl-no-revoke", "-s", "-L", video_path, "-o", temp_vid]
            subprocess.run(cmd)
            if os.path.exists(temp_vid) and os.path.getsize(temp_vid) > 1000:
                video_path = temp_vid
            else:
                return {"success": False, "error": f"Uzak video indirilemedi: {video_path}"}
        else:
            return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

    cred_info = check_youtube_credentials()
    if not cred_info.get("token_ready"):
        print(f"[YouTube Publisher] ⚠️ {cred_info.get('message', 'Yetkilendirme eksik')}")
        return {"success": False, "error": cred_info.get("message", "Yetkilendirme eksik")}

    try:
        access_token = get_valid_access_token()
    except Exception as e:
        return {"success": False, "error": f"Yetkilendirme anahtarı alınamadı: {e}"}

    # Başlığı Shorts standartlarına uyarla (Maks 100 karakter, #Shorts ekle, < > temizle)
    clean_title = sanitize_youtube_text(title)
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        clean_title = f"{clean_title[:88]} #Shorts"
    else:
        clean_title = clean_title[:100]

    # Açıklama metnini düzenle (#reklam, web vitrin linki, #Shorts zorunlu, < > temizle)
    clean_desc = sanitize_youtube_text(description)
    from config import SITE_URL
    web_link = f"{SITE_URL}?utm_source=youtube&utm_medium=shorts"
    if SITE_URL not in clean_desc:
        clean_desc = f"{clean_desc}\n\n⚡ Tüm Dip Fiyatlar & İndirim Radarı:\n🔗 {web_link}"
    if "#Shorts" not in clean_desc and "#shorts" not in clean_desc:
        clean_desc = f"{clean_desc}\n\n#Shorts #indirim #fırsat #reklam #işbirliği"

    default_tags = ["shorts", "indirim", "fırsat", "kampanya", "alışveriş", "sıcakfırsat", "teknoloji"]
    if tags:
        sanitized_tags = [sanitize_youtube_text(t) for t in tags if t]
        default_tags = list(set(default_tags + sanitized_tags))

    privacy = privacy_status or YOUTUBE_PRIVACY_STATUS or "public"

    metadata = {
        "snippet": {
            "title": clean_title,
            "description": clean_desc,
            "tags": default_tags[:15],
            "categoryId": "28"  # 28: Science & Technology
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    file_size = os.path.getsize(video_path)
    print(f"\n[YouTube Publisher] 🚀 YouTube Shorts yüklemesi başlatılıyor...")
    print(f"📌 Başlık:   {clean_title}")
    print(f"🔒 Gizlilik:  {privacy.upper()}")
    print(f"📦 Dosya:     {os.path.basename(video_path)} ({int(file_size / (1024*1024))} MB)")

    # 1. Resumable Upload Başlat (Start session - Güvenli UTF-8 JSON dosyası üzerinden)
    meta_temp = os.path.join(DATA_DIR, "yt_meta_temp.json")
    with open(meta_temp, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    init_cmd = [
        "curl.exe", "-4", "--ssl-no-revoke", "-s", "-i", "-X", "POST",
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json; charset=UTF-8",
        "-H", "X-Upload-Content-Type: video/mp4",
        "-H", f"X-Upload-Content-Length: {file_size}",
        "--data-binary", f"@{meta_temp}"
    ]

    init_res = subprocess.run(init_cmd, capture_output=True, text=True, encoding="utf-8")
    headers = init_res.stdout

    upload_url = None
    for line in headers.splitlines():
        if line.lower().startswith("location:"):
            upload_url = line.split(":", 1)[1].strip()
            break

    if not upload_url:
        print(f"[YouTube Publisher] ❌ Resumable oturum açılamadı:\n{headers}")
        err_detail = "Bilinmeyen hata"
        try:
            json_start = headers.find("{")
            if json_start != -1:
                err_obj = json.loads(headers[json_start:])
                err_detail = err_obj.get("error", {}).get("message", headers[:200])
            else:
                err_detail = headers[:200]
        except Exception:
            err_detail = headers[:200]
        return {"success": False, "error": f"Oturum açılamadı: {err_detail}"}

    # 2. Video Dosyasını Yükle (PUT binary video)
    print("[YouTube Publisher] ⏳ Video Google sunucularına aktarılıyor...")
    put_cmd = [
        "curl.exe", "-4", "--ssl-no-revoke", "-s", "-X", "PUT",
        upload_url,
        "-H", "Content-Type: video/mp4",
        "-H", f"Content-Length: {file_size}",
        "--upload-file", video_path
    ]

    put_res = subprocess.run(put_cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        resp_json = json.loads(put_res.stdout)
        video_id = resp_json.get("id")
        if video_id:
            shorts_url = f"https://www.youtube.com/shorts/{video_id}"
            print(f"🎉 [YouTube Publisher] Video başarıyla yüklendi!")
            print(f"🔗 Shorts Linki: {shorts_url}")
            return {
                "success": True,
                "video_id": video_id,
                "url": shorts_url,
                "privacy": privacy
            }
        else:
            print(f"[YouTube Publisher] ❌ Yükleme yanıt hatası: {put_res.stdout}")
            return {"success": False, "error": put_res.stdout}
    except Exception as e:
        print(f"[YouTube Publisher] ❌ Ayrıştırma hatası: {e} | Çıktı: {put_res.stdout}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("--- YOUTUBE SHORTS PUBLISHER DURUMU ---")
    st = check_youtube_credentials()
    print(json.dumps(st, ensure_ascii=False, indent=2))
