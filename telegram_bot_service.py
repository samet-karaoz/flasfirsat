import os
import sys
import time
import json
import re
import requests
from dotenv import load_dotenv

from config import BASE_DIR
from affiliate_manager import get_affiliate_url, detect_store
from telegram_notifier import (
    load_pending_deals,
    save_pending_deals,
    edit_telegram_message_caption,
    answer_telegram_callback_query,
    generate_whatsapp_share_url
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@flasfirsat").strip()

DATA_DIR = os.path.join(BASE_DIR, "data")
USER_ALARMS_FILE = os.path.join(DATA_DIR, "user_alarms.json")

def load_user_alarms() -> list:
    if os.path.exists(USER_ALARMS_FILE):
        try:
            with open(USER_ALARMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_user_alarms(alarms: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USER_ALARMS_FILE, "w", encoding="utf-8") as f:
        json.dump(alarms, f, ensure_ascii=False, indent=2)

def extract_urls(text: str) -> list:
    """Metin içindeki HTTP/HTTPS linklerini bulur."""
    return re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text or "")

def send_telegram_text(chat_id: str or int, text: str, reply_markup: dict = None) -> bool:
    """Basit HTML formatlı metin mesajı gönderir."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        res = requests.post(url, data=payload, timeout=15)
        return res.json().get("ok", False)
    except Exception:
        return False

# ==============================================================================
# 1. ADIM: ONAY BUTONU İŞLEYİCİSİ (INSTAGRAM / YOUTUBE / TELEGRAM KANALI)
# ==============================================================================

def handle_callback_query(cq: dict):
    cq_id = cq.get("id")
    data = cq.get("data", "")
    message = cq.get("message", {})
    msg_id = message.get("message_id")
    chat_id = message.get("chat", {}).get("id")

    if data == "test_btn":
        answer_telegram_callback_query(cq_id, text="✅ Test başarılı! Sistem aktif ve çalışıyor.")
        return

    # Örn: approve_ig:deal_1791946000
    action, _, deal_id = data.partition(":")
    pending = load_pending_deals()
    item = pending.get(deal_id)

    if not item:
        answer_telegram_callback_query(cq_id, text="⚠️ Fırsat kaydı bulunamadı veya süresi doldu.", show_alert=True)
        return

    deal = item.get("deal", {})
    title = deal.get("title", "Fırsat")
    video_path = item.get("video_path", "")
    caption_text = item.get("caption_text", "")
    product_url = item.get("product_url", "")
    # 0) TÜM PLATFORMLARA YAYINLA (approve_all)
    if action == "approve_all":
        answer_telegram_callback_query(cq_id, text="🚀 Tüm platformlara yayın başlatılıyor...")
        edit_telegram_message_caption(chat_id, msg_id, f"⏳ <b>Tüm Platformlara Dağıtılıyor...</b>\n\n📦 {title}\nYouTube, Instagram, Telegram ve WhatsApp'a aktarılıyor...")

        statuses = []
        # 1. YouTube Shorts
        try:
            from youtube_publisher import publish_shorts_to_youtube
            yt_res = publish_shorts_to_youtube(video_path, title=title, description=caption_text)
            if yt_res.get("success"):
                statuses.append(f"• 📺 YouTube Shorts: <a href=\"{yt_res.get('url')}\">İzle</a>")
            else:
                statuses.append(f"• 📺 YouTube Shorts: ❌ {yt_res.get('error', 'Hata')}")
        except Exception as ey:
            statuses.append(f"• 📺 YouTube Shorts: ❌ {ey}")

        # 2. Instagram Reels
        try:
            from instagram_publisher import publish_reel_to_instagram
            ig_res = publish_reel_to_instagram(video_path, caption_text)
            if ig_res.get("success"):
                statuses.append("• 🎬 Instagram Reels: ✅ Yayında")
            else:
                statuses.append(f"• 🎬 Instagram Reels: ❌ {ig_res.get('error', 'Hata')}")
        except Exception as ei:
            statuses.append(f"• 🎬 Instagram Reels: ❌ {ei}")

        # 3. Telegram Kanalı
        try:
            from telegram_notifier import send_telegram_deal
            tg_ok = send_telegram_deal(video_path, caption_text, product_url=product_url)
            if tg_ok:
                statuses.append(f"• 📢 Telegram Kanalı: ✅ {TELEGRAM_CHANNEL_ID}")
            else:
                statuses.append("• 📢 Telegram Kanalı: ❌ Hata")
        except Exception as et:
            statuses.append(f"• 📢 Telegram Kanalı: ❌ {et}")

        # 4. WhatsApp Kanalı
        try:
            from whatsapp_publisher import publish_deal_to_whatsapp_channel
            wp_res = publish_deal_to_whatsapp_channel(deal, image_path=deal.get("image_path"))
            if wp_res.get("success"):
                statuses.append("• 🟢 WhatsApp Kanalı: ✅ Flaş Fırsat ⚡")
            else:
                statuses.append(f"• 🟢 WhatsApp Kanalı: ❌ {wp_res.get('error', 'Hata')}")
        except Exception as ew:
            statuses.append(f"• 🟢 WhatsApp Kanalı: ❌ {ew}")

        item["status"] = "published_all"
        save_pending_deals(pending)

        final_caption = (
            f"🎉 <b>TÜM PLATFORMLARDA YAYINLANDI!</b>\n\n"
            f"📦 <b>Ürün:</b> {title}\n"
            f"💰 <b>Fiyat:</b> {deal.get('new_price')}\n\n"
            f"<b>Platform Durumları:</b>\n" + "\n".join(statuses)
        )
        from config import SITE_URL
        markup = {
            "inline_keyboard": [
                [
                    {"text": "🛒 Ürün Sayfası", "url": product_url} if product_url else {"text": "🌐 Web Vitrini", "url": SITE_URL},
                    {"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=telegram&utm_medium=channel"}
                ]
            ]
        }
        edit_telegram_message_caption(chat_id, msg_id, final_caption, reply_markup=markup)
        return

    # A) Instagram Reels Paylaş
    if action == "approve_ig":
        answer_telegram_callback_query(cq_id, text="🚀 Instagram Reels yayını başlatılıyor...")
        edit_telegram_message_caption(chat_id, msg_id, f"⏳ <b>Instagram Reels Yükleniyor...</b>\n\n📦 {title}\nLütfen bekleyin...")

        from instagram_publisher import publish_reel_to_instagram
        
        target_video = video_path if (video_path and os.path.exists(video_path)) else None
        if not target_video:
            if not public_video_url and item.get("file_id"):
                from telegram_notifier import get_telegram_file_url
                public_video_url = get_telegram_file_url(item["file_id"])
            target_video = public_video_url

        if not target_video:
            res_ig = {"success": False, "error": "Videonun dosyası veya genel linki bulunamadı."}
        else:
            res_ig = publish_reel_to_instagram(target_video, caption_text)

        if res_ig.get("success"):
            media_id = res_ig.get("media_id", "")
            item["status"] = "published_instagram"
            save_pending_deals(pending)

            new_caption = (
                f"✅ <b>INSTAGRAM'DA YAYINLANDI! 🎉</b>\n\n"
                f"📦 <b>Ürün:</b> {title}\n"
                f"🆔 <b>Medya ID:</b> {media_id}\n\n"
                f"Diğer kanallara da göndermek ister misiniz?"
            )
            from config import SITE_URL
            wp_url = item.get("whatsapp_share_url") or generate_whatsapp_share_url(deal, product_url)
            markup_buttons = [
                [
                    {"text": "📢 Kanala da At (@flasfirsat)", "callback_data": f"approve_ch:{deal_id}"},
                    {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
                ],
                [
                    {"text": "🟢 WhatsApp'ta Paylaş", "url": wp_url}
                ]
            ]
            row_links = []
            if product_url:
                row_links.append({"text": "🛒 Ürün Sayfası", "url": product_url})
            row_links.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=instagram&utm_medium=reels"})
            markup_buttons.append(row_links)
            markup = {"inline_keyboard": markup_buttons}
            edit_telegram_message_caption(chat_id, msg_id, new_caption, reply_markup=markup)
        else:
            err = res_ig.get("error", "Bilinmeyen hata")
            fail_caption = (
                f"❌ <b>INSTAGRAM YAYIN HATASI:</b>\n{err}\n\n"
                f"📦 <b>Ürün:</b> {title}\nTekrar denemek için butona basabilirsiniz:"
            )
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔄 Tekrar Dene (Instagram)", "callback_data": f"approve_ig:{deal_id}"},
                        {"text": "📢 Kanala At", "callback_data": f"approve_ch:{deal_id}"}
                    ],
                    [{"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}]
                ]
            }
            edit_telegram_message_caption(chat_id, msg_id, fail_caption, reply_markup=markup)

    # B) Kanala Paylaş (@flasfirsat)
    elif action == "approve_ch":
        answer_telegram_callback_query(cq_id, text="📢 Kanala paylaşılıyor...")
        target_ch = TELEGRAM_CHANNEL_ID
        ch_caption = caption_text[:850] if len(caption_text) > 850 else caption_text
        from config import SITE_URL
        site_link = f"{SITE_URL}?utm_source=telegram&utm_medium=channel"
        extras = []
        if product_url:
            extras.append(f"🛒 Satın Al: {product_url}")
        extras.append(f"🌐 Tüm Fırsatlar: {site_link}")
        ch_caption += "\n\n" + "\n".join(extras)

        # Telegram sendVideo to channel
        ch_ok = False
        try:
            with open(video_path, "rb") as vf:
                c_res = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                    data={"chat_id": target_ch, "caption": ch_caption, "supports_streaming": "true"},
                    files={"video": vf},
                    timeout=120
                )
                ch_ok = c_res.json().get("ok", False)
        except Exception as e:
            print(f"[Telegram Service] Kanal gönderim hatası: {e}")

        if ch_ok:
            item["status"] = "published_channel"
            save_pending_deals(pending)
            updated_caption = (
                f"✅ <b>KANALDA PAYLAŞILDI! ({target_ch})</b>\n\n"
                f"📦 <b>Ürün:</b> {title}\n"
                f"💰 <b>Fiyat:</b> {deal.get('new_price')}\n\n"
                f"Diğer platformlar:"
            )
            wp_url = item.get("whatsapp_share_url") or generate_whatsapp_share_url(deal, product_url)
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
                        {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
                    ],
                    [
                        {"text": "🟢 WhatsApp'ta Paylaş", "url": wp_url}
                    ]
                ]
            }
            row_links = []
            if product_url:
                row_links.append({"text": "🛒 Ürün Sayfası", "url": product_url})
            row_links.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=telegram&utm_medium=channel"})
            markup["inline_keyboard"].append(row_links)
            edit_telegram_message_caption(chat_id, msg_id, updated_caption, reply_markup=markup)
        else:
            answer_telegram_callback_query(cq_id, text="❌ Kanala gönderilirken hata oluştu!", show_alert=True)

    # C) YouTube Shorts Paylaş
    elif action == "approve_yt":
        answer_telegram_callback_query(cq_id, text="📺 YouTube Shorts yüklemesi başlatılıyor...")
        edit_telegram_message_caption(chat_id, msg_id, f"⏳ <b>YouTube Shorts Yükleniyor...</b>\n\n📦 {title}\nLütfen bekleyin...")

        target_video = video_path if (video_path and os.path.exists(video_path)) else None
        if not target_video:
            if not public_video_url and item.get("file_id"):
                from telegram_notifier import get_telegram_file_url
                public_video_url = get_telegram_file_url(item["file_id"])
            target_video = public_video_url

        from youtube_publisher import publish_shorts_to_youtube
        yt_res = publish_shorts_to_youtube(target_video or video_path, title=title, description=caption_text)

        if yt_res.get("success"):
            yt_url = yt_res.get("url", "")
            item["status"] = "published_youtube"
            save_pending_deals(pending)

            updated_caption = (
                f"✅ <b>YOUTUBE SHORTS OLARAK YAYINLANDI! 🎉</b>\n\n"
                f"📦 <b>Ürün:</b> {title}\n"
                f"🔗 <b>Shorts Linki:</b> {yt_url}\n\n"
                f"Diğer platformlar:"
            )
            wp_url = item.get("whatsapp_share_url") or generate_whatsapp_share_url(deal, product_url)
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
                        {"text": "📢 Kanala At", "callback_data": f"approve_ch:{deal_id}"}
                    ],
                    [
                        {"text": "🟢 WhatsApp'ta Paylaş", "url": wp_url}
                    ]
                ]
            }
            from config import SITE_URL
            row_links = []
            if yt_url:
                row_links.append({"text": "📺 Shorts Videosunu Aç", "url": yt_url})
            row_links.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=youtube&utm_medium=shorts"})
            markup["inline_keyboard"].append(row_links)
            edit_telegram_message_caption(chat_id, msg_id, updated_caption, reply_markup=markup)
        else:
            err = yt_res.get("error", "Bilinmeyen hata")
            fail_caption = (
                f"❌ <b>YOUTUBE YÜKLEME HATASI:</b>\n{err}\n\n"
                f"📦 <b>Ürün:</b> {title}"
            )
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔄 Tekrar Dene (YouTube)", "callback_data": f"approve_yt:{deal_id}"},
                        {"text": "🎬 Instagram'a At", "callback_data": f"approve_ig:{deal_id}"}
                    ],
                    [{"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}]
                ]
            }
            edit_telegram_message_caption(chat_id, msg_id, fail_caption, reply_markup=markup)

    # D) WhatsApp Kanalında Otomatik Paylaş
    elif action == "approve_wp":
        answer_telegram_callback_query(cq_id, text="🟢 WhatsApp Kanalı yüklemesi başlatılıyor...")
        edit_telegram_message_caption(chat_id, msg_id, f"⏳ <b>WhatsApp Kanalına Yükleniyor...</b>\n\n📦 {title}\nLütfen bekleyin...")

        from whatsapp_publisher import publish_deal_to_whatsapp_channel, check_whatsapp_ready
        chk = check_whatsapp_ready()
        if not chk.get("ready"):
            fail_caption = (
                f"❌ <b>WHATSAPP WEB OTURUMU GEREKLİ!</b>\n\n"
                f"Otomatik paylaşım için bilgisayarınızda bir defaya mahsus:\n"
                f"<code>python whatsapp_auth.py</code>\n"
                f"çalıştırıp QR kodu telefonunuzdan okutun.\n\n"
                f"<i>(Dilerseniz alttaki butondan mobilde tek tıkla hemen paylaşabilirsiniz)</i>"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "📲 WhatsApp Paylaş (Mobil)", "url": item.get("whatsapp_share_url") or generate_whatsapp_share_url(deal, product_url)}],
                    [{"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}]
                ]
            }
            edit_telegram_message_caption(chat_id, msg_id, fail_caption, reply_markup=markup)
        else:
            wp_res = publish_deal_to_whatsapp_channel(deal, image_path=deal.get("image_path") or item.get("image_path"))
            if wp_res.get("success"):
                item["status"] = "published_whatsapp"
                save_pending_deals(pending)

                updated_caption = (
                    f"✅ <b>WHATSAPP KANALINDA YAYINLANDI! 🎉</b>\n\n"
                    f"📦 <b>Ürün:</b> {title}\n"
                    f"💰 <b>Fiyat:</b> {deal.get('new_price')}\n\n"
                    f"Diğer platformlar:"
                )
                markup = {
                    "inline_keyboard": [
                        [
                            {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
                            {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
                        ],
                        [
                            {"text": "📢 Kanala At (@flasfirsat)", "callback_data": f"approve_ch:{deal_id}"}
                        ]
                    ]
                }
                from config import SITE_URL
                row_links = []
                if product_url:
                    row_links.append({"text": "🛒 Ürün Sayfası", "url": product_url})
                row_links.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=whatsapp&utm_medium=channel"})
                markup["inline_keyboard"].append(row_links)
                edit_telegram_message_caption(chat_id, msg_id, updated_caption, reply_markup=markup)
            else:
                err = wp_res.get("error", "Bilinmeyen hata")
                fail_caption = (
                    f"❌ <b>WHATSAPP YÜKLEME HATASI:</b>\n{err}\n\n"
                    f"📦 <b>Ürün:</b> {title}\nMobilden tek tıkla gönderebilirsiniz:"
                )
                markup = {
                    "inline_keyboard": [
                        [
                            {"text": "🔄 Tekrar Dene (Oto)", "callback_data": f"approve_wp:{deal_id}"},
                            {"text": "📲 Mobil WhatsApp", "url": item.get("whatsapp_share_url") or generate_whatsapp_share_url(deal, product_url)}
                        ],
                        [{"text": "❌ İptal Et", "callback_data": f"reject:{deal_id}"}]
                    ]
                }
                edit_telegram_message_caption(chat_id, msg_id, fail_caption, reply_markup=markup)

    # E) İptal Et
    elif action == "reject":
        answer_telegram_callback_query(cq_id, text="❌ Fırsat iptal edildi.")
        item["status"] = "rejected"
        save_pending_deals(pending)
        edit_telegram_message_caption(
            chat_id,
            msg_id,
            f"❌ <b>FIRSAT YAYINI İPTAL EDİLDİ.</b>\n\n📦 <b>Ürün:</b> {title}\nBu içerik hiçbir platformda paylaşılmayacak.",
            reply_markup={"inline_keyboard": []}
        )

# ==============================================================================
# 3. ADIM: FİYAT TAKİP VE ALARM SİSTEMİ (/takip [link], /listem, /yardim)
# ==============================================================================

def handle_user_message(msg: dict):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()
    user_name = chat.get("first_name") or chat.get("username") or "Kullanıcı"

    if not text or not chat_id:
        return

    # 1. /start Komutu
    if text.startswith("/start"):
        welcome = (
            f"👋 <b>Merhaba {user_name}! Ben Fırsat Avcısı Botu.</b> 🎯\n\n"
            "İnternetteki en büyük indirimleri senin için takip eder, fiyatı düşünce ilk sana haber veririm!\n\n"
            "📌 <b>Nasıl Kullanılır?</b>\n"
            "Takip etmek istediğin herhangi bir <b>Amazon, Trendyol veya Hepsiburada</b> ürün linkini bana mesaj olarak göndermen yeterli!\n\n"
            "💡 <b>Komutlar:</b>\n"
            "• <code>/program</code> - Günlük 12:30 & 20:00 yayın saatleri ve sıradaki paylaşım\n"
            "• <code>/otopilot</code> - Saati beklemeden hemen 4 platforma yayın yap\n"
            "• <code>/takip [link]</code> - Ürünü fiyat takibine alır\n"
            "• <code>/listem</code> - Takip ettiğin ürünleri listeler\n"
            "• <code>/stats</code> - Web vitrini ve etkileşim analizlerini gösterir\n"
            "• <code>/yardim</code> - Kullanım rehberi"
        )
        send_telegram_text(chat_id, welcome)
        return

    # 1.5 /program veya /zamanlayici Komutu
    if text.startswith("/program") or text.startswith("/zamanlayici"):
        from scheduler_service import get_next_run_info
        info = get_next_run_info()
        prog_msg = (
            "⏰ <b>FLAŞ FIRSAT OTOPİLOT YAYIN PROGRAMI</b> 🚀\n\n"
            "Algoritmanın en yüksek etkileşim verdiği 2 saat kuşağı:\n"
            "• 🌞 <b>1. Kuşak (Öğle Molası):</b> 12:30\n"
            "• 🌙 <b>2. Kuşak (Akşam Prime Time):</b> 20:00\n\n"
            f"👉 <b>Bir Sonraki Otomatik Yayın:</b> {info['next_time']}\n"
            f"⏳ <b>Kalan Süre:</b> {info['remaining_str']} ({info['slot_name']})\n\n"
            "📱 <b>Otomatik Yayınlanan Platformlar:</b>\n"
            "• 📺 YouTube Shorts\n"
            "• 🎬 Instagram Reels (@flasfirsat)\n"
            "• 📢 Telegram Kanalı (@flasfirsat)\n"
            "• 🟢 WhatsApp Kanalı (Flaş Fırsat ⚡)\n"
            "• 🌐 Web Vitrini (Canlı İndirim Radarı)\n\n"
            "💡 <i>Saati beklemeden hemen yayınlatmak için: <code>/otopilot</code></i>"
        )
        send_telegram_text(chat_id, prog_msg)
        return

    # 1.6 /otopilot Komutu (Hemen Tek Tıkla Döngü Başlat)
    if text.startswith("/otopilot"):
        send_telegram_text(chat_id, "🚀 <b>Otopilot döngüsü başlatıldı!</b>\n\nEn iyi indirim avlanıyor, split-screen video üretiliyor ve YouTube, Instagram, Telegram ve WhatsApp kanallarına otomatik dağıtılıyor. İşlem tamamlandığında rapor iletilecektir...")
        import threading
        from autopilot_engine import run_autopilot_deal_cycle
        threading.Thread(target=run_autopilot_deal_cycle, kwargs={"dry_run": False, "slot_name": "Telegram Manuel Tetikleme"}, daemon=True).start()
        return

    # 2. /yardim Komutu
    if text.startswith("/yardim"):
        help_text = (
            "ℹ️ <b>Fırsat Avcısı & Otopilot Rehberi</b>\n\n"
            "🤖 <b>24/7 Otopilot Yayın Sistemi:</b>\n"
            "Sistem her gün <b>12:30</b> ve <b>20:00</b> saatlerinde en iyi indirimi otomatik bulur, 9:16 reels videosunu derler ve tüm sosyal medya platformlarınıza eş zamanlı yükler!\n\n"
            "💡 <b>Yönetim Komutları:</b>\n"
            "• <code>/program</code> - Sıradaki otomatik yayın zamanı\n"
            "• <code>/otopilot</code> - Hemen otomatik video üret ve 4 kanala yayınla\n"
            "• <code>/stats</code> - Web paneli ve ziyaretçi istatistikleri\n"
            "• <code>/takip [link]</code> - İstediğin ürünü fiyat takibine al\n"
            "• <code>/listem</code> - Takip listen\n"
        )
        send_telegram_text(chat_id, help_text)
        return

    # 3. /listem Komutu
    if text.startswith("/listem"):
        alarms = load_user_alarms()
        user_alarms = [a for a in alarms if a.get("chat_id") == chat_id and a.get("status") == "active"]
        if not user_alarms:
            send_telegram_text(chat_id, "📋 Henüz takip ettiğiniz aktif bir ürün yok. Link göndererek takibe başlayabilirsiniz!")
            return

        resp = f"📋 <b>Takip Listeniz ({len(user_alarms)} Ürün):</b>\n\n"
        for i, a in enumerate(user_alarms, 1):
            resp += f"{i}. <b>{a.get('title', 'Ürün')[:40]}...</b>\n"
            resp += f"   💰 Başlangıç Fiyatı: <b>{a.get('initial_price_str', 'Bilinmiyor')}</b> ({a.get('store_name')})\n"
            resp += f"   ❌ Takibi Bırak: <code>/sil {a.get('alarm_id')}</code>\n\n"
        send_telegram_text(chat_id, resp)
        return

    # 3.5 /stats veya /web Komutu
    if text.startswith("/stats") or text.startswith("/web"):
        from web_showcase import load_deals
        from config import SITE_URL, GA_MEASUREMENT_ID
        deals = load_deals()
        amazon_cnt = sum(1 for d in deals if "amazon" in d.get("store_name", "").lower())
        trendyol_cnt = sum(1 for d in deals if "trendyol" in d.get("store_name", "").lower())
        hb_cnt = sum(1 for d in deals if "hepsi" in d.get("store_name", "").lower())
        other_cnt = len(deals) - (amazon_cnt + trendyol_cnt + hb_cnt)

        ga_status = f"🟢 Aktif (<code>{GA_MEASUREMENT_ID}</code>)" if GA_MEASUREMENT_ID else "🟡 Yerel Telemetri (Tarayıcı İçi)"

        stats_msg = (
            f"📊 <b>FLAŞ FIRSAT WEB & ANALİTİK PANELİ</b> ⚡\n\n"
            f"🌐 <b>Web Vitrini:</b> {SITE_URL}\n"
            f"📦 <b>Yayındaki Aktif Fırsat:</b> {len(deals)} adet\n\n"
            f"🏪 <b>Mağaza Dağılımı:</b>\n"
            f" • Amazon TR: <b>{amazon_cnt}</b>\n"
            f" • Trendyol: <b>{trendyol_cnt}</b>\n"
            f" • Hepsiburada: <b>{hb_cnt}</b>\n"
        )
        if other_cnt > 0:
            stats_msg += f" • Diğer: <b>{other_cnt}</b>\n"
        stats_msg += (
            f"\n📈 <b>Google Analytics 4:</b> {ga_status}\n\n"
            f"🔗 <b>Sosyal Medya UTM Linkleri:</b>\n"
            f" • Instagram: <code>{SITE_URL}?utm_source=instagram</code>\n"
            f" • YouTube: <code>{SITE_URL}?utm_source=youtube</code>\n"
            f" • Telegram: <code>{SITE_URL}?utm_source=telegram</code>\n\n"
            f"👇 <i>Canlı ziyaretçi, tıklama ve cihaz grafiklerini görmek için butona tıklayın:</i>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "📊 Canlı Web Panelini Aç (Yönetici)", "url": f"{SITE_URL}?admin=flas"}]
            ]
        }
        send_telegram_text(chat_id, stats_msg, reply_markup=markup)
        return

    # 4. /sil <alarm_id>
    if text.startswith("/sil"):
        parts = text.split()
        if len(parts) > 1:
            target_id = parts[1].strip()
            alarms = load_user_alarms()
            found = False
            for a in alarms:
                if a.get("alarm_id") == target_id and a.get("chat_id") == chat_id:
                    a["status"] = "cancelled"
                    found = True
                    break
            if found:
                save_user_alarms(alarms)
                send_telegram_text(chat_id, f"✅ <code>{target_id}</code> kodlu ürün takipten çıkarıldı.")
            else:
                send_telegram_text(chat_id, "⚠️ Bu ID'ye ait aktif bir takip bulunamadı.")
        return

    # 5. Link Gönderimi veya /takip Link
    found_urls = extract_urls(text)
    if found_urls:
        raw_url = found_urls[0]
        store = detect_store(raw_url)
        send_telegram_text(chat_id, f"🔍 <b>{store}</b> linki inceleniyor ve güncel fiyat taranıyor...")

        from deal_hunter import parse_deal_from_url
        try:
            deal_data = parse_deal_from_url(raw_url)
            title = deal_data.get("title", "Takip Edilen Ürün")
            price_str = deal_data.get("new_price") or deal_data.get("old_price") or "0 TL"
            from deal_hunter import parse_price_to_float
            price_val = parse_price_to_float(price_str)

            alarm_id = f"alm_{int(time.time())}"
            alarms = load_user_alarms()
            alarms.append({
                "alarm_id": alarm_id,
                "chat_id": chat_id,
                "username": user_name,
                "url": raw_url,
                "title": title,
                "initial_price": price_val,
                "initial_price_str": price_str,
                "store_name": store,
                "status": "active",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            save_user_alarms(alarms)

            success_msg = (
                f"🎯 <b>Ürün Başarıyla Takibe Alındı!</b>\n\n"
                f"📦 <b>Ürün:</b> {title}\n"
                f"💰 <b>Kayıt Fiyatı:</b> {price_str}\n"
                f"🏪 <b>Mağaza:</b> {store}\n"
                f"🆔 <b>Takip Kodu:</b> <code>{alarm_id}</code>\n\n"
                f"🔔 Bu ürünün fiyatı düştüğü anda sana özel affiliate linkiyle buradan haber vereceğim!"
            )
            send_telegram_text(chat_id, success_msg)
        except Exception as e:
            send_telegram_text(chat_id, f"❌ Ürün bilgileri alınırken hata oluştu: {e}")
        return

def check_user_price_alarms():
    """
    Kullanıcıların takip ettiği ürünlerin fiyatlarını kontrol eder.
    Fiyat düşüşü tespit edildiğinde doğrudan kullanıcıya affiliate linkiyle haber verir!
    """
    alarms = load_user_alarms()
    active_alarms = [a for a in alarms if a.get("status") == "active"]
    if not active_alarms:
        return

    from deal_hunter import parse_deal_from_url, parse_price_to_float

    for a in active_alarms:
        try:
            url = a.get("url")
            fresh = parse_deal_from_url(url)
            current_str = fresh.get("new_price") or fresh.get("old_price")
            if not current_str:
                continue

            current_val = parse_price_to_float(current_str)
            init_val = a.get("initial_price", 0.0)

            # En az %3 fiyat düşüşü varsa bildir
            if init_val > 0 and current_val < (init_val * 0.97):
                diff = init_val - current_val
                pct = int(((init_val - current_val) / init_val) * 100)
                aff_url = get_affiliate_url(url, a.get("store_name"))

                alert_msg = (
                    f"🚨 <b>MÜJDE! TAKİP ETTİĞİN ÜRÜN İNDİRİME GİRDİ!</b> 🔥\n\n"
                    f"📦 <b>{a.get('title')}</b>\n\n"
                    f"❌ Eski Fiyat: <s>{a.get('initial_price_str')}</s>\n"
                    f"🔥 <b>Yeni Fiyat: {current_str}</b> (-%{pct})\n"
                    f"💸 <b>Net İndirim: {int(diff):,} TL</b>\n\n"
                    f"🛒 <b>İndirimli Satın Almak İçin Tıkla:</b>\n"
                    f"👉 {aff_url}\n\n"
                    f"<i>(Fırsat ürünleri hızla tükenebilir, kaçırmayın!)</i>"
                )
                send_telegram_text(a.get("chat_id"), alert_msg)
                # Alarmı güncellendi olarak işaretle
                a["status"] = "notified"
                a["last_notified_price"] = current_val
                save_user_alarms(alarms)
                print(f"[Price Alarm] 🔔 Bildirim gönderildi -> {a.get('username')} ({a.get('title')})")
        except Exception as ex:
            print(f"[Price Alarm] Kontrol hatası ({a.get('title')}): {ex}")

# ==============================================================================
# ANA TELEGRAM SERVİS DÖNGÜSÜ
# ==============================================================================

def run_telegram_service():
    """
    Telegram Bot API dinleyicisini başlatır (Long Polling).
    Onay butonlarını ve fiyat alarm taleplerini eş zamanlı yönetir.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram Service] ⚠️ TELEGRAM_BOT_TOKEN eksik. Servis başlatılamadı.")
        return

    print("=======================================================")
    print("🤖 [TELEGRAM INTERAKTIF YÖNETİM & ALARM SERVİSİ BAŞLADI]")
    print("• Yönetici Onay Butonları: Aktif (Instagram, YouTube, Kanal)")
    print("• Kişisel Fiyat Takip Botu (/takip, /listem): Aktif")
    print("• 24/7 Otopilot Zamanlayıcı: Aktif (12:30 & 20:00)")
    print("Durdurmak için Ctrl+C basabilirsiniz.")
    print("=======================================================\n")

    # Otopilot Zamanlayıcıyı Arka Planda Başlat (12:30 ve 20:00)
    try:
        import threading
        from scheduler_service import run_scheduler_daemon
        sched_thread = threading.Thread(target=run_scheduler_daemon, kwargs={"dry_run": False}, daemon=True)
        sched_thread.start()
        print("⏰ [ZAMANLAYICI SERVİSİ] 12:30 & 20:00 kuşağı için arka plan iş parçacığı başlatıldı.\n")
    except Exception as es:
        print(f"[Telegram Service] Zamanlayıcı başlatılamadı: {es}")

    offset = None
    last_alarm_check = time.time()

    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            res = requests.get(url, params=params, timeout=35)
            data = res.json()

            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    # Buton Tıklaması (Callback Query)
                    if "callback_query" in update:
                        handle_callback_query(update["callback_query"])

                    # Kullanıcı Mesajı
                    elif "message" in update:
                        handle_user_message(update["message"])

            # 15 dakikada bir kullanıcı alarmlarını kontrol et
            if time.time() - last_alarm_check > 900:
                print("[Telegram Service] ⏰ Takip edilen ürünlerin fiyatları kontrol ediliyor...")
                check_user_price_alarms()
                last_alarm_check = time.time()

        except requests.exceptions.RequestException:
            time.sleep(3)
        except Exception as e:
            print(f"[Telegram Service] Döngü hatası: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_telegram_service()
