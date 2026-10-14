import os
import time
import json
import requests
from config import BASE_DIR
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@flasfirsat").strip()

PENDING_DEALS_FILE = os.path.join(BASE_DIR, "data", "pending_deals.json")

def load_pending_deals() -> dict:
    if os.path.exists(PENDING_DEALS_FILE):
        try:
            with open(PENDING_DEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pending_deals(deals: dict):
    os.makedirs(os.path.dirname(PENDING_DEALS_FILE), exist_ok=True)
    with open(PENDING_DEALS_FILE, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)

def get_telegram_file_url(file_id: str, bot_token: str = None) -> str:
    """Telegram'a yüklenmiş bir dosyanın doğrudan genel (public) indirme linkini alır."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token or not file_id:
        return ""
    try:
        url = f"https://api.telegram.org/bot{token}/getFile"
        res = requests.get(url, params={"file_id": file_id}, timeout=10)
        data = res.json()
        if data.get("ok"):
            file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as e:
        print(f"[Telegram Notifier] getFile hatası: {e}")
    return ""

def send_telegram_deal_for_approval(
    deal: dict,
    video_path: str,
    caption_text: str,
    product_url: str = None,
    chat_id: str = None,
    bot_token: str = None
) -> dict:
    """
    Üretilen videoyu doğrudan yöneticiye (chat_id) interaktif onay butonlarıyla gönderir.
    Instagram Reels, YouTube Shorts veya Kanalda yayınlama kararı butona tıklanarak verilir.
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    if not token or not cid:
        print("[Telegram Notifier] ⚠️ Token veya Chat ID eksik.")
        return {"success": False, "error": "Token veya Chat ID eksik"}

    if not os.path.exists(video_path):
        print(f"[Telegram Notifier] ❌ Video dosyası bulunamadı: {video_path}")
        return {"success": False, "error": "Video bulunamadı"}

    timestamp = int(time.time())
    deal_id = f"deal_{timestamp}"

    title = deal.get("title", "Fırsat Ürünü")
    new_price = deal.get("new_price", "")
    old_price = deal.get("old_price", "")
    discount_pct = deal.get("discount_pct", "")
    store = deal.get("store_name", "Amazon TR")
    net_cost = deal.get("net_cost", "")
    bank_camp = deal.get("bank_campaign", "")

    # Yönetici Önizleme Mesajı
    approval_caption = (
        f"🎬 <b>YENİ FIRSAT ONAY BEKLİYOR!</b>\n\n"
        f"📦 <b>Ürün:</b> {title}\n"
        f"💰 <b>Fiyat:</b> <s>{old_price}</s> ➔ <b>{new_price}</b> ({discount_pct})\n"
    )
    if net_cost:
        approval_caption += f"💳 <b>Net Maliyet:</b> {net_cost} ({bank_camp})\n"
    approval_caption += f"🏪 <b>Mağaza:</b> {store}\n\n"
    approval_caption += "👇 <i>Yayınlamak istediğiniz platformu seçin:</i>"

    # Butonlar
    inline_keyboard = [
        [
            {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
            {"text": "📢 Kanala At (@flasfirsat)", "callback_data": f"approve_ch:{deal_id}"}
        ],
        [
            {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"},
            {"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}
        ]
    ]
    if product_url:
        inline_keyboard.append([
            {"text": "🛒 Ürün Sayfasını Aç", "url": product_url}
        ])

    reply_markup = {"inline_keyboard": inline_keyboard}

    print(f"[Telegram Notifier] 📲 Video yönetici onayına gönderiliyor: {title}...")
    api_url = f"https://api.telegram.org/bot{token}/sendVideo"

    try:
        with open(video_path, "rb") as video_file:
            payload = {
                "chat_id": cid,
                "caption": approval_caption,
                "parse_mode": "HTML",
                "supports_streaming": "true",
                "reply_markup": json.dumps(reply_markup)
            }
            files = {"video": video_file}
            res = requests.post(api_url, data=payload, files=files, timeout=120)

        data = res.json()
        if not data.get("ok"):
            err_desc = data.get("description", str(data))
            print(f"[Telegram Notifier] ❌ Onay videosu gönderilemedi: {err_desc}")
            return {"success": False, "error": err_desc}

        msg_id = data["result"]["message_id"]
        file_id = data["result"].get("video", {}).get("file_id", "")
        public_url = get_telegram_file_url(file_id, token) if file_id else ""

        # Bekleyen fırsatlara kaydet (Token içeren URL diske yazılmaz, sadece file_id saklanır)
        pending = load_pending_deals()
        pending[deal_id] = {
            "deal_id": deal_id,
            "message_id": msg_id,
            "chat_id": cid,
            "deal": deal,
            "video_path": video_path,
            "caption_text": caption_text,
            "product_url": product_url,
            "file_id": file_id,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_pending_deals(pending)

        print(f"✅ [Telegram Notifier] Fırsat yönetici onayına sunuldu! (Deal ID: {deal_id}, Mesaj ID: {msg_id})")
        return {
            "success": True,
            "deal_id": deal_id,
            "message_id": msg_id,
            "file_id": file_id,
            "public_video_url": public_url
        }

    except Exception as e:
        print(f"[Telegram Notifier] ❌ İstek hatası: {e}")
        return {"success": False, "error": str(e)}

def edit_telegram_message_caption(chat_id: str, message_id: int, new_caption: str, reply_markup: dict = None, bot_token: str = None) -> bool:
    """Gönderilmiş bir Telegram mesajının başlık ve butonlarını günceller."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/editMessageCaption"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": new_caption,
        "parse_mode": "HTML"
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json().get("ok", False)
    except Exception:
        return False

def answer_telegram_callback_query(callback_query_id: str, text: str = "", show_alert: bool = False, bot_token: str = None) -> bool:
    """Telegram buton tıklamasını (callback query) onaylar ve bildirim balonu gösterir."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    try:
        res = requests.post(url, data={"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}, timeout=10)
        return res.json().get("ok", False)
    except Exception:
        return False

def send_telegram_deal(video_path: str, caption_text: str, product_url: str = None, chat_id: str = None, bot_token: str = None) -> bool:
    """
    Üretilen MP4 videosunu doğrudan kanala ve telefona yayınlar (Otomatik doğrudan mod).
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

    if not targets or not os.path.exists(video_path):
        return False

    short_caption = caption_text[:1000] if len(caption_text) > 1000 else caption_text
    if product_url:
        caption_with_url = f"{short_caption}\n\n🛒 Doğrudan Satın Al: {product_url}"
        if len(caption_with_url) <= 1024:
            short_caption = caption_with_url

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    overall_ok = True

    for target in targets:
        label = "Kanal (@flasfirsat)" if target == TELEGRAM_CHANNEL_ID else "Telefon (Özel)"
        try:
            with open(video_path, "rb") as vf:
                data = {
                    "chat_id": target,
                    "caption": short_caption,
                    "supports_streaming": "true"
                }
                res = requests.post(url, data=data, files={"video": vf}, timeout=120)
                resp_data = res.json()
                if resp_data.get("ok"):
                    print(f"✅ [TELEGRAM] {label} paylaşımı başarılı!")
                else:
                    print(f"❌ [TELEGRAM HATA - {label}] {resp_data.get('description')}")
                    overall_ok = False
        except Exception as e:
            print(f"❌ [TELEGRAM HATA - {label}] {e}")
            overall_ok = False

    return overall_ok

def test_telegram_connection(bot_token: str = None) -> dict:
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False, "error": "Token yok"}
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_telegram_alert(message: str, chat_id: str = None, bot_token: str = None) -> bool:
    """Sistem hatalarını veya CAPTCHA engellerini anında Telegram üzerinden bildirir."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID
    if not token or not cid:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": f"⚠️ <b>[OTOMASYON UYARISI]</b>\n\n{message}",
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json().get("ok", False)
    except Exception:
        return False
