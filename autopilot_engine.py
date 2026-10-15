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

        # 2. Videoyu ve İçerikleri Üret (En yüksek indirimden başlayarak geçerli bir aday bulunana kadar tara)
        print(f"\n[Adım 2/4] 🎬 Split-screen viral video ve açıklama hazırlanıyor ({len(candidates)} aday taranacak)...")
        from deal_bot import process_deal_to_reel

        deal = None
        title = None
        prod_res = None

        for idx, cand in enumerate(candidates, 1):
            cand_title = cand.get("title", "Fırsat")
            cand_pct = get_deal_discount_pct(cand)
            print(f"\n👉 Aday {idx}/{len(candidates)} deneniyor: {cand_title} (-%{cand_pct})...")
            p_res = process_deal_to_reel(
                deal=cand,
                upload=False,
                require_approval=False
            )
            if p_res and p_res.get("video_path"):
                prod_res = p_res
                deal = cand
                title = cand_title
                print(f"🎉 Aday {idx} başarıyla doğrulandı ve video hazırlandı: {title}")
                break
            else:
                print(f"⏭️ Aday {idx} elendi / doğrulanamadı. Sıradaki adaya geçiliyor...")

        if not prod_res or not prod_res.get("video_path") or not deal:
            err = f"Aday fırsatların hiçbiri doğrulanamadı veya video üretilemedi ({len(candidates)} aday test edildi)."
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

        # B2) Instagram Story (Tıklanabilir Link Çıkartması ile)
        print("\n--- 2b. Instagram Story (Tıklanabilir Link Çıkartması) ---")
        try:
            from story_composer import create_story_card
            from instagram_publisher import publish_story_with_link
            story_img = create_story_card(deal)
            st_res = publish_story_with_link(story_img, link_url=aff_url)
            if st_res.get("success"):
                result["platforms"]["instagram_story"] = {"status": "ok", "media_id": st_res.get("media_id")}
                print(f"✅ Instagram Story Başarılı (Link Çıkartmalı)! ID: {st_res.get('media_id')}")
            else:
                result["platforms"]["instagram_story"] = {"status": "error", "error": st_res.get("error")}
                print(f"❌ Instagram Story Hatası: {st_res.get('error')}")
        except Exception as es:
            result["platforms"]["instagram_story"] = {"status": "error", "error": str(es)}
            print(f"❌ Instagram Story İstisna: {es}")

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

        # Instagram Story
        st_info = result["platforms"].get("instagram_story", {})
        if st_info.get("status") == "ok":
            status_lines.append(f"• 📸 <b>Instagram Story:</b> ✅ Link Çıkartmalı Hikaye Yayında")
        elif "instagram_story" in result["platforms"]:
            status_lines.append(f"• 📸 <b>Instagram Story:</b> ❌ {st_info.get('error', 'Hata')}")

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
        # Fırsatı geçmiş listesine ekle (Sonraki döngülerde aynı ürünün tekrar seçilmesini önler)
        try:
            from deal_bot import save_history, set_last_product, set_last_subtype, get_product_subtype
            deal_sig = deal.get("store_url") or deal.get("url") or title
            if deal_sig:
                history.add(deal_sig)
                save_history(history)
            set_last_product(title)
            set_last_subtype(get_product_subtype(title))
            print(f"[Autopilot Engine] 💾 Ürün geçmiş listesine işlendi ({len(history)} ürün).")
        except Exception as eh:
            print(f"[Autopilot Engine] ⚠️ Geçmiş kaydedilemedi: {eh}")

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

