import os
import sys
import ssl
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Python 3.14 Windows OpenSSL Session ID hatasını önleme
try:
    orig_create_context = ssl.create_default_context
    def patched_create_default_context(*args, **kwargs):
        ctx = orig_create_context(*args, **kwargs)
        if hasattr(ssl, "OP_NO_TICKET"):
            ctx.options |= ssl.OP_NO_TICKET
        return ctx
    ssl.create_default_context = patched_create_default_context
except Exception:
    pass

from config import safe_run_subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "data", "youtube_token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
PORT = 8088
REDIRECT_URI = f"http://localhost:{PORT}/"

auth_code_holder = {}

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Konsol gürültüsünü engelle

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if "code" in qs:
            auth_code_holder["code"] = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>YouTube Bağlantısı Başarılı</title></head>
            <body style="font-family: Arial, sans-serif; background: #0f172a; color: white; text-align: center; padding-top: 80px;">
                <div style="background: #1e293b; max-width: 500px; margin: 0 auto; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                    <div style="font-size: 64px;">🎉</div>
                    <h1 style="color: #4ade80; margin-top: 20px;">Tebrikler!</h1>
                    <p style="font-size: 18px; color: #cbd5e1;">YouTube hesabınız başarıyla bağlandı.</p>
                    <p style="font-size: 14px; color: #94a3b8; margin-top: 30px;">Bu sekmeyi artık kapatabilirsiniz.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            err = qs.get("error", ["Bilinmeyen hata"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h3>Giriş Reddedildi veya İptal Edildi: {err}</h3>".encode("utf-8"))

def authenticate():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
        cs_data = json.load(f)["installed"]

    client_id = cs_data["client_id"]
    client_secret = cs_data["client_secret"]

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline"
    )

    print("=" * 60, flush=True)
    print("🚀 YOUTUBE OTURUM AÇMA BAĞLANTISI HAZIR:", flush=True)
    print(auth_url, flush=True)
    print("=" * 60, flush=True)

    # Tarayıcıyı aç
    try:
        import webbrowser
        webbrowser.open(auth_url)
    except Exception:
        pass

    server = HTTPServer(("localhost", PORT), OAuthCallbackHandler)
    print(f"Port {PORT} üzerinde Google yanıtı bekleniyor...", flush=True)

    while "code" not in auth_code_holder:
        server.handle_request()

    code = auth_code_holder["code"]
    print("✅ Yetkilendirme kodu alındı! Token ile takas ediliyor...", flush=True)

    # Doğrudan requests.post ile token al (OpenSSL bug'ına takılmaz)
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": flow.code_verifier
    }

    # Windows Python 3.14 SSL bug'ını önlemek için curl.exe --ssl-no-revoke ile doğrudan al
    post_data = urllib.parse.urlencode(token_payload)
    cmd = [
        "curl.exe", "-4", "--ssl-no-revoke", "-s", "-X", "POST",
        token_url,
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-d", post_data
    ]
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        token_json = json.loads(res.stdout)
    except Exception as parse_err:
        print(f"❌ Token yanıtı okunamadı ({parse_err}): {res.stdout}", flush=True)
        return False

    if "access_token" not in token_json:
        print(f"❌ Token alınamadı: {token_json}", flush=True)
        return False

    creds = Credentials(
        token=token_json.get("access_token"),
        refresh_token=token_json.get("refresh_token"),
        token_uri=token_url,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print("\n" + "=" * 60, flush=True)
    print("🎉 YOUTUBE OTURUMU BAŞARIYLA BAĞLANDI VE KAYDEDİLDİ!", flush=True)
    print(f"📁 Dosya: {TOKEN_FILE}", flush=True)
    print("=" * 60 + "\n", flush=True)
    return True

if __name__ == "__main__":
    authenticate()
