import os
import sys
import html as _html
import requests

sys.path.append('.')
from telegram_notifier import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    send_telegram_deal_for_approval
)
from telegram_bot_service import send_telegram_text
from story_composer import create_story_card

deal = {
    "title": "Dell 24\" 200Hz 1ms IPS Gaming Monitör",
    "old_price": "5.999 TL",
    "new_price": "4.449 TL",
    "discount_pct": "-26%",
    "discount_val": 26,
    "store_name": "Amazon TR",
    "store_url": "https://www.amazon.com.tr/dp/B0FHHVD75B?tag=flasfirsat04-21",
    "seller_badge": "AMAZON TR",
    "image_path": "assets/products/dell_200hz_gaming_monitor.jpg",
    "installment": "Peşin Fiyatına 3 Taksit x 1.483 TL",
    "killer_hook": "4.449 TL'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ!",
    "feature_pill": "4.449 TL'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ!",
    "has_verified_old_price": True,
    "is_lowest_30d": True,
    "market_badge": "SON 30 GÜNÜN EN DÜŞÜĞÜ",
    "reaction_text": "200Hz IPS MONİTÖRÜ 4.449 TL'YE GÖREN BİZİM TAYFA:"
}

video_path = os.path.abspath("output/20261017_012830_dell_24_200hz_1ms_ips_gaming_m.mp4")
yt_video_path = os.path.abspath("output/20261017_012830_dell_24_200hz_1ms_ips_gaming_m_youtube.mp4")
caption_file = os.path.abspath("output/20261017_012830_dell_24_200hz_1ms_ips_gaming_m_aciklama.txt")

with open(caption_file, "r", encoding="utf-8") as f:
    caption_text = f.read().strip()

# Story kartını yeniden taze üretelim (en güncel yerleşim ve Pilmoji emojileri ile)
story_path = os.path.abspath("temp/story_dell_200hz_gaming_monitor.jpg")
create_story_card(deal, story_path)

product_url = deal["store_url"]

print("1️⃣ Onay ve kontrol paneli Telegram'a gönderiliyor...")
res = send_telegram_deal_for_approval(
    deal=deal,
    video_path=video_path,
    caption_text=caption_text,
    product_url=product_url,
    youtube_video_path=yt_video_path,
    story_image_path=story_path
)

if not res.get("success"):
    print("❌ Hata:", res.get("error"))
    sys.exit(1)

print(f"✅ Video başarıyla gönderildi! (Mesaj ID: {res.get('message_id')})")

print("2️⃣ 1080x1920 Story kartı fotoğraf olarak gönderiliyor...")
with open(story_path, "rb") as sf:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": (
                f"📸 <b>1080x1920 HİKAYE (STORY) KARTI HAZIR!</b>\n\n"
                f"1️⃣ Bu görseli telefonuna kaydet ve Instagram/TikTok Hikayene ekle.\n"
                f"2️⃣ <b>🗳️ Anket Çıkartması (Etkileşim Hilesi):</b>\n"
                f"Soru: <i>'Sizce bu fiyata değer mi?'</i>\n"
                f"Seçenekler: [🔥 Alınır] / [😴 Değmez]\n"
                f"3️⃣ <b>🔗 Bağlantı (Link) Çıkartması:</b>\n"
                f"En alttaki kutucuğa dokunup bu linki yapıştır:\n"
                f"<code>{_html.escape(product_url)}</code>"
            ),
            "parse_mode": "HTML"
        },
        files={"photo": sf},
        timeout=45
    )

print("3️⃣ Tek dokunuşla kopyalanabilir açıklama ve ManyChat paketi gönderiliyor...")
first_comment_str = "📌 Fırsat şu an aktif! Ürün linki profilimizdeki web sitemizde ve Hikayede! (Doğrudan DM kutusuna isteyenler yoruma 'FIRSAT' yazabilir 👇)"
studio_msg = (
    f"📲 <b>%100 ORGANİK INSTAGRAM & TIKTOK STÜDYO PAKETİ</b>\n"
    f"<i>(Aşağıdaki kutucuklara bir kez dokunarak metni kopyalayabilirsiniz)</i>\n\n"
    f"📋 <b>1. VİDEO AÇIKLAMASI (Dokun & Kopyala):</b>\n"
    f"<code>{_html.escape(caption_text)}</code>\n\n"
    f"💬 <b>2. BAŞA TUTTURULACAK İLK YORUM (Dokun & Kopyala):</b>\n"
    f"<code>{_html.escape(first_comment_str)}</code>\n\n"
    f"🔗 <b>3. LİNK ÇIKARTMASI & BİO (Dokun & Kopyala):</b>\n"
    f"<code>{_html.escape(product_url)}</code>\n\n"
    f"💡 <b>Keşfet İpucu:</b> Yukarıdaki videoyu telefonuna kaydet, Instagram veya TikTok'tan Reels/Shorts olarak yüklerken <i>'Ses Ekle'</i> kısmından popüler bir müziği <b>%5-10 ses</b> seviyesinde arkaya ekle!"
)
send_telegram_text(TELEGRAM_CHAT_ID, studio_msg)

print("🎉 Tüm paket Telegram'a eksiksiz iletildi!")
