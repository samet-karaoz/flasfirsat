import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from config import safe_run_subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSION_FILE = os.path.join(DATA_DIR, "instagram_session.json")

# instagrapi Giriş Bilgileri (.env)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "").strip()
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "").strip()

# Meta Graph API Bilgileri (Alternatif)
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "").strip()

def check_instagram_credentials() -> dict:
    """Instagram oturum veya API kimlik durumunu kontrol eder."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. instagrapi Bilgileri Kontrolü (Öncelikli)
    if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
        has_session = os.path.exists(SESSION_FILE)
        return {
            "configured": True,
            "mode": "instagrapi",
            "username": INSTAGRAM_USERNAME,
            "session_saved": has_session,
            "message": f"instagrapi hazır (Kullanıcı: @{INSTAGRAM_USERNAME})"
        }

    # 2. Meta Graph API Bilgileri Kontrolü
    if INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID:
        return {
            "configured": True,
            "mode": "graph_api",
            "message": "Meta Graph API hazır"
        }

    return {
        "configured": False,
        "mode": "none",
        "error": "Instagram bilgileri eksik. Lütfen .env dosyasına INSTAGRAM_USERNAME ve INSTAGRAM_PASSWORD ekleyin."
    }

_CACHED_INSTAGRAPI_CLIENT = None
_LAST_SESSION_CHECK_TIME = 0

def get_instagrapi_client(force_refresh: bool = False):
    """Oturum açılmış ve yapılandırılmış instagrapi Client nesnesi döner. Bellekte önbelleğe alır."""
    global _CACHED_INSTAGRAPI_CLIENT, _LAST_SESSION_CHECK_TIME
    from instagrapi import Client
    from instagrapi.exceptions import (
        BadPassword,
        TwoFactorRequired,
        ChallengeRequired,
        FeedbackRequired
    )

    now = time.time()
    if not force_refresh and _CACHED_INSTAGRAPI_CLIENT is not None:
        # Son 10 dakika içinde oturum başarıyla doğrulanmışsa doğrudan bellekteki nesneyi dön
        if (now - _LAST_SESSION_CHECK_TIME) < 600:
            return _CACHED_INSTAGRAPI_CLIENT
        # 10 dakikada bir oturum hala canlı mı diye hafif kontrol yap
        try:
            _CACHED_INSTAGRAPI_CLIENT.get_timeline_feed()
            _LAST_SESSION_CHECK_TIME = now
            return _CACHED_INSTAGRAPI_CLIENT
        except Exception:
            _CACHED_INSTAGRAPI_CLIENT = None

    os.makedirs(DATA_DIR, exist_ok=True)
    cl = Client()
    cl.delay_range = [2, 5]

    # Türkiye lokasyon ve cihaz ayarları
    cl.set_locale("tr_TR")
    cl.set_country(90)
    cl.set_timezone_offset(3 * 3600)

    # Kayıtlı oturum varsa yükle
    if os.path.exists(SESSION_FILE):
        try:
            print("[Instagram Publisher] 🔑 Kayıtlı oturum yükleniyor...")
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            # Oturum canlı mı test et
            cl.get_timeline_feed()
            print("✅ [Instagram Publisher] Kayıtlı oturum doğrulandı!")
            _CACHED_INSTAGRAPI_CLIENT = cl
            _LAST_SESSION_CHECK_TIME = now
            return cl
        except Exception as e:
            print(f"[Instagram Publisher] ⚠️ Kayıtlı oturum yenileniyor ({e})...")

    # Sıfırdan giriş yap
    print(f"[Instagram Publisher] 🚀 Instagram'a giriş yapılıyor: @{INSTAGRAM_USERNAME}...")
    try:
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("✅ [Instagram Publisher] Giriş başarılı! Oturum anahtarı kaydedildi.")
        _CACHED_INSTAGRAPI_CLIENT = cl
        _LAST_SESSION_CHECK_TIME = now
        return cl
    except TwoFactorRequired:
        raise RuntimeError("Instagram hesabınızda İki Adımlı Doğrulama (2FA) açık. Lütfen geçici olarak SMS kodunu girin.")
    except BadPassword:
        raise ValueError("Instagram şifresi hatalı! Lütfen .env dosyasını kontrol edin.")
    except ChallengeRequired:
        raise RuntimeError("Instagram güvenlik doğrulaması (Challenge/E-posta onayı) istedi. Lütfen Instagram uygulamasından giriş yapıp onaylayın.")
    except Exception as ex:
        raise RuntimeError(f"Instagram giriş hatası: {ex}")

def publish_reel_via_instagrapi(video_path: str, caption: str, first_comment: str = None) -> dict:
    """
    Yerel MP4 videosunu instagrapi üzerinden doğrudan Instagram Reels olarak yükler.
    Herhangi bir genel internet URL'si veya Facebook sayfası gerektirmez.
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

    try:
        cl = get_instagrapi_client()
        print(f"\n[Instagram Publisher] 📤 Reels yükleniyor: {os.path.basename(video_path)}...")
        print(f"✍️ Açıklama: {caption[:80]}...")

        # Otomatik FFmpeg thumbnail üretimi (Moviepy bağımlılığı olmadan %100 garantili)
        thumb_path = str(video_path) + ".jpg"
        if not os.path.exists(thumb_path):
            try:
                safe_run_subprocess([
                    "ffmpeg", "-y", "-ss", "00:00:01",
                    "-i", str(video_path), "-vframes", "1",
                    "-q:v", "2", thumb_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except Exception as ethumb:
                print(f"[Instagram Publisher] ⚠️ FFmpeg thumbnail oluşturulamadı: {ethumb}")

        upload_kwargs = {"caption": caption}
        if os.path.exists(thumb_path):
            upload_kwargs["thumbnail"] = Path(thumb_path)

        # Reels yükleme (clip_upload)
        media = cl.clip_upload(
            Path(video_path),
            **upload_kwargs
        )

        media_pk = getattr(media, "pk", "")
        media_code = getattr(media, "code", "")
        reel_url = f"https://www.instagram.com/reel/{media_code}/" if media_code else ""

        print(f"\n🎉 [Instagram Publisher] Reels başarıyla yayınlandı!")
        print(f"🔗 Instagram Reels Linki: {reel_url}")

        # 🚀 Algoritma & Keşfet Kancası: Otomatik İlk Yorum (Auto-First Comment)
        if media_pk:
            try:
                time.sleep(3)
                fc_text = first_comment or "📌 Fırsat ve indirim şu an aktif! Doğrudan satın alma linkini DM'den almak için yoruma 'Link gönder' veya 'Bana da at' yazabilirsiniz 👇 Sizce fiyat nasıl?"
                cl.media_comment(media_pk, fc_text)
                print("💬 [Instagram Publisher] ✅ Otomatik ilk kanca yorumu başarıyla paylaşıldı!")
            except Exception as efc:
                print(f"[Instagram Publisher] ⚠️ İlk yorum paylaşılamadı: {efc}")

        return {
            "success": True,
            "media_id": str(media_pk),
            "code": media_code,
            "url": reel_url
        }

    except Exception as e:
        print(f"[Instagram Publisher] ❌ Reels yükleme hatası: {e}")
        return {"success": False, "error": str(e)}

def post_reel_first_comment(media_id: str, comment_text: str) -> bool:
    """Yayınlanmış bir Reels'e ilk kanca yorumunu ekler."""
    try:
        cl = get_instagrapi_client()
        cl.media_comment(media_id, comment_text)
        return True
    except Exception as e:
        print(f"[Instagram Publisher] İlk yorum ekleme hatası: {e}")
        return False

def publish_reel_to_instagram(video_source: str, caption: str, share_to_feed: bool = True, first_comment: str = None) -> dict:
    """
    Instagram'da Reels paylaşımı için ana fonksiyon.
    .env'de INSTAGRAM_USERNAME ve INSTAGRAM_PASSWORD varsa instagrapi ile doğrudan yükler.
    """
    status = check_instagram_credentials()

    if status.get("mode") == "instagrapi":
        # Yerel dosya yolu veya web/Telegram indirme URL'si
        local_path = video_source
        is_temp_file = False
        if video_source.startswith("http://") or video_source.startswith("https://"):
            import requests
            temp_dl = os.path.join(DATA_DIR, f"temp_reel_{int(time.time())}.mp4")
            try:
                print(f"[Instagram Publisher] 📥 Video uzak sunucudan indiriliyor: {video_source[:60]}...")
                r = requests.get(video_source, stream=True, timeout=60)
                if r.status_code == 200:
                    with open(temp_dl, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            f.write(chunk)
                    local_path = temp_dl
                    is_temp_file = True
                else:
                    return {"success": False, "error": f"Video indirilemedi (HTTP {r.status_code}): {video_source}"}
            except Exception as e:
                return {"success": False, "error": f"Video indirme hatası: {e}"}

        if os.path.exists(local_path):
            try:
                return publish_reel_via_instagrapi(local_path, caption, first_comment=first_comment)
            finally:
                if is_temp_file and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass
        else:
            return {"success": False, "error": f"Yerel video dosyası bulunamadı: {video_source}"}

    elif status.get("mode") == "graph_api":
        # Meta Graph API fallback
        from media_uploader import upload_video_to_public_url
        import requests
        video_url = video_source
        if not video_source.startswith("http") and os.path.exists(video_source):
            video_url = upload_video_to_public_url(video_source)

        create_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
        res = requests.post(create_url, data=payload, timeout=20).json()
        if "id" not in res:
            return {"success": False, "error": str(res)}
        c_id = res["id"]
        time.sleep(15)
        pub_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media_publish"
        p_res = requests.post(pub_url, data={"creation_id": c_id, "access_token": INSTAGRAM_ACCESS_TOKEN}).json()
        return {"success": "id" in p_res, "media_id": p_res.get("id")}

def publish_story_with_link(image_path: str, link_url: str, caption: str = "") -> dict:
    """
    1080x1920 dikey görseli Instagram Hikayelerine (Story) doğrudan tıklanabilir Link Çıkartması ile yükler.
    """
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Story görseli bulunamadı: {image_path}"}

    status = check_instagram_credentials()
    if status.get("mode") != "instagrapi":
        return {"success": False, "error": "Story yüklemesi için instagrapi oturumu gereklidir."}

    try:
        from instagrapi.types import StoryLink
        cl = get_instagrapi_client()
        story_link = StoryLink(webUri=link_url)
        print(f"\n[Instagram Story] 📸 Hikaye yükleniyor: {os.path.basename(image_path)}...")
        print(f"🔗 Tıklanabilir Link: {link_url}")

        media = cl.photo_upload_to_story(
            Path(image_path),
            caption=caption,
            links=[story_link]
        )
        media_pk = getattr(media, "pk", "")
        print(f"🎉 [Instagram Story] Hikaye başarıyla yayınlandı! (ID: {media_pk})")
        return {"success": True, "media_id": str(media_pk)}

    except Exception as e:
        print(f"[Instagram Story] ❌ Hikaye yükleme hatası: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("--- INSTAGRAM PUBLISHER DURUMU ---")
    st = check_instagram_credentials()
    print(json.dumps(st, ensure_ascii=False, indent=2))
