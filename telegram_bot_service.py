import os
import sys
import time
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

from config import BASE_DIR
from affiliate_manager import get_affiliate_url, detect_store
from telegram_notifier import (
    load_pending_deals,
    save_pending_deals,
    edit_telegram_message_caption,
    answer_telegram_callback_query,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@flasfirsat").strip()

DATA_DIR = os.path.join(BASE_DIR, "data")
USER_ALARMS_FILE = os.path.join(DATA_DIR, "user_alarms.json")
IS_DM_SCANNING = False

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

def ensure_local_video(item: dict) -> str:
    """
    Videonun yerel dosyasını doğrular.
    Eğer yerel dosya silinmişse veya GitHub Actions (bulut) tarafından üretilmişse,
    Telegram file_id üzerinden doğrudan temp/ klasörüne indirir.
    """
    v_path = item.get("video_path", "")
    if v_path and os.path.exists(v_path) and os.path.getsize(v_path) > 1000:
        return v_path

    file_id = item.get("file_id")
    if file_id:
        try:
            from telegram_notifier import get_telegram_file_url
            file_url = get_telegram_file_url(file_id)
            if file_url:
                dl_dir = os.path.join(BASE_DIR, "temp")
                os.makedirs(dl_dir, exist_ok=True)
                deal_id = item.get("deal_id", f"video_{int(time.time())}")
                dl_path = os.path.join(dl_dir, f"dl_{deal_id}.mp4")
                print(f"[Telegram Service] 📥 Video Telegram sunucusundan indiriliyor (file_id: {file_id[:15]}...)...")
                r = requests.get(file_url, stream=True, timeout=60)
                if r.status_code == 200:
                    with open(dl_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            f.write(chunk)
                    if os.path.exists(dl_path) and os.path.getsize(dl_path) > 1000:
                        print(f"✅ [Telegram Service] Video başarıyla indirildi: {dl_path}")
                        item["video_path"] = dl_path
                        return dl_path
        except Exception as e_dl:
            print(f"[Telegram Service] ❌ Video indirme hatası: {e_dl}")
    return v_path

def handle_callback_query(cq: dict):
    cq_id = cq.get("id")
    data = cq.get("data", "")
    message = cq.get("message", {})
    msg_id = message.get("message_id")
    chat_id = message.get("chat", {}).get("id")

    if data == "test_btn":
        answer_telegram_callback_query(cq_id, text="✅ Test başarılı! Sistem aktif ve çalışıyor.")
        return

    if data == "cmd_denetle":
        answer_telegram_callback_query(cq_id, text="🔍 Vitrin denetimi arka planda başlatıldı...")
        import threading
        def _run_v():
            try:
                from web_showcase import check_and_update_all_deals_status, load_deals
                res_v = check_and_update_all_deals_status()
                changed = res_v.get("updated", False) if isinstance(res_v, dict) else bool(res_v)
                deals = load_deals()
                act = sum(1 for d in deals if not d.get("is_expired", False))
                exp = len(deals) - act
                send_telegram_text(
                    chat_id,
                    f"✅ <b>Canlı Vitrin Denetimi Tamamlandı!</b>\n\n"
                    f"• 🟢 Aktif Fırsat: <b>{act}</b>\n"
                    f"• 🔴 Tükendi / İndirimi Bitti: <b>{exp}</b>\n"
                    f"• 🔄 Durumu Güncellenen: <b>{'Evet (GitHub Pages Güncellendi)' if changed else 'Değişiklik Yok (Tümü Güncel)'}</b>"
                )
            except Exception as ev:
                send_telegram_text(chat_id, f"❌ Vitrin denetim hatası: {ev}")
        threading.Thread(target=_run_v, daemon=True).start()
        return

    # Örn: approve_ig:deal_1791946000
    action, _, deal_id = data.partition(":")
    pending = load_pending_deals()
    item = pending.get(deal_id)

    # Buluttan yeni bir fırsat push edilmiş olabilir, bulamazsa git rebase çekip tekrar dene
    if not item:
        try:
            from config import safe_run_subprocess
            safe_run_subprocess(["git", "pull", "--rebase", "origin", "main"], timeout=15, capture_output=True)
            pending = load_pending_deals()
            item = pending.get(deal_id)
        except Exception:
            pass

    if not item:
        answer_telegram_callback_query(cq_id, text="⚠️ Fırsat kaydı bulunamadı veya süresi doldu.", show_alert=True)
        return

    deal = item.get("deal", {})
    title = deal.get("title", "Fırsat")
    caption_text = item.get("caption_text", "")
    product_url = item.get("product_url", "") or deal.get("affiliate_url", "")
    target_video = ensure_local_video(item)

    # Yardımcı: %100 Organik Instagram Stüdyo Paketi Gönderici (Sıfır Bot İzi / Telefona Hazır Paket)
    def _deliver_ig_studio_package():
        import html as _html
        story_img = item.get("story_image_path")
        if not (story_img and os.path.exists(story_img)):
            try:
                from story_composer import create_story_card
                story_img = create_story_card(deal)
            except Exception as es:
                print(f"[Telegram Service] Story kartı üretilemedi: {es}")
                story_img = None

        # 1. Story görselini fotoğraf olarak gönder (Telefona tek tıkla kaydetmelik)
        if story_img and os.path.exists(story_img):
            try:
                with open(story_img, "rb") as sf:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                        data={
                            "chat_id": chat_id,
                            "caption": (
                                f"📸 <b>1080x1920 HİKAYE (STORY) KARTI HAZIR!</b>\n\n"
                                f"1️⃣ Bu görseli telefonuna kaydet ve Hikayene ekle.\n"
                                f"2️⃣ <b>🗳️ Anket Çıkartması (Etkileşim Hilesi):</b>\n"
                                f"Soru: <i>'Sizce bu fiyata değer mi?'</i>\n"
                                f"Seçenekler: [🔥 Alınır] / [😴 Değmez]\n"
                                f"3️⃣ <b>🔗 Bağlantı (Link) Çıkartması:</b>\n"
                                f"En alttaki kutucuğa dokunup bu linki yapıştır:\n"
                                f"<code>{_html.escape(product_url or '')}</code>"
                            ),
                            "parse_mode": "HTML"
                        },
                        files={"photo": sf},
                        timeout=45
                    )
            except Exception as ep:
                print(f"[Telegram Service] Story fotoğraf gönderim hatası: {ep}")

        # 2. Tek Dokunuşla Kopyalanabilir Reels Açıklaması, İlk Yorum, Story Linki & Görünmez SEO
        clean_words = re.findall(r'\w+', (title or "").lower())
        meaningful_words = [w for w in clean_words if len(w) > 2 and w not in ["ve", "ile", "için", "olan", "cok", "daha", "tl"]]
        base_seo = ["indirim", "fırsat", "kampanya", "amazon", "amazontr", "fırsatürünleri", "ucuzluk", "alışveriş", "reels", "keşfet", "türkiye"]
        category_seo = []
        t_low = (title or "").lower()
        if any(k in t_low for k in ["monitör", "klavye", "mouse", "kulaklık", "gaming", "oyuncu"]):
            category_seo = ["gaming", "oyuncu", "setup", "pcgaming", "oyuncuekipmanı"]
        elif any(k in t_low for k in ["kahve", "termos", "stanley", "airfryer", "mutfak"]):
            category_seo = ["mutfak", "evyaşam", "kahvekeyfi", "çeyiz", "termos", "airfryer"]
        elif any(k in t_low for k in ["şarj", "powerbank", "bluetooth", "kulaklık"]):
            category_seo = ["teknoloji", "kulaklık", "bluetooth", "telefonaksesuar"]
        elif any(k in t_low for k in ["krem", "parfüm", "bakım", "şampuan"]):
            category_seo = ["kişiselbakım", "kozmetik", "ciltbakımı", "güzellik"]

        all_seo = list(dict.fromkeys(meaningful_words[:5] + category_seo + base_seo[:5]))
        seo_str = " ".join(all_seo)

        deal_code_val = deal.get("deal_code", "")
        code_pin_line = f"🔢 Fırsat Kodu: {deal_code_val} (flasfirsat.com.tr arama kutusuna {deal_code_val} yazarak anında bulabilirsiniz!)\n\n" if deal_code_val else ""
        first_comment_str = (
            f"📌 Ürün linki şu an Hikayemizde (Story) ve profilimizdeki sitede (flasfirsat.com.tr) aktif! 24 saat dolmadan Hikayemizden direkt ürüne gidebilirsiniz 👇\n\n"
            f"{code_pin_line}"
            f"Sizce bu fiyata değer mi, alınır mı? Yorumlarda buluşalım!"
        )
        dm_reply_str = (
            f"Selam! 👋 Videomuzdaki {title} için indirimli satın alma linkin burada:\n"
            f"{product_url or 'https://flasfirsat.com.tr'}\n\n"
            f"Flaş fırsatları kaçırmamak için bildirimleri açmayı ve bizi takip etmeyi unutma! ⚡"
        )
        studio_msg = (
            f"📲 <b>%100 ORGANİK INSTAGRAM STÜDYO PAKETİ</b>\n"
            f"<i>(Üzerine bir kez dokunduğunuz metin otomatik kopyalanır)</i>\n\n"
            f"📋 <b>1. REELS AÇIKLAMASI (Dokun & Kopyala):</b>\n"
            f"<code>{_html.escape(caption_text)}</code>\n\n"
            f"💬 <b>2. BAŞA TUTTURULACAK İLK YORUM (Dokun & Kopyala):</b>\n"
            f"<code>{_html.escape(first_comment_str)}</code>\n\n"
            f"🔗 <b>3. HİKAYE (STORY) LİNKİ (Dokun & Kopyala):</b>\n"
            f"<code>{_html.escape(product_url or '')}</code>\n\n"
            f"🔍 <b>4. INSTAGRAM 'Aa' GÖRÜNMEZ SEO KELİMELERİ (Dokun & Kopyala):</b>\n"
            f"<code>{_html.escape(seo_str)}</code>\n\n"
            f"📩 <b>5. 'LİNK' YAZANLARA ATILACAK DM CEVABI (Dokun & Kopyala):</b>\n"
            f"<code>{_html.escape(dm_reply_str)}</code>\n\n"
            f"💡 <b>Keşfet Taktikleri:</b>\n"
            f"1️⃣ <b>Trend Ses:</b> Reels'e popüler bir müziği <b>%2 ses</b> seviyesinde ekle.\n"
            f"2️⃣ <b>Görünmez SEO:</b> 4. kutudaki kelimeleri Instagram'ın 'Aa' metin aracına yapıştır, ekranın köşesine küçültüp gizle!\n"
            f"3️⃣ <b>Hikaye:</b> Gönderilen Story kartını paylaşıp anket çıkartması ve link çıkartması ekle.\n"
            f"4️⃣ <b>Auto-DM:</b> Yoruma 'LİNK' yazanlara 5. kutudaki metni tek dokunuşla yapıştırıp göndererek doğrudan takipçiye dönüştür!"
        )
        send_telegram_text(chat_id, studio_msg)
        return True

    # 0) TÜM PLATFORMLARA YAYINLA (approve_all)
    if action == "approve_all":
        answer_telegram_callback_query(cq_id, text="🚀 Tüm platformlara yayın ve IG Stüdyo Paketi hazırlanıyor...")
        edit_telegram_message_caption(chat_id, msg_id, f"⏳ <b>Tüm Platformlara Dağıtılıyor...</b>\n\n📦 {title}\nYouTube, Telegram, Web Vitrini ve Organik IG Paketi hazırlanıyor...")

        statuses = []
        yt_url = None

        # 1. YouTube Shorts
        try:
            from youtube_publisher import publish_shorts_to_youtube
            yt_target = item.get("youtube_video_path")
            yt_upload = yt_target if (yt_target and os.path.exists(yt_target)) else target_video
            yt_desc = caption_text
            if "BİO" not in yt_desc and "bio" not in yt_desc:
                yt_desc = f"👉 İndirim linkine kanal profilimizdeki (BİO) linkten hemen ulaşabilirsiniz! 🌐\n\n{yt_desc}"
            yt_res = publish_shorts_to_youtube(yt_upload, title=title, description=yt_desc)
            if yt_res.get("success"):
                yt_url = yt_res.get("url")
                statuses.append(f"• 📺 YouTube Shorts: <a href=\"{yt_url}\">İzle</a>")
            else:
                statuses.append(f"• 📺 YouTube Shorts: ❌ {yt_res.get('error', 'Hata')}")
        except Exception as ey:
            statuses.append(f"• 📺 YouTube Shorts: ❌ {ey}")

        # 2. Organik Instagram Stüdyo Paketi (Bot Girişi Yok - %0 Ban Riski)
        try:
            _deliver_ig_studio_package()
            statuses.append("• 📲 Instagram Paketi: ✅ Story + Kopyalanabilir Metin Gönderildi")
        except Exception as ei:
            statuses.append(f"• 📲 Instagram Paketi: ❌ {ei}")

        # 3. Telegram Kanalı (channel_only=True: Admin'e mükerrer video gitmesini önler)
        tg_ok = False
        try:
            from telegram_notifier import send_telegram_deal
            tg_ok = send_telegram_deal(target_video, caption_text, product_url=product_url, channel_only=True)
            if tg_ok:
                statuses.append(f"• 📢 Telegram Kanalı: ✅ {TELEGRAM_CHANNEL_ID}")
            else:
                statuses.append("• 📢 Telegram Kanalı: ❌ Hata")
        except Exception as et:
            statuses.append(f"• 📢 Telegram Kanalı: ❌ {et}")

        # 5. Web Vitrini Güncellemesi
        try:
            from web_showcase import add_deal_to_web
            if deal.get("top3_deals"):
                for d in deal["top3_deals"]:
                    add_deal_to_web(d)
                statuses.append("• 🌐 Web Vitrini: ✅ Top 3 Ürünü Eklendi (#1-3 Sıra)")
            else:
                add_deal_to_web(deal)
                statuses.append("• 🌐 Web Vitrini: ✅ Güncellendi (#1 Sıra)")
        except Exception as e_web:
            print(f"[Telegram Service] Web vitrin hatası: {e_web}")

        # 6. Otopilot Geçmiş Kaydı
        try:
            from autopilot_engine import record_autopilot_run
            auto_rec = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "slot": item.get("slot", "Telegram Onaylı Yayın"),
                "success": True,
                "deal": deal,
                "platforms": {
                    "instagram": {"status": "organic_studio_package"},
                    "youtube": {"status": "ok" if yt_url else "error", "url": yt_url or ""},
                    "telegram": {"status": "ok" if tg_ok else "error", "channel": TELEGRAM_CHANNEL_ID}
                }
            }
            record_autopilot_run(auto_rec)
        except Exception as eh:
            print(f"[Telegram Service] autopilot_history kayıt hatası: {eh}")

        # 7. Ürün Geçmiş Kaydı
        try:
            from deal_bot import load_history, save_history, set_last_product, set_last_subtype, get_product_subtype
            history = load_history()
            if deal.get("top3_deals"):
                for d in deal["top3_deals"]:
                    d_sig = d.get("store_url") or d.get("url") or d.get("title")
                    if d_sig:
                        history.add(d_sig)
                save_history(history)
                if deal["top3_deals"]:
                    first_t = deal["top3_deals"][0].get("title", "")
                    set_last_product(first_t)
                    set_last_subtype(get_product_subtype(first_t))
            elif str(deal.get("old_price", "")).strip() != "Çoklu Ürün" and "Top 3" not in str(deal.get("title", "")):
                deal_sig = deal.get("store_url") or deal.get("url") or title
                if deal_sig:
                    history.add(deal_sig)
                    save_history(history)
                set_last_product(title)
                set_last_subtype(get_product_subtype(title))
        except Exception as ed:
            print(f"[Telegram Service] history_deals kayıt hatası: {ed}")

        item["status"] = "published_all"
        save_pending_deals(pending)

        final_caption = (
            f"🎉 <b>RESMİ KANALLARDA YAYINLANDI & IG PAKETİ HAZIR!</b>\n\n"
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

    # A) Organik Instagram Stüdyo Paketi Hazırla (approve_ig)
    if action == "approve_ig":
        answer_telegram_callback_query(cq_id, text="📲 Organik Instagram Stüdyo Paketi gönderiliyor...")

        # Web vitrinine ekle ki profildeki linkte ürün en üstte hazır dursun
        try:
            from web_showcase import add_deal_to_web
            if deal.get("top3_deals"):
                for d in deal["top3_deals"]:
                    add_deal_to_web(d)
            else:
                add_deal_to_web(deal)
        except Exception as e_web:
            print(f"[Telegram Service] Web vitrin hatası: {e_web}")

        _deliver_ig_studio_package()
        item["status"] = "prepared_instagram_organic"
        save_pending_deals(pending)

        new_caption = (
            f"✅ <b>ORGANİK INSTAGRAM PAKETİ GÖNDERİLDİ! 🎉</b>\n\n"
            f"📦 <b>Ürün:</b> {title}\n"
            f"📸 <b>Story Kartı:</b> ✅ Aşağıda gönderildi\n"
            f"📋 <b>Tek Tık Kopyala Metinler:</b> ✅ Aşağıda gönderildi\n"
            f"🌐 <b>Web Vitrini:</b> ✅ Eklendi (#1 Sıra)\n\n"
            f"Diğer kanallara da göndermek ister misiniz?"
        )
        from config import SITE_URL
        markup_buttons = [
            [
                {"text": "📢 Kanala da At (@flasfirsat)", "callback_data": f"approve_ch:{deal_id}"},
                {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
            ]
        ]
        row_links = []
        if product_url:
            row_links.append({"text": "🛒 Ürün Sayfası", "url": product_url})
        row_links.append({"text": "🌐 Web Vitrini", "url": f"{SITE_URL}?utm_source=instagram&utm_medium=reels"})
        markup_buttons.append(row_links)
        markup = {"inline_keyboard": markup_buttons}
        edit_telegram_message_caption(chat_id, msg_id, new_caption, reply_markup=markup)

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

        ch_ok = False
        try:
            if target_video and os.path.exists(target_video):
                with open(target_video, "rb") as vf:
                    c_res = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                        data={"chat_id": target_ch, "caption": ch_caption, "supports_streaming": "true"},
                        files={"video": vf},
                        timeout=120
                    )
                    ch_ok = c_res.json().get("ok", False)
            elif item.get("file_id"):
                c_res = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                    data={"chat_id": target_ch, "video": item["file_id"], "caption": ch_caption, "supports_streaming": "true"},
                    timeout=30
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
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
                        {"text": "📺 YouTube Shorts Paylaş", "callback_data": f"approve_yt:{deal_id}"}
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

        yt_custom_video = item.get("youtube_video_path")
        upload_video = yt_custom_video if (yt_custom_video and os.path.exists(yt_custom_video)) else target_video

        yt_desc = caption_text
        if "BİO" not in yt_desc and "bio" not in yt_desc:
            yt_desc = f"👉 İndirim linkine kanal profilimizdeki (BİO) linkten hemen ulaşabilirsiniz! 🌐\n\n{yt_desc}"

        from youtube_publisher import publish_shorts_to_youtube
        yt_res = publish_shorts_to_youtube(upload_video, title=title, description=yt_desc)

        if yt_res.get("success"):
            yt_url = yt_res.get("url", "")
            item["status"] = "published_youtube"
            save_pending_deals(pending)

            # Web vitrinine ekle
            try:
                from web_showcase import add_deal_to_web
                add_deal_to_web(deal)
            except Exception as e_web:
                print(f"[Telegram Service] Web vitrin hatası: {e_web}")

            # autopilot_history.json kaydet
            try:
                from autopilot_engine import record_autopilot_run
                auto_rec = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "slot": item.get("slot", "Telegram Onaylı YouTube"),
                    "success": True,
                    "deal": deal,
                    "platforms": {
                        "youtube": {"status": "ok", "url": yt_url}
                    }
                }
                record_autopilot_run(auto_rec)
            except Exception as eh:
                print(f"[Telegram Service] autopilot_history kayıt hatası: {eh}")

            # history_deals.json kaydet
            try:
                from deal_bot import load_history, save_history, set_last_product, set_last_subtype, get_product_subtype
                history = load_history()
                deal_sig = deal.get("store_url") or deal.get("url") or title
                if deal_sig:
                    history.add(deal_sig)
                    save_history(history)
                set_last_product(title)
                set_last_subtype(get_product_subtype(title))
            except Exception as ed:
                print(f"[Telegram Service] history_deals kayıt hatası: {ed}")

            updated_caption = (
                f"✅ <b>YOUTUBE SHORTS OLARAK YAYINLANDI! 🎉</b>\n\n"
                f"📦 <b>Ürün:</b> {title}\n"
                f"🔗 <b>Shorts Linki:</b> {yt_url}\n\n"
                f"Diğer platformlar:"
            )
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "🎬 Instagram Reels Paylaş", "callback_data": f"approve_ig:{deal_id}"},
                        {"text": "📢 Kanala At", "callback_data": f"approve_ch:{deal_id}"}
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



    # T) Fiyat Hatası / Acil Stok Modu Aç/Kapa
    elif action == "toggle_urgent":
        is_urgent = not item.get("is_urgent", False)
        item["is_urgent"] = is_urgent
        orig_caption = item.get("orig_caption_text") or item.get("caption_text", "")
        if "orig_caption_text" not in item:
            item["orig_caption_text"] = orig_caption

        if is_urgent:
            urgent_banner = "🚨 DİKKAT: FİYAT HATASI ŞÜPHESİ! Stoklar her an tükenebilir!\n\n"
            if not item["caption_text"].startswith("🚨 DİKKAT: FİYAT HATASI"):
                item["caption_text"] = urgent_banner + item["caption_text"]
            answer_telegram_callback_query(cq_id, text="🚨 Fiyat Hatası Modu AÇILDI! Paylaşım metnine aciliyet uyarısı eklendi.", show_alert=True)
            status_tag = "🚨 <b>[FİYAT HATASI / ACİL MOD AKTİF!]</b>\n\n"
        else:
            item["caption_text"] = item.get("orig_caption_text", item["caption_text"])
            answer_telegram_callback_query(cq_id, text="✅ Normal Fırsat Moduna Döndürüldü.", show_alert=False)
            status_tag = ""

        save_pending_deals(pending)

        # Mesaj önizlemesini güncelle
        deal = item.get("deal", {})
        title = deal.get("title", "Fırsat")
        updated_prev = (
            f"{status_tag}🎬 <b>YENİ FIRSAT ONAY BEKLİYOR!</b>\n\n"
            f"📦 <b>Ürün:</b> {title}\n"
            f"💰 <b>Fiyat:</b> <s>{deal.get('old_price')}</s> ➔ <b>{deal.get('new_price')}</b> ({deal.get('discount_pct')})\n"
        )
        if deal.get("net_cost"):
            updated_prev += f"💳 <b>Net:</b> {deal.get('net_cost')} ({deal.get('bank_campaign')})\n"
        updated_prev += f"🏪 <b>Mağaza:</b> {deal.get('store_name', 'Amazon TR')}\n\n"
        updated_prev += "👇 <i>Yayınlamak istediğiniz platformu seçin:</i>"

        try:
            curr_markup = message.get("reply_markup")
            edit_telegram_message_caption(chat_id, msg_id, updated_prev, reply_markup=curr_markup)
        except Exception:
            pass
        return

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
            "• <code>/otopilot</code> - Hemen en sıcak indirimi bulup video ve onay butonlarını hazırla\n"
            "• <code>/durum</code> veya <code>/program</code> - Video üretim modunu ve durumunu gösterir\n"
            "• <code>/takip [link]</code> - Ürünü fiyat takibine alır\n"
            "• <code>/listem</code> - Takip ettiğin ürünleri listeler\n"
            "• <code>/stats</code> - Web vitrini ve etkileşim analizlerini gösterir\n"
            "• <code>/yardim</code> - Kullanım rehberi"
        )
        send_telegram_text(chat_id, welcome)
        return

    # 1.5 /program, /durum veya /zamanlayici Komutu
    if text.startswith("/program") or text.startswith("/zamanlayici") or text.startswith("/durum"):
        prog_msg = (
            "🎯 <b>VİDEO ÜRETİM MODU: SADECE SEN İSTEYİNCE (İSTEĞE BAĞLI)</b> 🛑\n\n"
            "Tüm otomatik video üretimleri ve arka plan zamanlayıcıları (bulut ve yerel) tamamen kapatıldı.\n"
            "Sistem siz talimat vermediğiniz sürece asla kendi kendine video üretmez.\n\n"
            "🎬 <b>Nasıl Video Ürettirebilirsiniz?</b>\n"
            "1. <b>Fırsat Avı Başlatmak İçin:</b> Buraya <code>/otopilot</code> yazın. Sistem anında en sıcak indirimi bulup onayınıza sunar.\n"
            "2. <b>Belirli Bir Ürün İçin:</b> Bir Amazon linkini doğrudan buraya gönderin, linke özel video hazırlansın.\n"
            "3. <b>AI Asistanına Söyleyerek:</b> Sohbette 'şimdi üret' veya 'video üret' demeniz yeterlidir.\n\n"
            "✨ <i>Üretilen her video önce Telegram'a onay butonlarıyla gelir; onay vermeden hiçbir yerde yayınlanmaz.</i>"
        )
        send_telegram_text(chat_id, prog_msg)
        return

    # 1.6 /otopilot Komutu (Hemen Tek Tıkla Döngü Başlat)
    if text.startswith("/otopilot"):
        is_force = ("zorla" in text.lower() or "force" in text.lower())
        send_telegram_text(chat_id, "🚀 <b>Otopilot döngüsü başlatıldı!</b>\n\nEn iyi indirim avlanıyor, dikey viral video üretiliyor ve YouTube Shorts, Instagram ve Telegram kanallarına otomatik dağıtılıyor. İşlem tamamlandığında rapor iletilecektir...")
        import threading
        def _run_auto():
            try:
                from autopilot_engine import run_autopilot_deal_cycle
                res = run_autopilot_deal_cycle(dry_run=False, slot_name="Telegram Manuel Tetikleme", force=is_force)
                if res.get("skipped"):
                    send_telegram_text(chat_id, f"ℹ️ {res.get('error') or res.get('reason')}")
            except Exception as ex:
                send_telegram_text(chat_id, f"❌ Otopilot hatası: {ex}")
        threading.Thread(target=_run_auto, daemon=True).start()
        return

    # 1.7 /dm Komutu (Instagram Yorumlarını Tara ve DM Gönder)
    if text.startswith("/dm") or text.startswith("/autodm"):
        send_telegram_text(chat_id, "🔍 <b>Instagram Reels yorumları taranıyor...</b>\n\n'LİNK', 'FİYAT' yazan takipçilere DM ile doğrudan ürün linkleri gönderiliyor...")
        import threading
        def _run_dm():
            try:
                from instagram_auto_dm import check_and_reply_comments
                count = check_and_reply_comments()
                send_telegram_text(chat_id, f"✅ <b>Auto-DM Tamamlandı!</b>\nToplam <b>{count}</b> takipçiye link DM ile iletildi.")
            except Exception as ex:
                send_telegram_text(chat_id, f"❌ Auto-DM hatası: {ex}")
        threading.Thread(target=_run_dm, daemon=True).start()
        return

    # 1.8 /top3 Komutu (Durduruldu - Tekli Video Modu Aktif)
    if text.startswith("/top3"):
        send_telegram_text(
            chat_id,
            "ℹ️ <b>Top 3 Üretimi Durduruldu!</b>\n\n"
            "Sistem tercihinize göre <b>sadece tekli video</b> üretecek şekilde ayarlandı.\n\n"
            "🚀 Hemen tekli viral video üretmek için <code>/otopilot</code> komutunu gönderebilirsiniz!"
        )
        return

    # 2. /yardim Komutu
    if text.startswith("/yardim"):
        help_text = (
            "ℹ️ <b>Fırsat Avcısı & Otopilot Rehberi</b>\n\n"
            "🤖 <b>24/7 Otopilot Yayın Sistemi:</b>\n"
            "Sistem her gün <b>12:30</b>, <b>16:30</b> ve <b>20:00</b> saatlerinde en iyi indirimi otomatik bulur, 9:16 reels videosunu derler ve tüm sosyal medya platformlarınıza eş zamanlı iletir!\n\n"
            "💡 <b>Yönetim Komutları:</b>\n"
            "• <code>/otopilot</code> - Hemen otomatik tekli video üret ve onaya sun\n"
            "• <code>/program</code> - Sıradaki otomatik yayın zamanı\n"
            "• <code>/dm</code> - Instagram Reels yorumlarını tara ve link isteyenlere Auto-DM at\n"
            "• <code>/stats</code> - Web paneli ve ziyaretçi istatistikleri\n"
            "• <code>/denetle</code> - Canlı vitrin stok ve fiyat kontrolü\n"
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

    # 3.5 /stats, /web veya /rapor Komutu
    if text.startswith("/stats") or text.startswith("/web") or text.startswith("/rapor"):
        from web_showcase import load_deals
        from config import SITE_URL, GA_MEASUREMENT_ID
        deals = load_deals()
        active_cnt = sum(1 for d in deals if not d.get("is_expired", False))
        expired_cnt = len(deals) - active_cnt
        amazon_cnt = sum(1 for d in deals if "amazon" in d.get("store_name", "").lower())
        trendyol_cnt = sum(1 for d in deals if "trendyol" in d.get("store_name", "").lower())
        hb_cnt = sum(1 for d in deals if "hepsi" in d.get("store_name", "").lower())
        other_cnt = len(deals) - (amazon_cnt + trendyol_cnt + hb_cnt)
        latest_code = deals[0].get("deal_code", "#101") if deals else "#101"

        ga_status = f"🟢 Aktif (<code>{GA_MEASUREMENT_ID}</code>)" if GA_MEASUREMENT_ID else "🟡 Yerel Telemetri (Tarayıcı İçi)"

        import re
        from config import TEMP_DIR
        discounts = []
        for d in deals:
            pct_s = str(d.get("discount_pct", ""))
            m = re.search(r"(\d+)", pct_s)
            if m:
                discounts.append(int(m.group(1)))
        avg_disc = int(sum(discounts) / len(discounts)) if discounts else 0

        temp_mb = 0.0
        if os.path.exists(TEMP_DIR):
            temp_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, _, files in os.walk(TEMP_DIR) for f in files)
            temp_mb = temp_bytes / (1024 * 1024)

        stats_msg = (
            f"📊 <b>FLAŞ FIRSAT YÖNETİCİ & VİTRİN RAPORU</b> ⚡\n\n"
            f"🌐 <b>Resmi Domain:</b> {SITE_URL}\n"
            f"📦 <b>Toplam Vitrin Ürünü:</b> {len(deals)} adet (🟢 {active_cnt} Aktif / 🔴 {expired_cnt} Tükendi)\n"
            f"🔥 <b>Ortalama İndirim Oranı:</b> %{avg_disc}\n"
            f"🔢 <b>Son Atanan Fırsat Kodu:</b> <code>{latest_code}</code>\n"
            f"💾 <b>Geçici Depolama (Temp):</b> {temp_mb:.1f} MB (Oto-temizleme: 2 gün)\n"
            f"📱 <b>Video Cihaz İzi:</b> Xiaomi Redmi Note 11 Pro (Android 13)\n\n"
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
            f"💡 <i>Vitrin stoklarını hemen canlı denetlemek için aşağıdaki butona basın veya <code>/denetle</code> yazın.</i>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "🔍 Vitrini Canlı Denetle", "callback_data": "cmd_denetle"}],
                [{"text": "📊 Canlı Web Panelini Aç (Yönetici)", "url": f"{SITE_URL}?admin=flas"}]
            ]
        }
        send_telegram_text(chat_id, stats_msg, reply_markup=markup)
        return

    # 3.6 /denetle Komutu (Canlı Vitrin Stok ve Fiyat Denetimi)
    if text.startswith("/denetle"):
        send_telegram_text(chat_id, "🔍 <b>Canlı Vitrin Stok & Fiyat Denetimi Başlatıldı!</b>\n\nflasfirsat.com.tr üzerindeki tüm ürünler tek tek kontrol ediliyor, tükenen veya indirimi bitenler işaretleniyor...")
        import threading
        def _run_verify():
            try:
                from web_showcase import check_and_update_all_deals_status, load_deals
                res_v = check_and_update_all_deals_status()
                changed = res_v.get("updated", False) if isinstance(res_v, dict) else bool(res_v)
                deals = load_deals()
                act = sum(1 for d in deals if not d.get("is_expired", False))
                exp = len(deals) - act
                send_telegram_text(
                    chat_id,
                    f"✅ <b>Canlı Vitrin Denetimi Tamamlandı!</b>\n\n"
                    f"• 🟢 Aktif Fırsat: <b>{act}</b>\n"
                    f"• 🔴 Tükendi / İndirimi Bitti: <b>{exp}</b>\n"
                    f"• 🔄 Durumu Güncellenen: <b>{'Evet (GitHub Pages Güncellendi)' if changed else 'Değişiklik Yok (Tümü Güncel)'}</b>"
                )
            except Exception as ev:
                send_telegram_text(chat_id, f"❌ Vitrin denetim hatası: {ev}")
        threading.Thread(target=_run_verify, daemon=True).start()
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
    print("🤖 [TELEGRAM İNTERAKTİF YÖNETİM & STÜDYO SERVİSİ BAŞLADI]")
    print("• Video Üretim Modu: %100 İSTEĞE BAĞLI (Otomatik zamanlayıcılar kapalı)")
    print("• Yönetici Onay Butonları: Aktif (YouTube, Kanal, Web, Organik IG Paketi)")
    print("• Instagram Modu: %100 Organik Stüdyo (Bot Girişi Kapalı - Sıfır Ban Riski)")
    print("• Kişisel Fiyat Takip Botu (/takip, /listem): Aktif")
    print("• Tetikleme: Sadece siz isteyince (/otopilot veya link atarak)")
    print("Durdurmak için Ctrl+C basabilirsiniz.")
    print("=======================================================\n")
    print("🛑 [OTOMATİK ZAMANLAYICILAR KAPALI] Bulut ve yerel tüm otomatik döngüler kaldırıldı.")
    print("🎬 [İSTEĞE BAĞLI MOD] Video üretimi yalnızca siz talimat verdiğinizde başlar.\n")

    # Başlangıçta eski temp dosyalarını temizle
    try:
        from config import clean_temp_files
        clean_temp_files(max_age_days=2)
    except Exception as e_tc:
        print(f"[Telegram Service] Başlangıç temp temizleme uyarısı: {e_tc}")

    offset = None
    last_alarm_check = time.time()
    last_vitrin_check = time.time()
    last_temp_clean = time.time()

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

            # 3 saatte bir Web Vitrini (flasfirsat.com.tr) canlı stok/fiyat denetimi yap
            if time.time() - last_vitrin_check > 10800:
                print("[Telegram Service] 🌐 3 Saatlik Otomatik Vitrin Stok & Fiyat Denetimi başlatılıyor...")
                try:
                    from web_showcase import check_and_update_all_deals_status
                    check_and_update_all_deals_status()
                except Exception as evc:
                    print(f"[Telegram Service] Vitrin stok denetim uyarısı: {evc}")
                last_vitrin_check = time.time()

            # 24 saatte bir temp/ klasörü otomatik temizliği yap
            if time.time() - last_temp_clean > 86400:
                print("[Telegram Service] 🧹 Günlük temp/ otomatik temizliği yapılıyor...")
                try:
                    from config import clean_temp_files
                    clean_temp_files(max_age_days=2)
                except Exception as etc:
                    print(f"[Telegram Service] Temp temizleme uyarısı: {etc}")
                last_temp_clean = time.time()

        except requests.exceptions.RequestException:
            time.sleep(3)
        except Exception as e:
            print(f"[Telegram Service] Döngü hatası: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_telegram_service()
