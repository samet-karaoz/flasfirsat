import os
import sys
import time
import re
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
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
    target_channel = channel_name or WHATSAPP_CHANNEL_NAME or "Flaş Fırsat"
    caption_text = format_whatsapp_message(deal)
    target_img = image_path if (image_path and os.path.exists(image_path)) else deal.get("image_path")

    # 1. Bulut Webhook / API Köprüsü Kontrolü (Cloud-First Mode)
    webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL") or os.getenv("WHATSAPP_API_URL")
    if webhook_url:
        print(f"\n[WhatsApp Publisher] 🌐 Bulut Webhook Köprüsü Kullanılıyor: {webhook_url}...")
        try:
            import requests
            payload = {
                "channel": target_channel,
                "caption": caption_text,
                "title": deal.get("title"),
                "price": deal.get("new_price"),
                "url": deal.get("affiliate_url") or deal.get("store_url", "")
            }
            files = {}
            f_handle = None
            if target_img and os.path.exists(target_img):
                f_handle = open(target_img, "rb")
                files["image"] = f_handle

            headers = {}
            api_token = os.getenv("WHATSAPP_API_TOKEN")
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"

            try:
                res = requests.post(webhook_url, data=payload, files=files, headers=headers, timeout=20)
                if res.status_code in (200, 201, 202):
                    print("✅ [WhatsApp Publisher] Bulut Köprüsü ile WhatsApp Kanalına Başarıyla Gönderildi!")
                    return {"success": True, "mode": "cloud_webhook"}
                else:
                    print(f"⚠️ [WhatsApp Publisher] Webhook yanıt kodu: {res.status_code}")
            finally:
                if f_handle:
                    f_handle.close()
        except Exception as e_hook:
            print(f"[WhatsApp Publisher] Webhook hatası: {e_hook}")

    # 2. Yerel / Headless Playwright Tarayıcı Modu
    if not sync_playwright:
        msg = "Playwright modülü sistemde yüklü değil. Yerel WhatsApp paylaşımı için 'pip install playwright' gereklidir."
        print(f"[WhatsApp Publisher] ⚠️ {msg}")
        return {"success": False, "error": msg}

    chk = check_whatsapp_ready()
    if not chk.get("ready"):
        print(f"[WhatsApp Publisher] ⚠️ {chk.get('message')}")
        return {"success": False, "error": chk.get("message")}

    print(f"\n[WhatsApp Publisher] 🚀 WhatsApp Kanalına otomatik paylaşım başlatılıyor...")
    print(f"📢 Hedef Kanal: {target_channel}")
    print(f"📦 Ürün:       {deal.get('title')}")

    try:
        with sync_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage"
            ]
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=headless,
                    channel="chrome",
                    args=launch_args,
                    viewport={"width": 1280, "height": 800}
                )
            except Exception:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=headless,
                    args=launch_args,
                    viewport={"width": 1280, "height": 800}
                )

            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            # 1. Sayfanın yüklenmesini bekle (Sohbet paneli)
            print("[WhatsApp Publisher] ⏳ WhatsApp Web yükleniyor...")
            pane = page.wait_for_selector(
                "#pane-side, div[contenteditable='true']",
                timeout=45000
            )
            if not pane:
                context.close()
                return {"success": False, "error": "WhatsApp Web açılamadı veya oturum süresi doldu."}

            time.sleep(2)

            # 2. Kanallar Sekmesini Aç
            channel_tab = page.locator("button[aria-label*='Kanal'], div[aria-label*='Kanal'], span[data-icon='newsletter-outline']").first
            if channel_tab.is_visible():
                print("[WhatsApp Publisher] 📂 Kanallar sekmesine geçiliyor...")
                channel_tab.click()
                time.sleep(2)

            # 3. Kanalı Bul ve Aç
            channel_item = page.locator(f"span[title*='{target_channel}']").first
            if not channel_item.is_visible():
                channel_item = page.locator("span[title*='Flaş Fırsat']").first
            if not channel_item.is_visible():
                channel_item = page.locator("div[role='listitem']").filter(has_text="Flaş Fırsat").first

            if not channel_item.is_visible():
                context.close()
                return {"success": False, "error": f"'{target_channel}' adlı WhatsApp kanalı listenizde bulunamadı."}

            channel_item.click()
            time.sleep(2)
            print(f"[WhatsApp Publisher] ✅ '{target_channel}' kanalı açıldı.")

            # 4. Görsel veya Metin Gönder
            lines = caption_text.split("\n")

            if target_img and os.path.exists(target_img):
                print(f"[WhatsApp Publisher] 🖼️ Görsel yükleniyor: {os.path.basename(target_img)}...")
                page.set_input_files("input[type='file'][accept*='image']", target_img)
                time.sleep(2)

                # Açıklama (Caption) kutusuna metni yaz
                caption_box = page.locator("div[contenteditable='true'][aria-label*='Açıklama'], div[contenteditable='true'][aria-label*='yazın'], div[contenteditable='true']").last
                try:
                    caption_box.click(force=True, timeout=5000)
                except Exception:
                    try:
                        caption_box.focus(timeout=3000)
                    except Exception:
                        pass

                for i, line in enumerate(lines):
                    if line:
                        page.keyboard.insert_text(line)
                    if i < len(lines) - 1:
                        page.keyboard.press("Shift+Enter")
                time.sleep(1)

                # Gönder butonu
                send_btn = page.locator("span[data-icon='send'], div[aria-label*='Gönder']").first
                if send_btn.is_visible():
                    send_btn.click()
                else:
                    page.keyboard.press("Enter")
            else:
                # Sadece Metin Gönder
                print("[WhatsApp Publisher] ✍️ Metin güncellemesi yazılıyor...")
                msg_box = page.locator("div[contenteditable='true'][data-tab='10'], div[contenteditable='true'][aria-label*='mesaj'], div[contenteditable='true'][aria-label*='güncelleme']").last
                msg_box.click()

                for i, line in enumerate(lines):
                    if line:
                        page.keyboard.insert_text(line)
                    if i < len(lines) - 1:
                        page.keyboard.press("Shift+Enter")
                time.sleep(1)
                page.keyboard.press("Enter")

            print("[WhatsApp Publisher] ⏳ Mesaj iletiliyor...")
            time.sleep(4)
            context.close()
            print("🎉 [WhatsApp Publisher] Fırsat WhatsApp Kanalında başarıyla yayınlandı!")
            return {"success": True, "message": "WhatsApp Kanalında başarıyla yayınlandı!"}

    except Exception as e:
        print(f"[WhatsApp Publisher] ❌ Hata oluştu: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    st = check_whatsapp_ready()
    print("WhatsApp Durumu:", st)
