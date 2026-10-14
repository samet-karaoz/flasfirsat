import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USER_DATA_DIR = os.path.join(DATA_DIR, "whatsapp_user_data")

def check_whatsapp_login() -> bool:
    """WhatsApp oturumunun kayıtlı olup olmadığını hızlıca kontrol eder."""
    if not os.path.exists(USER_DATA_DIR):
        return False
    # Local Storage veya IndexedDB var mı
    idb = os.path.join(USER_DATA_DIR, "Default", "IndexedDB")
    return os.path.exists(idb) and len(os.listdir(idb)) > 0

def login_whatsapp_interactive(timeout_sec: int = 120):
    """
    Kullanıcıya WhatsApp Web penceresini açar ve QR kodu okutmasını bekler.
    QR kod okutulduğunda oturumu kalıcı olarak data/whatsapp_user_data klasörüne kaydeder.
    """
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    print("\n" + "="*60)
    print("🟢 WHATSAPP WEB OTURUM AÇMA BAŞLATILIYOR...")
    print("="*60)
    print("1. Tarayıcı penceresi açılacak.")
    print("2. Telefonunuzdan WhatsApp > Bağlı Cihazlar > Cihaz Bağla diyerek ekrandaki QR kodu okutun.")
    print("3. Sohbetler yüklendiğinde oturum kalıcı olarak kaydedilecektir.\n")

    with sync_playwright() as p:
        # Gerçek kullanıcı gibi görünmek için Chrome parametreleri
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chromium",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ],
            viewport=None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://web.whatsapp.com")

        print("[WhatsApp Auth] ⏳ QR kod bekleniyor / Oturum açılıyor...")
        
        # Giriş yapıldığında sol taraftaki panel veya sohbet listesi belirir
        logged_in = False
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            try:
                # Sohbet listesi veya arama kutusu kontrolü
                if page.locator("#pane-side").is_visible() or page.locator("div[aria-label='Sohbet listesi']").is_visible() or page.locator("div[contenteditable='true'][data-tab='3']").is_visible():
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(1.5)

        if logged_in:
            print("\n🎉 TEBRİKLER! WhatsApp Web oturumu başarıyla bağlandı ve kaydedildi!")
            print(f"📁 Oturum Konumu: {USER_DATA_DIR}\n")
            time.sleep(3)
            context.close()
            return True
        else:
            print("\n⚠️ Süre doldu veya QR kod okutulmadı.")
            context.close()
            return False

if __name__ == "__main__":
    login_whatsapp_interactive()
