import os
import sys
import time
import json
from datetime import datetime, timedelta
from config import BASE_DIR, DATA_DIR

SCHEDULE_STATE_FILE = os.path.join(DATA_DIR, "scheduler_state.json")

# Günün Algoritma Açısından En Verimli 2 Saati (Türkiye Yerel Saati)
TARGET_SLOTS = [
    {"name": "Öğle Molası (Algoritma Zirvesi)", "hour": 12, "minute": 30},
    {"name": "Akşam Prime Time (Etkileşim & Alışveriş Zirvesi)", "hour": 20, "minute": 0}
]

def load_schedule_state() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SCHEDULE_STATE_FILE):
        try:
            with open(SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_schedule_state(state: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(SCHEDULE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Scheduler] Durum kaydedilemedi: {e}")

def get_next_run_info() -> dict:
    """Bir sonraki hedeflenen çalışma zamanını ve kalan süreyi hesaplar."""
    now = datetime.now()
    candidates = []

    for slot in TARGET_SLOTS:
        target_today = now.replace(hour=slot["hour"], minute=slot["minute"], second=0, microsecond=0)
        if target_today > now:
            candidates.append((target_today, slot["name"]))
        else:
            target_tomorrow = target_today + timedelta(days=1)
            candidates.append((target_tomorrow, slot["name"]))

    candidates.sort(key=lambda x: x[0])
    next_time, slot_name = candidates[0]
    diff = next_time - now
    hours, remainder = divmod(int(diff.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)

    return {
        "next_time": next_time.strftime("%Y-%m-%d %H:%M:%S"),
        "slot_name": slot_name,
        "remaining_str": f"{hours} saat {minutes} dakika",
        "remaining_seconds": int(diff.total_seconds())
    }

def run_scheduler_daemon(dry_run: bool = False):
    """
    Arka planda kesintisiz çalışan zamanlayıcı servisi.
    Saat 12:30 ve 20:00'da otopilot motorunu tetikler.
    """
    print("="*65)
    print("⏰ [FLAŞ FIRSAT 24/7 OTOPİLOT ZAMANLAYICI BAŞLATILDI]")
    print("🎯 Hedef Kuşaklar:")
    for s in TARGET_SLOTS:
        print(f"  • {s['hour']:02d}:{s['minute']:02d} - {s['name']}")
    print("📱 Hedef Kanallar: YouTube Shorts, Instagram Reels, Telegram, WhatsApp")
    print("Durdurmak için Ctrl+C basabilirsiniz.")
    print("="*65 + "\n")

    from autopilot_engine import run_autopilot_deal_cycle

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            state = load_schedule_state()
            executed_slots = state.get("executed_slots", [])

            for slot in TARGET_SLOTS:
                sh = slot["hour"]
                sm = slot["minute"]
                slot_id = f"{today_str}_{sh:02d}{sm:02d}"

                # Saat ve dakika eşleşti mi?
                if now.hour == sh and now.minute == sm:
                    if slot_id not in executed_slots:
                        print(f"\n🔔 [ZAMANLAYICI TETİKLENDİ!] Saat: {sh:02d}:{sm:02d} -> {slot['name']}")
                        
                        # Pazar akşamı 20:00 kuşağında haftalık Top 3 bülteni yayınla, diğer günlerde tekli fırsat
                        if now.weekday() == 6 and sh == 20:
                            print("🏆 [Pazar Özel] Haftalık 'En İyi 3 İndirim' videosu hazırlanıyor...")
                            from autopilot_engine import run_top3_deal_cycle
                            res = run_top3_deal_cycle(dry_run=dry_run, slot_name="Haftalık Top 3 Bülteni (Pazar Özel)")
                        else:
                            res = run_autopilot_deal_cycle(dry_run=dry_run, slot_name=slot["name"])
                        
                        # Durumu kaydet (aynı dakika içinde ikinci kez çalışmaması için)
                        executed_slots.append(slot_id)
                        # Son 30 kaydı tut
                        state["executed_slots"] = executed_slots[-30:]
                        state["last_run"] = {
                            "slot_id": slot_id,
                            "slot_name": slot["name"],
                            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "success": res.get("success", False)
                        }
                        save_schedule_state(state)
                        print(f"✅ Slot '{slot_id}' başarıyla kaydedildi. Bir sonraki hedef bekleniyor...\n")

            # Her 20 saniyede bir kontrol et
            time.sleep(20)

        except KeyboardInterrupt:
            print("\n👋 Zamanlayıcı durduruldu.")
            break
        except Exception as e:
            print(f"[Scheduler] Döngü istisnası: {e}")
            time.sleep(20)

if __name__ == "__main__":
    if "--status" in sys.argv:
        info = get_next_run_info()
        print("\n📊 [OTOPİLOT ZAMANLAYICI DURUMU]")
        print(f"👉 Bir Sonraki Yayın: {info['next_time']} ({info['slot_name']})")
        print(f"⏳ Kalan Süre:         {info['remaining_str']}\n")
    else:
        dry = "--dry-run" in sys.argv
        run_scheduler_daemon(dry_run=dry)
