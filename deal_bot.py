import os
import sys
import time
import json
import argparse
import random
import datetime
from deal_hunter import hunt_online_deals, hunt_amazon_deals, hunt_best_deals, parse_deal_from_image, parse_deal_from_url, get_product_subtype
from split_composer import create_product_banner, build_split_screen_video, AVAILABLE_MEMES, AVAILABLE_AUDIOS
from top3_composer import build_top3_video, generate_top3_caption
from caption_generator import generate_viral_caption
from telegram_notifier import send_telegram_deal

from affiliate import get_affiliate_url
from web_showcase import add_deal_to_web
from config import BASE_DIR, OUTPUT_DIR, TEMP_DIR

HISTORY_FILE = os.path.join(BASE_DIR, "history_deals.json")
LAST_PRODUCT_FILE = os.path.join(TEMP_DIR, "last_product.txt")
LAST_SUBTYPE_FILE = os.path.join(TEMP_DIR, "last_subtype.txt")

def get_last_product() -> str:
    try:
        if os.path.exists(LAST_PRODUCT_FILE):
            with open(LAST_PRODUCT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def set_last_product(prod_name: str):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(LAST_PRODUCT_FILE, "w", encoding="utf-8") as f:
            f.write(prod_name)
    except Exception:
        pass

def get_last_subtype() -> str:
    try:
        if os.path.exists(LAST_SUBTYPE_FILE):
            with open(LAST_SUBTYPE_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
    except Exception:
        pass
    last_p = get_last_product()
    return get_product_subtype(last_p)

def set_last_subtype(subtype: str):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(LAST_SUBTYPE_FILE, "w", encoding="utf-8") as f:
            f.write(subtype)
    except Exception:
        pass

def load_history() -> set:

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(history: set):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Uyarı] Geçmiş kaydedilemedi: {e}")

def get_deal_sig(deal: dict) -> str:
    return deal.get("store_url") or deal.get("title", "")

def clean_filename(s: str) -> str:
    """Türkçe karakterleri ve geçersiz dosya adı karakterlerini temizler."""
    tr_map = {
        'ı': 'i', 'I': 'I', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for tr, en in tr_map.items():
        s = s.replace(tr, en)
    s = "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in s])
    return "_".join(s.split())[:30].lower()

def process_deal_to_reel(
    deal: dict,
    meme_choice: str = None,
    audio_choice: str = None,
    output_prefix: str = None,
    upload: bool = True
) -> dict:
    """
    Tek bir fırsat nesnesinden (deal dict):
    1. 1080x960 Üst Banner üretir (büyük ürün görseli ve çarpıcı tipografi).
    2. Viral meme ve phonk müzikle 1080x1920 MP4 Video derler.
    3. Gemini ile viral açıklama metni ve hashtag'leri üretir.
    4. Dosyaları output/ klasörüne kaydeder.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = clean_filename(deal.get("title", "firsat"))
    base_name = f"{timestamp}_{slug}" if not output_prefix else f"{output_prefix}_{slug}"

    print(f"\n=======================================================")
    print(f"🎬 [İŞLENİYOR] {deal.get('title')}")
    print(f"💰 Fiyat: {deal.get('old_price')} -> {deal.get('new_price')} ({deal.get('discount_pct')})")
    print(f"=======================================================")

    # 0. Yayın Öncesi Canlı Stok ve Fiyat Doğrulaması
    from product_verifier import verify_deal_before_publish
    v_info = verify_deal_before_publish(deal)
    if not v_info.get("valid", True):
        print(f"[Deal Bot] ⏭️ Fırsat yayına uygun değil ({v_info.get('reason', 'Doğrulanamadı')}). Atlanıyor: {deal.get('title')}")
        return None
    deal = v_info.get("deal", deal)

    # Banka Kampanyası ve Net Maliyet Hesapla
    from campaign_calculator import calculate_campaign_and_net_cost
    camp_info = calculate_campaign_and_net_cost(deal.get("new_price", ""), deal.get("store_name", "Amazon TR"))
    deal["bank_campaign"] = deal.get("bank_campaign") or camp_info["bank_campaign"]
    deal["net_cost"] = deal.get("net_cost") or camp_info["net_cost"]
    deal["installment"] = deal.get("installment") or camp_info.get("installment", "")

    print(f"💳 Banka/Nays Avantajı: {deal['bank_campaign']} -> Net: {deal['net_cost']}")

    # 1. Ürün Banner'ı Üret (DEV İNDİRİM Sabit Şablon)
    banner_temp = os.path.join(TEMP_DIR, f"banner_{base_name}.png")
    print("[1/3] 🎨 Üst banner (1080x960) tasarlanıyor...")
    create_product_banner(
        product_image_path=deal.get("image_path"),
        title=deal.get("title", "Günün Fırsatı"),
        old_price=deal.get("old_price", "Piyasa Fiyatı"),
        new_price=deal.get("new_price", "İndirimde"),
        discount_pct=deal.get("discount_pct", "-40%"),
        badge_text="DEV İNDİRİM",
        store_name=deal.get("store_name", "Amazon TR"),
        bank_campaign=deal.get("bank_campaign", ""),
        net_cost=deal.get("net_cost", ""),
        installment=deal.get("installment", ""),
        feature_text=deal.get("feature_pill", ""),
        is_lowest_30d=deal.get("is_lowest_30d", False),
        output_path=banner_temp
    )

    # 2. Viral Split-Screen Video Derle (Akıllı Meme Eşleştirme - Ard arda aynı meme gelmez)
    video_filename = f"{base_name}.mp4"
    print(f"[2/3] 🎥 Video derleniyor (Split Screen 1080x1920)...")
    video_path = build_split_screen_video(
        top_source=banner_temp,
        meme_name=meme_choice,
        audio_name=audio_choice,
        output_filename=video_filename,
        discount_pct=deal.get("discount_pct", ""),
        product_title=deal.get("title", "")
    )

    # Affiliate Link Dönüşümü
    raw_url = deal.get("store_url", "")
    aff_url = get_affiliate_url(raw_url, deal.get("store_name", ""))
    deal["store_url"] = aff_url
    deal["affiliate_url"] = aff_url

    # 3. Viral Açıklama Metni (Caption) ve Hashtag'ler
    print("[3/3] ✍️ Gemini ile viral açıklama metni ve hashtag'ler yazılıyor...")
    caption_text = generate_viral_caption(
        product_title=deal.get("title", "Fırsat Ürünü"),
        old_price=deal.get("old_price", ""),
        new_price=deal.get("new_price", ""),
        discount_pct=deal.get("discount_pct", ""),
        deal_details=deal.get("hook", ""),
        store_url=aff_url,
        bank_campaign=deal.get("bank_campaign", ""),
        net_cost=deal.get("net_cost", "")
    )

    caption_filename = f"{base_name}_aciklama.txt"
    caption_path = os.path.join(OUTPUT_DIR, caption_filename)
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption_text)

    # Geçmişe kaydet
    sig = get_deal_sig(deal)
    if sig:
        history = load_history()
        history.add(sig)
        save_history(history)
    set_last_product(deal.get("title", ""))
    sub = get_product_subtype(deal.get("title", ""))
    set_last_subtype(sub)

    # 4. Telegram Bildirimi (Telefona Video + Açıklama + Ürün Linki Gönder)
    if upload:
        send_telegram_deal(video_path, caption_text, product_url=aff_url)
    else:
        print("\n[Telegram] ⏸️ Yükleme atlandı (--no-upload aktif). Video ve açıklama sadece yerel olarak hazırlandı.")

    # 5. Web Vitrini Güncelle (Otomatik Web Sayfasına Ekle)
    if upload:
        try:
            add_deal_to_web(deal)
        except Exception as e:
            print(f"[Web] Vitrine ekleme uyarısı: {e}")
    else:
        print("[Web] ⏸️ Web vitrinine ekleme atlandı (--no-upload aktif).")

    # 6. Performans Geri Bildirimi Kaydı
    try:
        from performance_tracker import log_published_deal
        log_published_deal(deal, meme=meme_choice, audio=audio_choice, video_path=video_path)
    except Exception as e:
        print(f"[Performance] Kayıt uyarısı: {e}")

    print("\n✅ [TAMAMLANDI!] Fırsat Paylaşıma Hazır!")
    print(f"📁 Video:    {video_path}")
    print(f"📁 Açıklama: {caption_path}")
    if deal.get("store_url"):
        print(f"🔗 Ürün Linki: {deal.get('store_url')}")
    print("-------------------------------------------------------")
    print(caption_text)
    print("-------------------------------------------------------\n")

    return {
        "video_path": video_path,
        "caption_path": caption_path,
        "caption_text": caption_text,
        "deal": deal
    }

def main():
    parser = argparse.ArgumentParser(
        description="Viral İndirim / Fırsat Video ve İçerik Otomasyonu (Amazon + Trendyol + Hepsiburada)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Kullanım Şekilleri:
  1. En İyi Fırsatı Avla (Amazon, Trendyol, Hepsiburada arasından en iyisini seçer):
     python deal_bot.py --auto
     python deal_bot.py --auto --platform all --count 3

  2. Belirli Bir Platform Seç:
     python deal_bot.py --platform trendyol
     python deal_bot.py --platform hepsiburada
     python deal_bot.py --platform amazon

  3. Full Aktif / Nöbetçi Modu:
     python deal_bot.py --watch --interval 30

  4. Kendi Görsel veya Linkinle:
     python deal_bot.py --image "screenshot.png"
     python deal_bot.py --url "https://www.trendyol.com/..."
        """
    )

    parser.add_argument("--auto", action="store_true", help="Otomatik mod: En iyi fırsatları avla (Amazon, Trendyol, Hepsiburada)")
    parser.add_argument("--platform", type=str, default="amazon", choices=["amazon", "all", "trendyol", "hepsiburada"], help="Taranacak e-ticaret platformu (Varsayılan: amazon)")
    parser.add_argument("--amazon", action="store_true", help="Sadece amazon.com.tr fırsat ve çok satanlar ürünlerini çek")
    parser.add_argument("--category", type=str, default="all", choices=["all", "gaming", "computers", "monitors", "electronics", "kitchen"], help="Ürün kategorisi (Varsayılan: all - otomatik rotasyon)")
    parser.add_argument("--watch", action="store_true", help="Nöbetçi mod: Arka planda sürekli çalışır, yeni indirim düştükçe video üretir")
    parser.add_argument("--interval", type=int, default=30, help="Nöbetçi modda kontrol aralığı (dakika, Varsayılan: 30)")
    parser.add_argument("--count", type=int, default=1, help="Üretilecek video sayısı (Varsayılan: 1)")
    parser.add_argument("--image", type=str, help="Kendi ürün fotoğrafın veya ekran görüntün (Gemini Vision ile okunur)")
    parser.add_argument("--url", type=str, help="İndirimli ürün web linki")
    parser.add_argument("--manual", action="store_true", help="Manuel bilgi girişi modu")
    parser.add_argument("--title", type=str, help="Ürün başlığı")
    parser.add_argument("--old", type=str, help="Eski fiyat (örn: 1.999 TL)")
    parser.add_argument("--new", type=str, help="Yeni indirimli fiyat (örn: 999 TL)")
    parser.add_argument("--discount", type=str, default="-40%", help="İndirim yüzdesi (örn: -50%%)")
    parser.add_argument("--badge", type=str, default="GÜNÜN FIRSATI", help="Rozet metni (örn: GÜNÜN FIRSATI, ÇÖKÜŞ FİYAT)")
    parser.add_argument("--hook", type=str, default="", help="Neden kaçırılmayacak fırsat olduğunu anlatan detay")
    parser.add_argument("--top3", action="store_true", help="Günün En İyi 3 Fırsatı (Top 3) videosunu ve açıklamasını üret")
    parser.add_argument("--meme", type=str, choices=[m.replace(".mp4", "") for m in AVAILABLE_MEMES], help="Kullanılacak özel meme videosu")
    parser.add_argument("--audio", type=str, help="Kullanılacak özel müzik dosyası")
    parser.add_argument("--no-upload", action="store_true", help="Videoyu ve metni hazırla ancak Telegram'a ve web vitrinine yükleme yapma")
    parser.add_argument("--min-discount", type=int, default=25, help="Minimum indirim yüzdesi eşiği (Varsayılan: 25)")
    parser.add_argument("--watchlist", action="store_true", help="İzleme listesindeki ürünlerin fiyat düşüşlerini kontrol et")

    args = parser.parse_args()

    platform = "amazon" if args.amazon else args.platform

    # Günün En İyi 3 Fırsatı (Top 3) Modu
    if args.top3:
        print(f"🏆 [MOD: GÜNÜN EN İYİ 3 FIRSATI (TOP 3) AVI - Platform: {platform.upper()}]")
        history = load_history()
        fresh_deals = hunt_best_deals(limit=3, platform=platform, category=args.category, min_discount=args.min_discount)
        if len(fresh_deals) < 3:
            print("⚠️ Yeterli indirim bulunamadı, mevcut fırsatlar tamamlanıyor...")
            defaults = [
                {"title": "Sony PS5 DualSense Kablosuz Kol", "old_price": "3.499 TL", "new_price": "2.299 TL", "discount_pct": "-34%", "store_name": "Amazon TR", "store_url": "https://www.amazon.com.tr/dp/B08H99BPJN"},
                {"title": "SteelSeries Arctis Nova 1 Oyuncu Kulaklığı", "old_price": "2.199 TL", "new_price": "1.349 TL", "discount_pct": "-38%", "store_name": "Amazon TR", "store_url": "https://www.amazon.com.tr/dp/B0B15VJZQZ"},
                {"title": "Logitech G G102 Lightsync RGB Gaming Mouse", "old_price": "899 TL", "new_price": "499 TL", "discount_pct": "-45%", "store_name": "Amazon TR", "store_url": "https://www.amazon.com.tr/dp/B07W4DH8JW"}
            ]
            for def_deal in defaults:
                if len(fresh_deals) < 3:
                    fresh_deals.append(def_deal)

        # Affiliate link ve web vitrini senkronizasyonu
        for d in fresh_deals:
            raw_url = d.get("store_url", "")
            aff_url = get_affiliate_url(raw_url, d.get("store_name", "Amazon TR"))
            d["store_url"] = aff_url
            d["affiliate_url"] = aff_url
            try:
                add_deal_to_web(d)
            except Exception as e:
                print(f"[Web Vitrini] Senkronizasyon uyarısı: {e}")

        # Video & Caption üret
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        v_name = f"top3_deals_{timestamp}.mp4"
        v_path = build_top3_video(fresh_deals, output_filename=v_name)
        c_text = generate_top3_caption(fresh_deals)
        c_path = os.path.join(OUTPUT_DIR, f"top3_deals_{timestamp}_aciklama.txt")
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(c_text)

        # Telegram'a gönder
        try:
            send_telegram_deal(v_path, c_text, product_url=fresh_deals[0].get("store_url"))
            print("📲 Telegram bildirimi başarıyla gönderildi!")
        except Exception as e:
            print(f"Telegram gönderim uyarısı: {e}")


        print(f"\n🎉 Top 3 Fırsat Videosu Hazır: {v_path}")
        print(f"✍️ Açıklama Metni: {c_path}")
        return

    # İzleme Listesi Fiyat Düşüşü Modu
    if args.watchlist:
        print(f"📡 [MOD: İZLEME LİSTESİ FİYAT DÜŞÜŞÜ ALARMI]")
        from watchlist import check_watchlist_drops
        drops = check_watchlist_drops(min_drop_pct=20.0)
        if not drops:
            print("💤 Takip listesindeki ürünlerde henüz %20+ fiyat düşüşü tespit edilmedi.")
            return
        print(f"🚨 {len(drops)} adet fiyat düşüş alarmı yakalandı! Videolar üretiliyor...")
        for deal in drops[:args.count]:
            process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)
        return

    # Nöbetçi Modu (Full Aktif / Arka Plan)
    if args.watch:
        print(f"👀 [NÖBETÇİ MODU AKTİF]")
        print(f"Bot arka planda sürekli çalışacak ve her {args.interval} dakikada bir Amazon, Trendyol ve Hepsiburada'yı tarayacak.")
        print("Durdurmak için Ctrl+C basabilirsiniz.\n")
        history = load_history()
        while True:
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{now_str}] 🔍 İndirimler ve İzleme Listesi taranıyor (Platform: {platform.upper()})...")

            # 1. İzleme listesi fiyat düşüş kontrolü
            try:
                from watchlist import check_watchlist_drops
                w_drops = check_watchlist_drops(min_drop_pct=20.0)
                for drop_deal in w_drops:
                    if get_deal_sig(drop_deal) not in history:
                        print(f"🚨 [Watchlist Alarmı] {drop_deal['title']} için öncelikli video üretiliyor!")
                        res = process_deal_to_reel(drop_deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)
                        if res:
                            history.add(get_deal_sig(drop_deal))
            except Exception as e:
                print(f"[Watchlist] Kontrol hatası: {e}")

            # 2. Genel indirim avı
            deals = hunt_best_deals(limit=5, platform=platform, category=args.category, exclude_urls=history, min_discount=args.min_discount)
            new_deals = [d for d in deals if get_deal_sig(d) not in history]
            if new_deals:
                print(f"🔔 {len(new_deals)} adet YENİ sıcak indirim yakalandı! Videolar hazırlanıyor...")
                for deal in new_deals[:2]:
                    res = process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)
                    if res:
                        history.add(get_deal_sig(deal))
            else:
                print("💤 Henüz yeni bir fırsat düşmedi. Bir sonraki kontrole kadar bekleniyor...")

            time.sleep(args.interval * 60)

    # Otomatik veya Çoklu Platform Modu
    elif args.auto or args.amazon or args.platform != "all":
        print(f"🚀 [MOD: EN İYİ İNDİRİM AVI - Platform: {platform.upper()}]")
        history = load_history()
        last_prod = get_last_product()
        last_sub = get_last_subtype()
        exclude_subtypes = {last_sub} if last_sub and last_sub != "general" else set()
        if exclude_subtypes:
            print(f"[Deal Bot] 🛡️ Çeşitlilik Koruması Aktif (Son ürün: '{last_prod}' | Engellenen Alt Kategori: {list(exclude_subtypes)})")

        fresh_deals = hunt_best_deals(limit=10, platform=platform, category=args.category, exclude_urls=history, exclude_subtypes=exclude_subtypes, min_discount=args.min_discount)
        if not fresh_deals:
            fresh_deals = hunt_best_deals(limit=10, platform=platform, category=args.category, exclude_subtypes=exclude_subtypes, min_discount=args.min_discount)
        if not fresh_deals:
            fresh_deals = hunt_best_deals(limit=10, platform=platform, category=args.category, min_discount=15)

        # Son işlenen ürünle veya alt kategorisiyle aynı olanları filtrele (ard arda tekrar etmez)
        valid_deals = []
        for d in fresh_deals:
            t = d.get("title", "")
            d_sub = get_product_subtype(t)
            if t == last_prod or get_deal_sig(d) == last_prod:
                continue
            if last_sub and d_sub == last_sub and d_sub != "general":
                continue
            valid_deals.append(d)

        chosen_deals = valid_deals if valid_deals else fresh_deals

        if not chosen_deals:
            print("❌ Yeni indirim bulunamadı.")
            sys.exit(1)

        print(f"\n🎯 Aday fırsatlar arasından doğrulanmış {args.count} adet video üretilecek (Ard arda tekrar engellendi)...\n")
        results = []
        candidate_idx = 0
        while len(results) < args.count and candidate_idx < len(chosen_deals):
            deal = chosen_deals[candidate_idx]
            candidate_idx += 1
            print(f">>> Fırsat Adayı {candidate_idx}/{len(chosen_deals)} işleniyor: [{deal.get('store_name')}] {deal.get('title')}")
            res = process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)
            if res:
                results.append(res)

        print(f"\n🎉 Tüm işlem tamamlandı! Toplam {len(results)} video 'output/' klasöründe paylaşıma hazır.")


    elif args.image and not args.manual:
        print(f"📸 [MOD: GÖRSEL ANALİZİ İLE ÜRETİM]")
        deal = parse_deal_from_image(args.image)
        if args.title: deal["title"] = args.title
        if args.old: deal["old_price"] = args.old
        if args.new: deal["new_price"] = args.new
        if args.discount != "-40%": deal["discount_pct"] = args.discount
        if args.badge != "GÜNÜN FIRSATI": deal["badge"] = args.badge
        if args.hook: deal["hook"] = args.hook

        process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)

    elif args.url:
        print(f"🔗 [MOD: WEB URL ANALİZİ İLE ÜRETİM]")
        deal = parse_deal_from_url(args.url)
        if args.title: deal["title"] = args.title
        if args.old: deal["old_price"] = args.old
        if args.new: deal["new_price"] = args.new
        if args.discount != "-40%": deal["discount_pct"] = args.discount
        if args.badge != "GÜNÜN FIRSATI": deal["badge"] = args.badge
        if args.hook: deal["hook"] = args.hook

        process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio, upload=not args.no_upload)

    elif args.manual or args.title:
        print("✍️ [MOD: MANUEL GİRİŞ İLE ÜRETİM]")
        deal = {
            "title": args.title or "Günün Özel Fırsat Ürünü",
            "old_price": args.old or "1.999 TL",
            "new_price": args.new or "999 TL",
            "discount_pct": args.discount,
            "badge": args.badge,
            "hook": args.hook or "Piyasanın çok altında, kaçırılmayacak fırsat!",
            "image_path": args.image or os.path.join(TEMP_DIR, "hunt_prod_1.jpg")
        }
        process_deal_to_reel(deal, meme_choice=args.meme, audio_choice=args.audio)

if __name__ == "__main__":
    main()
