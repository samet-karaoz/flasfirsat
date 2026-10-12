import os
import subprocess
import json
from config import BASE_DIR, get_curl_cmd
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@flasfirsat").strip()

def send_telegram_deal(video_path: str, caption_text: str, product_url: str = None, chat_id: str = None, bot_token: str = None) -> bool:
    """
    Üretilen MP4 videosunu, hazır açıklama metnini ve
    tıklanabilir doğrudan ürün linkini hem kullanıcının telefonuna hem de @flasfirsat kanalına gönderir.
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    if not token:
        print("\n[Telegram Notifier] ⚠️ TELEGRAM_BOT_TOKEN ayarlanmamış.")
        return False

    targets = []
    if cid:
        targets.append(cid)
    if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID not in targets:
        targets.append(TELEGRAM_CHANNEL_ID)

    if not targets:
        print("\n[Telegram Notifier] ⚠️ Hedef kanal veya Chat ID bulunamadı.")
        return False

    if not os.path.exists(video_path):
        print(f"[Telegram Notifier] ❌ Gönderilecek video dosyası bulunamadı: {video_path}")
        return False

    # Telegram sendVideo limiti caption için 1024 karakterdir.
    short_caption = caption_text[:1000] if len(caption_text) > 1000 else caption_text

    # Caption içine ve sonuna doğrudan satın alma linkini ekle
    if product_url:
        caption_with_url = f"{short_caption}\n\n🛒 Doğrudan Satın Al: {product_url}"
        if len(caption_with_url) <= 1024:
            short_caption = caption_with_url

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    overall_ok = True

    for target in targets:
        label = "Kanal (@flasfirsat)" if target == TELEGRAM_CHANNEL_ID else "Telefon (Özel)"
        print(f"[Telegram Notifier] 📱 Video gönderiliyor -> {label}...")
        cmd = get_curl_cmd([
            "--max-time", "120", "-s",
            "-F", f"chat_id={target}",
            "-F", f"video=@{video_path}",
            "-F", f"caption={short_caption}",
            "-F", "supports_streaming=true",
            url
        ])

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            data = json.loads(res.stdout)
            if data.get("ok"):
                print(f"✅ [TELEGRAM] {label} paylaşımı başarılı!")
            else:
                print(f"❌ [TELEGRAM HATA - {label}] {data.get('description', res.stdout)}")
                overall_ok = False
        except Exception as e:
            print(f"❌ [TELEGRAM HATA - {label}] {e}")
            overall_ok = False

    # 2. Doğrudan Ürün Linkini ve Paylaşım Kılavuzunu Ayrı Mesaj Olarak Gönder
    if product_url:
        link_msg = (
            f"🛒 <b>DOĞRUDAN ÜRÜN SATIN ALMA LİNKİ:</b>\n"
            f"👉 {product_url}\n\n"
            f"📱 <b>Hızlı Paylaşım Kılavuzu:</b>\n"
            f"1️⃣ <b>Affiliate Linki:</b> Yukarıdaki link otomatik olarak gelir ortaklığı kodunuzla hazırlanmıştır.\n"
            f"2️⃣ <b>Instagram / TikTok:</b> Videoyu paylaşırken profildeki linke (Telegram veya Web Vitrini) yönlendirin.\n"
            f"3️⃣ <b>Hikaye (Story):</b> Videoyu story atıp <b>'Bağlantı'</b> çıkartmasıyla bu linki yapıştırabilirsiniz!\n"
            f"4️⃣ <b>Web Vitrini:</b> Ürün eş zamanlı olarak web sitenize otomatik eklendi."
        )
        msg_cmd = get_curl_cmd([
            "-s",
            "-F", f"chat_id={cid}",
            "-F", f"text={link_msg}",
            "-F", "parse_mode=HTML",
            f"https://api.telegram.org/bot{token}/sendMessage"
        ])
        subprocess.run(msg_cmd)
        print("🔗 [TELEGRAM] Doğrudan ürün linki ve paylaşım kılavuzu telefonunuza ayrıca iletildi!")

    return overall_ok

def test_telegram_connection(bot_token: str = None) -> dict:
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False, "error": "Token yok"}
    url = f"https://api.telegram.org/bot{token}/getMe"
    cmd = get_curl_cmd(["-s", url])
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(res.stdout)
    except Exception:
        return {"ok": False, "error": "Bağlantı hatası"}
