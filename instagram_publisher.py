import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "").strip()

def check_instagram_credentials() -> dict:
    """Instagram Graph API erişim anahtarı ve kullanıcı kimliğini test eder."""
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        return {
            "configured": False,
            "error": "INSTAGRAM_ACCESS_TOKEN veya INSTAGRAM_USER_ID ayarlanmamış (.env dosyasına ekleyin)."
        }

    url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}"
    params = {
        "fields": "id,username,name",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if "error" in data:
            return {"configured": False, "error": data["error"].get("message", "Bilinmeyen API hatası")}
        return {"configured": True, "user": data}
    except Exception as e:
        return {"configured": False, "error": str(e)}

def publish_reel_to_instagram(video_public_url: str, caption: str, share_to_feed: bool = True) -> dict:
    """
    Instagram Graph API üzerinden video URL'sini Reels olarak otomatik paylaşır.
    Not: Meta Graph API, doğrudan yüklenecek videonun herkese açık bir HTTP/HTTPS URL'sinde olmasını şart koşar.
    """
    cred = check_instagram_credentials()
    if not cred["configured"]:
        print(f"[Instagram Publisher] ⚠️ {cred['error']}")
        return {"success": False, "error": cred["error"]}

    print(f"[Instagram Publisher] 🚀 Instagram Reels yayınlama başlatıldı: @{cred['user'].get('username')}...")

    # 1. Medya Konteyneri Oluştur (Create Container)
    create_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_public_url,
        "caption": caption,
        "share_to_feed": str(share_to_feed).lower(),
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    try:
        res = requests.post(create_url, data=payload, timeout=20)
        c_data = res.json()
        if "id" not in c_data:
            err_msg = c_data.get("error", {}).get("message", str(c_data))
            print(f"[Instagram Publisher] ❌ Konteyner oluşturulamadı: {err_msg}")
            return {"success": False, "error": err_msg}

        creation_id = c_data["id"]
        print(f"[Instagram Publisher] 📦 Konteyner oluşturuldu (ID: {creation_id}). Meta sunucularında işlenmesi bekleniyor...")

        # 2. İşlenme Durumunu Bekle (Polling status)
        status_url = f"https://graph.facebook.com/v20.0/{creation_id}"
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(5)
            s_res = requests.get(status_url, params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN}, timeout=10)
            s_data = s_res.json()
            code = s_data.get("status_code")
            print(f"[Instagram Publisher] Durum ({attempt+1}/{max_attempts}): {code}")

            if code == "FINISHED":
                break
            elif code == "ERROR":
                return {"success": False, "error": "Meta video işleme hatası verdi"}
        else:
            return {"success": False, "error": "Zaman aşımı (Video işlenemedi)"}

        # 3. Yayınla (Publish Container)
        pub_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media_publish"
        pub_res = requests.post(pub_url, data={"creation_id": creation_id, "access_token": INSTAGRAM_ACCESS_TOKEN}, timeout=20)
        pub_data = pub_res.json()

        if "id" in pub_data:
            print(f"🎉 [Instagram Publisher] Reels başarıyla yayınlandı! (Medya ID: {pub_data['id']})")
            return {"success": True, "media_id": pub_data["id"]}
        else:
            return {"success": False, "error": str(pub_data)}

    except Exception as e:
        print(f"[Instagram Publisher] İstek hatası: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    status = check_instagram_credentials()
    print("--- INSTAGRAM GRAPH API BAĞLANTI DURUMU ---")
    print(status)
