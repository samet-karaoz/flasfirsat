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

def generate_whatsapp_share_url(deal: dict, product_url: str = "") -> str:
    """WhatsApp desteği kullanıcı talebiyle kaldırılmıştır."""
    return ""

def send_telegram_deal_for_approval(
    deal: dict,
    video_path: str,
    caption_text: str,
    product_url: str = None,
    chat_id: str = None,
    bot_token: str = None,
    youtube_video_path: str = None,
    story_image_path: str = None
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
    installment = deal.get("installment", "")
    coupon_info = str(deal.get("coupon_info", "")).strip()

    deal_code = deal.get("deal_code", "")
    code_line = f"🔢 <b>Fırsat Kodu:</b> <code>{deal_code}</code>\n" if deal_code else ""

    # Yönetici Önizleme Mesajı
    approval_caption = (
        f"🎬 <b>YENİ FIRSAT ONAY BEKLİYOR!</b>\n\n"
        f"{code_line}"
        f"📦 <b>Ürün:</b> {title}\n"
        f"💰 <b>Fiyat:</b> <s>{old_price}</s> ➔ <b>{new_price}</b> ({discount_pct})\n"
    )
    if coupon_info:
        approval_caption += f"🎟️ <b>Kupon:</b> {coupon_info} (Sayfada Aktif Et)\n"
    if installment:
        approval_caption += f"💳 <b>Ödeme:</b> {installment}\n"
    approval_caption += f"🏪 <b>Mağaza:</b> {store}\n\n"
    approval_caption += "👇 <i>Yayınlamak istediğiniz platformu seçin:</i>"


    # Butonlar (%100 Organik Instagram Stüdyo Paketi & Resmi API Dağıtımı)
    inline_keyboard = [
        [
            {"text": "🚀 TÜMÜNE YAYINLA (YT + Kanal + Web + IG Paketi)", "callback_data": f"approve_all:{deal_id}"}
        ],
        [
            {"text": "📲 IG Stüdyo Paketi (Story + Kopyala)", "callback_data": f"approve_ig:{deal_id}"},
            {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
        ],
        [
            {"text": "📢 Kanala At (@flasfirsat)", "callback_data": f"approve_ch:{deal_id}"}
        ],
        [
            {"text": "🚨 Fiyat Hatası / Acil Modu (Aç/Kapa)", "callback_data": f"toggle_urgent:{deal_id}"}
        ],
        [{"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}]
    ]
    btn_row = []
    if product_url:
        btn_row.append({"text": "🛒 Ürün Sayfasını Aç", "url": product_url})
    from config import SITE_URL
    btn_row.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=telegram&utm_medium=channel"})
    inline_keyboard.append(btn_row)

    reply_markup = {"inline_keyboard": inline_keyboard}

    print(f"[Telegram Notifier] 📲 Video yönetici onayına gönderiliyor: {title}...")
    api_url = f"https://api.telegram.org/bot{token}/sendVideo"

    try:
        from datetime import datetime as _dt
        clean_fname = _dt.now().strftime("VID_%Y%m%d_%H%M%S.mp4")
        with open(video_path, "rb") as video_file:
            payload = {
                "chat_id": cid,
                "caption": approval_caption,
                "parse_mode": "HTML",
                "supports_streaming": "true",
                "reply_markup": json.dumps(reply_markup)
            }
            files = {"video": (clean_fname, video_file, "video/mp4")}
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
            "youtube_video_path": youtube_video_path,
            "story_image_path": story_image_path,
            "caption_text": caption_text,
            "product_url": product_url,
            "file_id": file_id,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_pending_deals(pending)

        # ☁️ BULUT BAĞIMSIZLIĞI (PC Kapalıyken GitHub Actions Üzerinde Çalışma):
        # Eğer bulut sunucusunda (GITHUB_ACTIONS=true) çalışıyorsa, PC kapalı olabileceği için
        # Story kartını, 4'lü Kopyala-Yapıştır Stüdyo Paketini, Telegram Kanalını ve YouTube Shorts'u
        # butona basılmasını beklemeden otomatik tamamla!
        if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
            try:
                import html as _html
                import re as _re
                print("[Telegram Notifier] ☁️ Bulut Modu Aktif: Story Paketi, Kanal ve YouTube otomatik dağıtılıyor...")
                # 1. Story görselini gönder
                if story_image_path and os.path.exists(story_image_path):
                    with open(story_image_path, "rb") as sf:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendPhoto",
                            data={
                                "chat_id": cid,
                                "caption": (
                                    f"📸 <b>1080x1920 HİKAYE (STORY) KARTI HAZIR!</b>\n\n"
                                    f"🔗 <b>Link Çıkartması İçin Kopyala:</b>\n"
                                    f"<code>{_html.escape(product_url or '')}</code>"
                                ),
                                "parse_mode": "HTML"
                            },
                            files={"photo": sf},
                            timeout=45
                        )
                # 2. 4'lü Kopyala-Yapıştır Stüdyo Kutularını gönder
                clean_w = _re.findall(r'\w+', (title or "").lower())
                seo_w = [w for w in clean_w if len(w) > 2][:5] + ["indirim", "fırsat", "kampanya", "amazon", "keşfet"]
                seo_str = " ".join(list(dict.fromkeys(seo_w)))
                code_pin = f"🔢 Fırsat Kodu: {deal_code} (flasfirsat.com.tr arama kutusuna {deal_code} yazarak anında bulabilirsiniz!)\n\n" if deal_code else ""
                first_comm = (
                    f"📌 Ürün linki şu an Hikayemizde (Story) ve profilimizdeki sitede (flasfirsat.com.tr) aktif! 24 saat dolmadan Hikayemizden direkt ürüne gidebilirsiniz 👇\n\n"
                    f"{code_pin}"
                    f"Sizce bu fiyata değer mi, alınır mı? Yorumlarda buluşalım!"
                )
                studio_msg = (
                    f"📲 <b>%100 ORGANİK INSTAGRAM & TIKTOK STÜDYO PAKETİ (Bulut Otomatik)</b>\n"
                    f"<i>(Üzerine bir kez dokunduğunuz metin otomatik kopyalanır)</i>\n\n"
                    f"📋 <b>1. REELS / TIKTOK AÇIKLAMASI (Dokun & Kopyala):</b>\n"
                    f"<code>{_html.escape(caption_text)}</code>\n\n"
                    f"💬 <b>2. BAŞA TUTTURULACAK İLK YORUM (Dokun & Kopyala):</b>\n"
                    f"<code>{_html.escape(first_comm)}</code>\n\n"
                    f"🔗 <b>3. HİKAYE (STORY) LİNKİ (Dokun & Kopyala):</b>\n"
                    f"<code>{_html.escape(product_url or '')}</code>\n\n"
                    f"🔍 <b>4. INSTAGRAM 'Aa' GÖRÜNMEZ SEO KELİMELERİ:</b>\n"
                    f"<code>{_html.escape(seo_str)}</code>"
                )
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": cid, "text": studio_msg, "parse_mode": "HTML"},
                    timeout=20
                )
                # 3. Telegram Kanalına (@flasfirsat) otomatik paylaş
                send_telegram_deal(video_path, caption_text, product_url=product_url, channel_only=True)
                # 4. YouTube Shorts'a otomatik yükle
                try:
                    from youtube_publisher import publish_shorts_to_youtube
                    yt_v = youtube_video_path if (youtube_video_path and os.path.exists(youtube_video_path)) else video_path
                    publish_shorts_to_youtube(yt_v, title=title, description=caption_text)
                except Exception as eyt:
                    print(f"[Telegram Notifier] Bulut YouTube yükleme uyarısı: {eyt}")
            except Exception as ecl:
                print(f"[Telegram Notifier] Bulut otomatik paket gönderim uyarısı: {ecl}")

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

def send_telegram_deal(video_path: str, caption_text: str, product_url: str = None, chat_id: str = None, bot_token: str = None, channel_only: bool = False) -> bool:
    """
    Üretilen MP4 videosunu kanala ve/veya telefona yayınlar.
    channel_only=True ise sadece TELEGRAM_CHANNEL_ID kanalına atar (onay sonrasında admin'e çift video gitmesini önler).
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    if not token:
        print("\n[Telegram Notifier] ⚠️ TELEGRAM_BOT_TOKEN ayarlanmamış.")
        return False

    targets = []
    if channel_only:
        if TELEGRAM_CHANNEL_ID:
            targets.append(TELEGRAM_CHANNEL_ID)
    else:
        if cid:
            targets.append(cid)
        if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID not in targets:
            targets.append(TELEGRAM_CHANNEL_ID)

    if not targets or not os.path.exists(video_path):
        return False

    short_caption = caption_text[:850] if len(caption_text) > 850 else caption_text
    from config import SITE_URL
    site_link = f"{SITE_URL}?utm_source=telegram&utm_medium=channel"
    extras = []
    if product_url:
        extras.append(f"🛒 Doğrudan Satın Al: {product_url}")
    extras.append(f"🌐 Tüm Fırsatlar & Radar: {site_link}")
    caption_with_url = f"{short_caption}\n\n" + "\n".join(extras)
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
