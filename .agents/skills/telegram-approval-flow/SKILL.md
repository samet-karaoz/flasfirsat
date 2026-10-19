---
name: telegram-approval-flow
description: "Yarı-otomatik Telegram onay sistemi (pending_deals.json), onay butonları, iptal edilen fırsatların temizlenmesi ve çoklu platform yayın tetikleme rehberi."
---

# Telegram Approval Flow (Yarı-Otomatik Telegram Onay ve Yayın Yönetimi)

Bu skill, üretilen videoların siz onaylamadan hiçbir platformda paylaşılmamasını sağlayan yarı-otomatik onay mekanizmasını (`telegram_bot_service.py`, `telegram_notifier.py` ve `data/pending_deals.json`) yönetir.

---

## 1. Onay Yaşam Döngüsü (`data/pending_deals.json`)

Her üretilen fırsat `pending_deals.json` içine benzersiz bir `deal_id` (Örn: `deal_1792396134`) ile kaydedilir:

- **`pending`:** Video üretildi, `video_content_validator` denetiminden geçti ve yöneticiye Telegram üzerinden önizleme + onay butonlarıyla gönderildi.
- **`approved` / `published_*`:** Yönetici Telegram'dan onay butonuna bastı (`🚀 Tümünde Paylaş`, `📸 Sadece IG`, `▶️ Sadece YT`, `📢 Sadece TG`).
- **`rejected`:** Yönetici `❌ İptal Et` butonuna bastı veya sohbetten iptal talimatı verdi.

---

## 2. İptal Edilen Videonun Geri Alınması (Rollback Protokolü)

Bir video iptal edildiğinde (`rejected`):

1. **Kuyruk Güncellemesi:** `data/pending_deals.json` içindeki kaydın `status` değeri `"rejected"` olarak işaretlenir.
2. **Ürün Geçmişi (`history_deals.json`):**
   - Eğer kullanıcı *"Bu ürünü beğenmedim, başka ürün bul"* dediyse ürün URL'si `history_deals.json` içinde kalır (bir daha aynı ürünü önermemek için).
   - Eğer kullanıcı *"Bu ürüne başka meme ekle / yeniden üret"* dediyse ürün URL'si ve başlığı `history_deals.json` içinden silinir.
3. **Meme Sırası (`data/meme_history.json`):**
   - İptal edilen videoda kullanılan meme harcanmamış sayılacaksa `meme_history.json` içindeki `next_index` bir adım geri sarılır ve `recent_used` listesinden çıkarılır.
