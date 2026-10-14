import os
import sys
import time
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

from config import (
    BASE_DIR,
    DATA_DIR,
    SITE_URL
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@flasfirsat").strip()
AUTOPILOT_LOG_FILE = os.path.join(DATA_DIR, "autopilot_history.json")

def load_autopilot_history() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(AUTOPILOT_LOG_FILE):
        try:
            with open(AUTOPILOT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def record_autopilot_run(record: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    history = load_autopilot_history()
    history.append(record)
    try:
        with open(AUTOPILOT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Autopilot Engine] Geçmiş kaydedilemedi: {e}")

def send_telegram_admin_summary(summary_text: str, reply_markup: dict = None):
    """Yöneticiye Telegram üzerinden özet raporu gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": summary_text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"[Autopilot Engine] Telegram özet gönderim hatası: {e}")

def run_autopilot_deal_cycle(dry_run: bool = False, slot_name: str = "Manuel") -> dict:
    """
    En algoritmik 2 saatte (12:30 ve 20:00) veya isteğe bağlı çalışan tam otomatik döngü:
    1. En yüksek indirimli ve teyitli ürünü avlar (Amazon TR / Fırsat Kanalları).
    2. 9:16 dikey split-screen viral videoyu (meme + banner) ve viral metni üretir.
    3. Sırasıyla 4 platforma doğrudan yayınlar:
       - YouTube Shorts
       - Instagram Reels
       - Telegram Kanalı (@flasfirsat)
       - WhatsApp Kanalı (Flaş Fırsat ⚡)
       - Web Vitrini (index.html / deals.json)
    4. Yönetici Telegram hesabına anlık başarı raporu iletir.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*65)
    print(f"🚀 [OTOPİLOT BAŞLATILDI] Kuşak: {slot_name} | Zaman: {now_str}")
    print("="*65)

    result = {
        "timestamp": now_str,
        "slot": slot_name,
        "success": False,
        "platforms": {},
        "error": None
    }

    try:
        # 1. En iyi fırsatı tara
        print("\n[Adım 1/4] 🔍 En yüksek indirimli taze fırsat avlanıyor...")
        from deal_hunter import hunt_best_deals, get_product_subtype
        from deal_bot import load_history, get_last_subtype

        history = load_history()
        last_sub = get_last_subtype()
        exclude_subs = {last_sub} if (last_sub and last_sub != "general") else None

        candidates = hunt_best_deals(
            limit=5,
            platform="amazon",
            category="all",
            exclude_urls=history,
            exclude_subtypes=exclude_subs,
            min_discount=25
        )

        if not candidates:
            print("[Autopilot Engine] ⚠️ %25 üzeri taze Amazon fırsatı bulunamadı. Genel kanallara bakılıyor...")
            candidates = hunt_best_deals(
                limit=5,
                platform="all",
                category="all",
                exclude_urls=history,
                min_discount=20
            )

        if not candidates:
            err = "Uygun kriterde (yeterli indirim ve stok) fırsat ürünü bulunamadı."
            print(f"[Autopilot Engine] ❌ {err}")
            send_telegram_admin_summary(f"⚠️ <b>[OTOPİLOT UYARISI]</b>\nKuşak: {slot_name}\n\n{err}")
            result["error"] = err
            record_autopilot_run(result)
            return result

        # En yüksek indirim oranına (%40, %50 vb.) ve net TL kârına göre kesin sıralama yap
        from deal_hunter import get_deal_discount_pct, get_deal_savings_tl
        candidates.sort(key=lambda d: (get_deal_discount_pct(d), get_deal_savings_tl(d)), reverse=True)

        deal = candidates[0]
        title = deal.get("title", "Fırsat")
        pct = get_deal_discount_pct(deal)
        print(f"🎯 Seçilen En Yüksek İndirimli Ürün: {title} (-%{pct})")
        print(f"💰 İndirim:     {deal.get('old_price')} ➔ {deal.get('new_price')} ({deal.get('discount_pct')})")

        # 2. Videoyu ve İçerikleri Üret
        print("\n[Adım 2/4] 🎬 Split-screen viral video ve açıklama hazırlanıyor...")
        from deal_bot import process_deal_to_reel

        prod_res = process_deal_to_reel(
            deal=deal,
            upload=False,
            require_approval=False
        )

        if not prod_res or not prod_res.get("video_path"):
            err = f"Video üretimi veya ürün doğrulaması başarısız oldu ({title})."
            print(f"[Autopilot Engine] ❌ {err}")
            send_telegram_admin_summary(f"⚠️ <b>[OTOPİLOT UYARISI]</b>\nKuşak: {slot_name}\n\n{err}")
            result["error"] = err
            record_autopilot_run(result)
            return result

        video_path = prod_res["video_path"]
        caption_text = prod_res["caption_text"]
        aff_url = deal.get("affiliate_url") or deal.get("store_url", "")
        result["deal"] = {
            "title": title,
            "new_price": deal.get("new_price"),
            "old_price": deal.get("old_price"),
            "discount_pct": deal.get("discount_pct"),
            "affiliate_url": aff_url
        }

        if dry_run:
            print("\n[Autopilot Engine] 🧪 DRY-RUN Aktif: Yayınlama adımları atlandı.")
            result["success"] = True
            result["dry_run"] = True
            record_autopilot_run(result)
            return result

        # 3. Sırasıyla 4 Platforma Yayınla
        print("\n[Adım 3/4] 📡 4 Platforma Eşzamanlı Otomatik Yayın Başlatılıyor...")

        # A) YouTube Shorts
        print("\n--- 1. YouTube Shorts ---")
        try:
            from youtube_publisher import publish_shorts_to_youtube
            yt_res = publish_shorts_to_youtube(video_path, title=title, description=caption_text)
            if yt_res.get("success"):
                result["platforms"]["youtube"] = {"status": "ok", "url": yt_res.get("url")}
                print(f"✅ YouTube Shorts Başarılı: {yt_res.get('url')}")
            else:
                result["platforms"]["youtube"] = {"status": "error", "error": yt_res.get("error")}
                print(f"❌ YouTube Shorts Hatası: {yt_res.get('error')}")
        except Exception as ey:
            result["platforms"]["youtube"] = {"status": "error", "error": str(ey)}
            print(f"❌ YouTube Shorts İstisna: {ey}")

        # B) Instagram Reels
        print("\n--- 2. Instagram Reels ---")
        try:
            from instagram_publisher import publish_reel_to_instagram
            ig_res = publish_reel_to_instagram(video_path, caption_text)
            if ig_res.get("success"):
                result["platforms"]["instagram"] = {"status": "ok", "media_id": ig_res.get("media_id")}
                print(f"✅ Instagram Reels Başarılı: Media ID {ig_res.get('media_id')}")
            else:
                result["platforms"]["instagram"] = {"status": "error", "error": ig_res.get("error")}
                print(f"❌ Instagram Reels Hatası: {ig_res.get('error')}")
        except Exception as ei:
            result["platforms"]["instagram"] = {"status": "error", "error": str(ei)}
            print(f"❌ Instagram Reels İstisna: {ei}")

        # C) Telegram Kanalı (@flasfirsat)
        print("\n--- 3. Telegram Kanalı ---")
        try:
            from telegram_notifier import send_telegram_deal
            tg_ok = send_telegram_deal(video_path, caption_text, product_url=aff_url)
            if tg_ok:
                result["platforms"]["telegram"] = {"status": "ok", "channel": TELEGRAM_CHANNEL_ID}
                print(f"✅ Telegram Kanalı Başarılı: {TELEGRAM_CHANNEL_ID}")
            else:
                result["platforms"]["telegram"] = {"status": "error", "error": "Telegram kanala gönderilemedi"}
                print("❌ Telegram Kanalı Hatası")
        except Exception as et:
            result["platforms"]["telegram"] = {"status": "error", "error": str(et)}
            print(f"❌ Telegram Kanal İstisna: {et}")

        # D) WhatsApp Kanalı (Flaş Fırsat ⚡)
        print("\n--- 4. WhatsApp Kanalı ---")
        try:
            from whatsapp_publisher import publish_deal_to_whatsapp_channel
            wp_res = publish_deal_to_whatsapp_channel(deal, image_path=deal.get("image_path"))
            if wp_res.get("success"):
                result["platforms"]["whatsapp"] = {"status": "ok", "channel": "Flaş Fırsat ⚡"}
                print("✅ WhatsApp Kanalı Başarılı!")
            else:
                result["platforms"]["whatsapp"] = {"status": "error", "error": wp_res.get("error")}
                print(f"❌ WhatsApp Kanalı Hatası: {wp_res.get('error')}")
        except Exception as ew:
            result["platforms"]["whatsapp"] = {"status": "error", "error": str(ew)}
            print(f"❌ WhatsApp Kanal İstisna: {ew}")

        # E) Web Vitrinine Ekle
        try:
            from web_showcase import add_deal_to_web
            add_deal_to_web(deal)
            result["platforms"]["web"] = {"status": "ok", "url": SITE_URL}
        except Exception as ewb:
            result["platforms"]["web"] = {"status": "error", "error": str(ewb)}

        # 4. Yöneticiye Başarı Raporu Gönder
        print("\n[Adım 4/4] 📲 Yöneticiye Telegram raporu gönderiliyor...")
        result["success"] = True

        status_lines = []
        # YouTube
        yt_info = result["platforms"].get("youtube", {})
        if yt_info.get("status") == "ok":
            status_lines.append(f"• 📺 <b>YouTube Shorts:</b> <a href=\"{yt_info.get('url')}\">İzle</a>")
        else:
            status_lines.append(f"• 📺 <b>YouTube Shorts:</b> ❌ {yt_info.get('error', 'Hata')}")

        # Instagram
        ig_info = result["platforms"].get("instagram", {})
        if ig_info.get("status") == "ok":
            status_lines.append(f"• 🎬 <b>Instagram Reels:</b> ✅ Yayınlandı (@flasfirsat)")
        else:
            status_lines.append(f"• 🎬 <b>Instagram Reels:</b> ❌ {ig_info.get('error', 'Hata')}")

        # Telegram
        tg_info = result["platforms"].get("telegram", {})
        if tg_info.get("status") == "ok":
            status_lines.append(f"• 📢 <b>Telegram Kanalı:</b> ✅ {TELEGRAM_CHANNEL_ID}")
        else:
            status_lines.append(f"• 📢 <b>Telegram Kanalı:</b> ❌ {tg_info.get('error', 'Hata')}")

        # WhatsApp
        wp_info = result["platforms"].get("whatsapp", {})
        if wp_info.get("status") == "ok":
            status_lines.append(f"• 🟢 <b>WhatsApp Kanalı:</b> ✅ Flaş Fırsat ⚡")
        else:
            status_lines.append(f"• 🟢 <b>WhatsApp Kanalı:</b> ❌ {wp_info.get('error', 'Hata')}")

        # Web
        status_lines.append(f"• 🌐 <b>Web Vitrini:</b> <a href=\"{SITE_URL}\">Vitrinde Yayında</a>")

        report_msg = (
            f"🎯 <b>OTOPİLOT YAYINI TAMAMLANDI!</b> 🚀\n"
            f"⏰ <b>Kuşak:</b> {slot_name} ({now_str})\n\n"
            f"📦 <b>Ürün:</b> {title}\n"
            f"💰 <b>Fiyat:</b> <s>{deal.get('old_price')}</s> ➔ <b>{deal.get('new_price')}</b> ({deal.get('discount_pct')})\n"
            f"💳 <b>Net:</b> {deal.get('net_cost')} ({deal.get('bank_campaign')})\n\n"
            f"<b>Platform Durumları:</b>\n" + "\n".join(status_lines)
        )

        markup = {
            "inline_keyboard": [
                [
                    {"text": "🛒 Ürünü Aç", "url": aff_url},
                    {"text": "🌐 Web Vitrini", "url": SITE_URL}
                ]
            ]
        }
        send_telegram_admin_summary(report_msg, reply_markup=markup)

        record_autopilot_run(result)
        print("\n🎉 [OTOPİLOT] Döngü başarıyla tamamlandı ve raporlandı!")
        return result

    except Exception as e:
        err = f"Otopilot genel hatası: {e}\n{traceback.format_exc()}"
        print(f"[Autopilot Engine] ❌ {err}")
        send_telegram_admin_summary(f"🚨 <b>[OTOPİLOT KRİTİK HATA]</b>\nKuşak: {slot_name}\n\n<code>{str(e)}</code>")
        result["error"] = str(e)
        record_autopilot_run(result)
        return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flaş Fırsat Otopilot Yayın Motoru")
    parser.add_argument("--now", action="store_true", help="Hemen bir otopilot döngüsü çalıştır")
    parser.add_argument("--dry-run", action="store_true", help="Gerçek yükleme yapmadan video ve metni test et")
    parser.add_argument("--slot", default="Manuel Test", help="Kuşak adı")
    args = parser.parse_args()

    if args.now or args.dry_run:
        run_autopilot_deal_cycle(dry_run=args.dry_run, slot_name=args.slot)
    else:
        print("Kullanım: python autopilot_engine.py --now (veya --dry-run)")
