import os
import time
import json
from dotenv import load_dotenv

load_dotenv()

# Google / YouTube API Imports
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOKEN_PATH = os.path.join(DATA_DIR, "youtube_token.json")
CLIENT_SECRETS_PATH = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", os.path.join(BASE_DIR, "client_secrets.json"))
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip().lower()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def check_youtube_credentials() -> dict:
    """YouTube API kimlik ve yetkilendirme durumunu kontrol eder."""
    if not GOOGLE_API_AVAILABLE:
        return {
            "configured": False,
            "error": "Google API kütüphaneleri eksik. 'pip install google-api-python-client google-auth-oauthlib' çalıştırın."
        }

    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Mevcut Token Kontrolü
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if creds and creds.valid:
                return {"configured": True, "token_ready": True, "message": "YouTube oturumu hazır."}
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    return {"configured": True, "token_ready": True, "message": "YouTube oturumu yenilendi."}
                except Exception as ref_err:
                    pass
        except Exception:
            pass

    # 2. client_secrets.json Kontrolü
    if not os.path.exists(CLIENT_SECRETS_PATH):
        return {
            "configured": False,
            "token_ready": False,
            "error": (
                f"YouTube OAuth dosya bulunamadı: '{CLIENT_SECRETS_PATH}'.\n"
                "Google Cloud Console'dan Masaüstü Uygulaması (Desktop App) OAuth 2.0 istemcisi oluşturup "
                "'client_secrets.json' adıyla proje klasörüne kaydedin. Rehber: docs/youtube_setup.md"
            )
        }

    return {
        "configured": True,
        "token_ready": False,
        "message": "client_secrets.json mevcut ancak ilk oturum açma (OAuth onayı) bekleniyor."
    }

def get_authenticated_service():
    """OAuth 2.0 ile YouTube servisine bağlanır ve yetkilendirilmiş istemci döner."""
    os.makedirs(DATA_DIR, exist_ok=True)
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(CLIENT_SECRETS_PATH):
                raise FileNotFoundError(
                    f"client_secrets.json bulunamadı. Lütfen Google Cloud Console'dan indirip {CLIENT_SECRETS_PATH} konumuna koyun."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            # Tarayıcıda bir defaya mahsus giriş sayfası açar
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

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
    - Sınırsız / kesintisiz resumable upload (parçalı yükleme).
    - Resmi Google YouTube Data API v3 uyumluluğu.
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

    cred_info = check_youtube_credentials()
    if not cred_info["configured"]:
        print(f"[YouTube Publisher] ⚠️ {cred_info['error']}")
        return {"success": False, "error": cred_info["error"]}

    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"[YouTube Publisher] ❌ Yetkilendirme hatası: {e}")
        return {"success": False, "error": str(e)}

    # Başlığı Shorts standartlarına uyarla (Maks 100 karakter, #Shorts ekle)
    clean_title = title.strip()
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        clean_title = f"{clean_title[:88]} #Shorts"
    else:
        clean_title = clean_title[:100]

    # Açıklama metnini düzenle (#reklam ve #Shorts zorunlu)
    clean_desc = description.strip()
    if "#Shorts" not in clean_desc:
        clean_desc = f"{clean_desc}\n\n#Shorts #indirim #fırsat #reklam #işbirliği"

    default_tags = ["shorts", "indirim", "fırsat", "kampanya", "alışveriş", "sıcakfırsat", "teknoloji"]
    if tags:
        default_tags = list(set(default_tags + tags))

    privacy = privacy_status or YOUTUBE_PRIVACY_STATUS or "public"

    body = {
        "snippet": {
            "title": clean_title,
            "description": clean_desc,
            "tags": default_tags[:15],
            "categoryId": "28"  # 28: Science & Technology (veya 22: People & Blogs)
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    print(f"\n[YouTube Publisher] 🚀 YouTube Shorts yüklemesi başlatılıyor...")
    print(f"📌 Başlık:  {clean_title}")
    print(f"🔒 Gizlilik: {privacy.upper()}")

    try:
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 2  # 2MB parçalar halinde
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[YouTube Publisher] ⏳ Yükleniyor: %{int(status.progress() * 100)}")

        video_id = response.get("id")
        shorts_url = f"https://www.youtube.com/shorts/{video_id}"
        print(f"🎉 [YouTube Publisher] Video başarıyla yüklendi!")
        print(f"🔗 Shorts Linki: {shorts_url}")

        return {
            "success": True,
            "video_id": video_id,
            "url": shorts_url,
            "privacy": privacy
        }

    except HttpError as he:
        err_msg = f"YouTube HTTP Hatası ({he.resp.status}): {he.content.decode('utf-8', errors='ignore')}"
        print(f"[YouTube Publisher] ❌ {err_msg}")
        return {"success": False, "error": err_msg}
    except Exception as ex:
        print(f"[YouTube Publisher] ❌ Beklenmeyen hata: {ex}")
        return {"success": False, "error": str(ex)}

if __name__ == "__main__":
    print("--- YOUTUBE SHORTS PUBLISHER DURUMU ---")
    st = check_youtube_credentials()
    print(json.dumps(st, ensure_ascii=False, indent=2))
