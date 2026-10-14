import os
import sys
import time
import re
from playwright.sync_api import sync_playwright
from config import BASE_DIR, DATA_DIR, SITE_URL

USER_DATA_DIR = os.path.join(DATA_DIR, "whatsapp_user_data")
WHATSAPP_CHANNEL_NAME = os.getenv("WHATSAPP_CHANNEL_NAME", "Flaş Fırsat").strip()

def check_whatsapp_ready() -> dict:
    """WhatsApp oturumunun hazır olup olmadığını denetler."""
    if not os.path.exists(USER_DATA_DIR):
        return {"ready": False, "message": "WhatsApp oturumu açılmamış. 'python whatsapp_auth.py' çalıştırarak bir kez QR kod okutun."}
    idb = os.path.join(USER_DATA_DIR, "Default", "IndexedDB")
    if not os.path.exists(idb) or len(os.listdir(idb)) == 0:
        return {"ready": False, "message": "WhatsApp oturumu eksik veya geçersiz. Lütfen 'python whatsapp_auth.py' ile tekrar giriş yapın."}
    return {"ready": True, "message": "WhatsApp oturumu hazır."}

def format_whatsapp_message(deal: dict, product_url: str = "") -> str:
    """WhatsApp için estetik ve biçimlendirilmiş fırsat metni üretir."""
    title = deal.get("title", "Flaş Fırsat")
    old_p = deal.get("old_price", "")
    new_p = deal.get("new_price", "")
    disc = deal.get("discount_pct", "")
    store = deal.get("store_name", "Amazon TR")
    seller_badge = deal.get("seller_badge", "")
    net_cost = deal.get("net_cost", "")
    bank_camp = deal.get("bank_campaign", "")
    p_url = product_url or deal.get("affiliate_url") or deal.get("store_url", "")
    site_link = f"{SITE_URL}?utm_source=whatsapp&utm_medium=channel"

    msg_lines = [
        f"🔥 *{title.upper()}*",
        ""
    ]
    if old_p and new_p:
        msg_lines.append(f"❌ Eski Fiyat: ~{old_p}~")
        msg_lines.append(f"✅ İndirimli Fiyat: *{new_p}* ({disc})")
    elif new_p:
        msg_lines.append(f"✅ Fırsat Fiyatı: *{new_p}*")

    if net_cost:
        msg_lines.append(f"💳 {bank_camp} ➔ *Net: {net_cost}*")

    if seller_badge:
        msg_lines.append(f"🏢 Satıcı: {seller_badge}")
    else:
        msg_lines.append(f"🏪 Mağaza: {store}")

    msg_lines.append("")
    if p_url:
        msg_lines.append("🛒 *İndirimli Satın Alma Linki:*")
        msg_lines.append(p_url)
        msg_lines.append("")

    msg_lines.append("🌐 *Tüm Canlı Fırsatlar & İndirim Radarı:*")
    msg_lines.append(site_link)
    msg_lines.append("")
    msg_lines.append("#işbirliği #reklam")

    return "\n".join(msg_lines)

