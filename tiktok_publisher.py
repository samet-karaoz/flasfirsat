import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

from config import BASE_DIR, DATA_DIR, safe_run_subprocess

BUFFER_API_URL = "https://api.buffer.com"

def get_buffer_token() -> str:
    """Buffer Access Token'ı ortam değişkenlerinden alır."""
    token = os.getenv("BUFFER_ACCESS_TOKEN") or os.getenv("BUFFER_API_KEY", "")
    return token.strip()

def check_tiktok_credentials() -> dict:
    """Buffer üzerinden TikTok bağlantısını ve API token'ını doğrular."""
    token = get_buffer_token()
    if not token:
        return {
            "configured": False,
            "connected": False,
            "error": "BUFFER_ACCESS_TOKEN bulunamadı. Lütfen .env dosyasına ekleyin."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Organizasyonu Al
    org_query = """
    query {
      account {
        id
        email
        organizations {
          id
          name
        }
      }
    }
    """
    try:
        r = requests.post(BUFFER_API_URL, json={"query": org_query}, headers=headers, timeout=10)
        if r.status_code != 200 or "errors" in r.json():
            return {
                "configured": True,
                "connected": False,
                "error": f"Buffer yetkilendirme hatası: {r.text}"
            }
        
        orgs = r.json().get("data", {}).get("account", {}).get("organizations", [])
        if not orgs:
            return {"configured": True, "connected": False, "error": "Buffer üzerinde organizasyon bulunamadı."}

        org_id = orgs[0]["id"]

        # 2. Kanalları Al
        channels_query = f"""
        query {{
          channels(input: {{ organizationId: "{org_id}" }}) {{
            id
            name
            service
          }}
        }}
        """
        r_ch = requests.post(BUFFER_API_URL, json={"query": channels_query}, headers=headers, timeout=10)
        channels = r_ch.json().get("data", {}).get("channels", [])
        
        tiktok_ch = next((c for c in channels if c.get("service") == "tiktok"), None)
        if not tiktok_ch:
            return {
                "configured": True,
                "connected": False,
                "message": "Buffer hesabında TikTok kanalı bağlı değil. Lütfen Buffer'a TikTok'u ekleyin."
            }

        return {
            "configured": True,
            "connected": True,
            "channel_id": tiktok_ch["id"],
            "channel_name": tiktok_ch["name"],
            "organization_id": org_id,
            "message": f"TikTok kanalı hazır: {tiktok_ch['name']}"
        }
    except Exception as e:
        return {"configured": True, "connected": False, "error": str(e)}

def ensure_video_hosted_publicly(video_path: str) -> str:
    """
    Yerel video dosyasını GitHub repomuza (assets/videos/) ekler,
    commit ve push yaparak Buffer'ın indirebileceği güvenli ve kalıcı
    bir genel URL oluşturur.
    """
    import shutil
    videos_dir = os.path.join(BASE_DIR, "assets", "videos")
    os.makedirs(videos_dir, exist_ok=True)

    base_name = os.path.basename(video_path)
    dst_path = os.path.join(videos_dir, base_name)
    if os.path.abspath(video_path) != os.path.abspath(dst_path):
        shutil.copy2(video_path, dst_path)

    # Git'e ekle ve pushla
    from web_showcase import push_to_github
    try:
        safe_run_subprocess(["git", "config", "user.name", "flasfirsat-bot[bot]"], check=False)
        safe_run_subprocess(["git", "config", "user.email", "bot@flasfirsat.com"], check=False)
        safe_run_subprocess(["git", "add", dst_path], check=False)
        safe_run_subprocess(["git", "commit", "-m", f"Add TikTok video asset: {base_name}"], check=False)
        push_to_github()
    except Exception as e:
        print(f"[TikTok Publisher] Git video push uyarısı: {e}")

    # GitHub Raw Doğrudan URL'si
    return f"https://raw.githubusercontent.com/samet-karaoz/flasfirsat/main/assets/videos/{base_name}"

def publish_video_to_tiktok(video_path: str, caption: str, mode: str = "shareNow") -> dict:
    """
    Verilen MP4 videosunu Buffer API üzerinden TikTok kanalına
    tam otomatik, güvenli ve resmi olarak herkese açık (Public) yükler.
    """
    cred = check_tiktok_credentials()
    if not cred.get("connected"):
        return {"success": False, "error": cred.get("error") or cred.get("message")}

    channel_id = cred["channel_id"]
    token = get_buffer_token()

    print(f"[TikTok Publisher] 🚀 TikTok yüklemesi hazırlanıyor: {cred['channel_name']}")
    public_video_url = ensure_video_hosted_publicly(video_path)
    print(f"[TikTok Publisher] 🌐 Video URL hazır: {public_video_url}")

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
          }
        }
        ... on LimitReachedError {
          message
        }
        ... on InvalidInputError {
          message
        }
        ... on UnexpectedError {
          message
        }
        ... on UnauthorizedError {
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "channelId": channel_id,
            "text": caption,
            "mode": mode,
            "schedulingType": "automatic",
            "needsApproval": False,
            "assets": [
                {
                    "video": {
                        "url": public_video_url
                    }
                }
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(BUFFER_API_URL, json={"query": mutation, "variables": variables}, headers=headers, timeout=20)
        res_json = r.json()
        create_res = res_json.get("data", {}).get("createPost", {})

        if "post" in create_res:
            p_data = create_res["post"]
            print(f"🎉 [TikTok Publisher] Video Buffer üzerinden TikTok'a başarıyla gönderildi! Post ID: {p_data.get('id')}")
            return {
                "success": True,
                "post_id": p_data.get("id"),
                "status": p_data.get("status"),
                "channel": cred["channel_name"]
            }
        else:
            err_msg = create_res.get("message") or str(res_json)
            print(f"❌ [TikTok Publisher] Gönderim hatası: {err_msg}")
            return {"success": False, "error": err_msg}

    except Exception as e:
        print(f"❌ [TikTok Publisher] İstek hatası: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    c = check_tiktok_credentials()
    print("Credentials Check:", c)