def run_top3_deal_cycle(dry_run: bool = False, slot_name: str = "Haftalık Top 3 Bülteni") -> dict:
    """
    Haftalık veya özel istek üzerine çalışan Top 3 Fırsat Otopilotu:
    1. En yüksek indirimli ve teyitli 3 farklı alt kategorideki ürünü avlar.
    2. 1080x1920 dikey kesintisiz viral meme + 3 slaytlı Top 3 videosunu derler.
    3. 4 platforma (YouTube Shorts, Instagram Reels, Telegram, WhatsApp) yayınlar.
    4. Web vitrinine ekler ve yöneticiye detaylı rapor iletir.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*65)
    print(f"🏆 [TOP 3 OTOPİLOTU BAŞLATILDI] Kuşak: {slot_name} | Zaman: {now_str}")
    print("="*65)

    result = {
        "timestamp": now_str,
        "slot": slot_name,
        "type": "top3",
        "success": False,
        "platforms": {},
        "error": None
    }

    try:
        from deal_hunter import hunt_best_deals, get_deal_discount_pct, get_deal_savings_tl, get_product_subtype
        from product_verifier import verify_and_enrich_product
        from top3_composer import build_top3_video, generate_top3_caption
        from deal_bot import load_history, save_history, get_affiliate_url

        history = load_history()
        candidates = hunt_best_deals(
            limit=12,
            platform="all",
            category="all",
            exclude_urls=history,
            min_discount=20
        )

        if len(candidates) < 3:
            candidates = hunt_best_deals(limit=12, platform="all", category="all", min_discount=15)

        candidates.sort(key=lambda d: (get_deal_discount_pct(d), get_deal_savings_tl(d)), reverse=True)

        top3_deals = []
        seen_subtypes = set()

        for c in candidates:
            if len(top3_deals) >= 3:
                break
            sub = get_product_subtype(c.get("title", ""))
            if sub != "general" and sub in seen_subtypes:
                continue

            v_deal = verify_and_enrich_product(c)
            if v_deal and v_deal.get("image_path") and os.path.exists(v_deal["image_path"]):
                raw_u = v_deal.get("store_url") or v_deal.get("url") or ""
                aff_u = get_affiliate_url(raw_u, v_deal.get("store_name", ""))
                v_deal["affiliate_url"] = aff_u
                top3_deals.append(v_deal)
                if sub != "general":
                    seen_subtypes.add(sub)
                print(f"✅ Top 3 Adayı Seçildi (#{len(top3_deals)}): {v_deal.get('title')[:40]} (-%{get_deal_discount_pct(v_deal)})")

        if len(top3_deals) < 3:
            err = f"Top 3 videosu için yeterli teyitli aday toplanamadı ({len(top3_deals)}/3 aday bulundu)."
            print(f"[Top3 Engine] ❌ {err}")
            send_telegram_admin_summary(f"⚠️ <b>[TOP 3 OTOPİLOT UYARISI]</b>\nKuşak: {slot_name}\n\n{err}")
            result["error"] = err
            record_autopilot_run(result)
            return result

        ts = int(time.time())
        video_filename = f"top3_weekly_{ts}.mp4"
        print(f"\n🎬 Top 3 videosu derleniyor: {video_filename}...")
        video_path = build_top3_video(top3_deals, output_filename=video_filename)
        caption_text = generate_top3_caption(top3_deals)

        if dry_run:
            print("\n[Top3 Engine] 🧪 DRY-RUN Aktif: Yayınlama adımları atlandı.")
            result["success"] = True
            result["dry_run"] = True
            result["video_path"] = video_path
            record_autopilot_run(result)
            return result

        print("\n📡 Top 3 Videosu Platformlara Dağıtılıyor...")

        # YouTube Shorts
        try:
            from youtube_publisher import publish_shorts_to_youtube
            yt_res = publish_shorts_to_youtube(video_path, title="Haftanın En İyi 3 Fırsatı 🔥", description=caption_text)
            if yt_res.get("success"):
                result["platforms"]["youtube"] = {"status": "ok", "url": yt_res.get("url")}
            else:
                result["platforms"]["youtube"] = {"status": "error", "error": yt_res.get("error")}
        except Exception as ey:
            result["platforms"]["youtube"] = {"status": "error", "error": str(ey)}

        # Instagram Reels
        try:
            from instagram_publisher import publish_reel_to_instagram
            ig_res = publish_reel_to_instagram(video_path, caption_text)
            if ig_res.get("success"):
                result["platforms"]["instagram"] = {"status": "ok", "media_id": ig_res.get("media_id")}
            else:
                result["platforms"]["instagram"] = {"status": "error", "error": ig_res.get("error")}
        except Exception as ei:
            result["platforms"]["instagram"] = {"status": "error", "error": str(ei)}

        # Telegram Kanalı
        try:
            from telegram_notifier import send_telegram_deal
            tg_ok = send_telegram_deal(video_path, caption_text, product_url=top3_deals[0].get("affiliate_url"))
            if tg_ok:
                result["platforms"]["telegram"] = {"status": "ok", "channel": TELEGRAM_CHANNEL_ID}
            else:
                result["platforms"]["telegram"] = {"status": "error", "error": "Telegram kanala gönderilemedi"}
        except Exception as et:
            result["platforms"]["telegram"] = {"status": "error", "error": str(et)}

        # Web Vitrinine 3 Ürünü de Ekle
        try:
            from web_showcase import add_deal_to_web
            for d in top3_deals:
                add_deal_to_web(d)
            result["platforms"]["web"] = {"status": "ok", "url": SITE_URL}
        except Exception as ewb:
            result["platforms"]["web"] = {"status": "error", "error": str(ewb)}

        for d in top3_deals:
            sig = d.get("store_url") or d.get("url") or d.get("title")
            if sig:
                history.add(sig)
        save_history(history)

        result["success"] = True
        summary_msg = (
            f"🏆 <b>TOP 3 HAFTALIK BÜLTEN YAYINLANDI!</b> 🚀\n"
            f"⏰ <b>Kuşak:</b> {slot_name}\n\n"
            f"🥇 #1: {top3_deals[0].get('title')[:35]} ({top3_deals[0].get('new_price')})\n"
            f"🥈 #2: {top3_deals[1].get('title')[:35]} ({top3_deals[1].get('new_price')})\n"
            f"🥉 #3: {top3_deals[2].get('title')[:35]} ({top3_deals[2].get('new_price')})\n\n"
            f"• 📺 YouTube Shorts: {'✅ Yayında' if result['platforms'].get('youtube', {}).get('status') == 'ok' else '❌ Hata'}\n"
            f"• 🎬 Instagram Reels: {'✅ Yayında' if result['platforms'].get('instagram', {}).get('status') == 'ok' else '❌ Hata'}\n"
            f"• 📢 Telegram: {'✅ Yayında' if result['platforms'].get('telegram', {}).get('status') == 'ok' else '❌ Hata'}\n"
            f"• 🌐 Web Vitrini: ✅ 3 Ürün Eklendi"
        )
        send_telegram_admin_summary(summary_msg)
        record_autopilot_run(result)
        print("\n🎉 [TOP 3] Bülten yayını başarıyla tamamlandı!")
        return result

    except Exception as e:
        err = f"Top 3 otopilot hatası: {e}\n{traceback.format_exc()}"
        print(f"[Top3 Engine] ❌ {err}")
        send_telegram_admin_summary(f"🚨 <b>[TOP 3 OTOPİLOT HATASI]</b>\nKuşak: {slot_name}\n\n<code>{str(e)}</code>")
        result["error"] = str(e)
        record_autopilot_run(result)
        return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flaş Fırsat Otopilot Yayın Motoru")
    parser.add_argument("--now", action="store_true", help="Hemen bir otopilot döngüsü çalıştır")
    parser.add_argument("--top3", action="store_true", help="Top 3 haftalık fırsat bülteni videosu üret ve yayınla")
    parser.add_argument("--dry-run", action="store_true", help="Gerçek yükleme yapmadan video ve metni test et")
    parser.add_argument("--slot", default="Manuel Test", help="Kuşak adı")
    args = parser.parse_args()

    if args.top3:
        run_top3_deal_cycle(dry_run=args.dry_run, slot_name=args.slot)
    elif args.now or args.dry_run:
        run_autopilot_deal_cycle(dry_run=args.dry_run, slot_name=args.slot)
    else:
        print("Kullanım: python autopilot_engine.py --now (veya --top3, --dry-run)")