def publish_deal_to_whatsapp_channel(
    deal: dict,
    image_path: str = None,
    channel_name: str = None,
    headless: bool = True
) -> dict:
    """
    Playwright ve WhatsApp Web üzerinden verilen fırsatı doğrudan WhatsApp Kanalına otomatik gönderir.
    Görsel varsa görsel + açıklama, yoksa metin olarak iletir.
    """
    chk = check_whatsapp_ready()
    if not chk.get("ready"):
        print(f"[WhatsApp Publisher] ⚠️ {chk.get('message')}")
        return {"success": False, "error": chk.get("message")}

    target_channel = channel_name or WHATSAPP_CHANNEL_NAME or "Flaş Fırsat"
    caption_text = format_whatsapp_message(deal)
    target_img = image_path if (image_path and os.path.exists(image_path)) else deal.get("image_path")

    print(f"\n[WhatsApp Publisher] 🚀 WhatsApp Kanalına otomatik paylaşım başlatılıyor...")
    print(f"📢 Hedef Kanal: {target_channel}")
    print(f"📦 Ürün:       {deal.get('title')}")

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=headless,
                channel="chromium",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars"
                ],
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )

            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            # 1. Sayfanın yüklenmesini bekle (Arama kutusu veya sohbet paneli)
            print("[WhatsApp Publisher] ⏳ WhatsApp Web yükleniyor...")
            search_box = page.wait_for_selector(
                "div[contenteditable='true'][data-tab='3'], #pane-side",
                timeout=45000
            )
            if not search_box:
                context.close()
                return {"success": False, "error": "WhatsApp Web açılamadı veya oturum süresi doldu."}

            time.sleep(2)

            # 2. Kanalı Bul ve Aç
            # Önce arama kutusuna kanal adını yaz
            search_input = page.locator("div[contenteditable='true'][data-tab='3']").first
            if search_input.is_visible():
                search_input.click()
                search_input.fill(target_channel)
                time.sleep(2)

            # Ekranda çıkan kanala/sohbete tıkla
            channel_item = page.locator(f"span[title*='{target_channel}']").first
            if not channel_item.is_visible():
                # Arama sonuçlarında genel span ara
                channel_item = page.locator(f"div[role='listitem'] >> text='{target_channel}'").first

            if not channel_item.is_visible():
                # Sol menüden 'Kanallar' sekmesine geçmeyi dene
                channels_tab = page.locator("button[aria-label*='Kanal'], button[aria-label*='Channel'], span[data-icon='newsletter-outline']").first
                if channels_tab.is_visible():
                    channels_tab.click()
                    time.sleep(2)
                    channel_item = page.locator(f"span[title*='{target_channel}']").first

            if not channel_item.is_visible():
                context.close()
                return {"success": False, "error": f"'{target_channel}' adlı WhatsApp kanalı sohbet listenizde bulunamadı."}

            channel_item.click()
            time.sleep(2)
            print(f"[WhatsApp Publisher] ✅ '{target_channel}' kanalı açıldı.")

            # 3. Görsel veya Metin Gönder
            if target_img and os.path.exists(target_img):
                print(f"[WhatsApp Publisher] 🖼️ Görsel yükleniyor: {os.path.basename(target_img)}...")
                # Dosya yükleme inputunu bul (WhatsApp Web'de gizli file input mevcuttur)
                file_input = page.locator("input[type='file'][accept*='image']").first
                if not file_input.is_visible():
                    # Ekle (+) butonuna bas
                    plus_btn = page.locator("div[title*='Ekle'], span[data-icon='plus'], div[aria-label*='Ekle']").first
                    if plus_btn.is_visible():
                        plus_btn.click()
                        time.sleep(1)

                page.set_input_files("input[type='file'][accept*='image']", target_img)
                time.sleep(2)

                # Açıklama (Caption) kutusuna metni yaz
                caption_box = page.locator("div[contenteditable='true'][aria-label*='Açıklama'], div[contenteditable='true'][data-tab='10'], div[contenteditable='true']").last
                caption_box.click()
                # Çok satırlı metni clipboard veya doğrudan yaz
                page.keyboard.type(caption_text, delay=10)
                time.sleep(1)

                # Gönder butonuna bas
                send_btn = page.locator("span[data-icon='send'], div[aria-label*='Gönder']").first
                if send_btn.is_visible():
                    send_btn.click()
                else:
                    page.keyboard.press("Enter")
            else:
                # Sadece Metin Gönder
                msg_box = page.locator("div[contenteditable='true'][data-tab='10']").first
                msg_box.click()
                page.keyboard.type(caption_text, delay=10)
                time.sleep(1)
                page.keyboard.press("Enter")

            print("[WhatsApp Publisher] ⏳ Mesaj gönderiliyor...")
            time.sleep(4)
            context.close()
            print("🎉 [WhatsApp Publisher] Fırsat WhatsApp Kanalında başarıyla yayınlandı!")
            return {"success": True, "message": "WhatsApp Kanalında başarıyla yayınlandı!"}

    except Exception as e:
        print(f"[WhatsApp Publisher] ❌ Hata oluştu: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    st = check_whatsapp_ready()
    print("Durum:", st)
