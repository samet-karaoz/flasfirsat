---
name: manual-deal-pipeline
description: "Kullanıcının '5 ürün listele ben seçeyim', 'bu ürünü şu meme ile üret' veya 'videoyu iptal et, değiştir' gibi manuel üretim isteklerinde izlenecek standart iş akışı."
---

# Manual Deal Pipeline (Manuel Ürün Seçimi ve Özel Video Üretim Akışı)

Kullanıcı otopilot dışında manuel müdahale ile ürün seçmek, belirli bir meme atamak veya üretilen bir videoyu iptal edip değiştirmek istediğinde bu iş akışı adım adım uygulanır.

---

## 1. "Bana X Tane Ürün Listele, Ben Seçeyim" Akışı

Kullanıcı aday ürünleri görmek istediğinde doğrudan video üretilmez; önce canlı doğrulamadan geçmiş en iyi adaylar listelenir:

1. `deal_hunter.py` içindeki `hunt_best_deals(limit=15, platform="amazon", min_discount=20)` ile adaylar çekilir ve `calculate_deal_viral_score(d)` ile sıralanır.
2. En yüksek puanlı adaylar `product_verifier.verify_deal_before_publish(d)` ile canlı olarak doğrulanır (stokta mı, fiyat gerçek mi).
3. Doğrulanan **ilk 5 ürün** kullanıcıya net bir tablo halinde sunulur:
   - Sıra No (`1..5`)
   - Ürün Başlığı
   - Eski Fiyat -> Yeni Fiyat ve İndirim Oranı (`-%XX`) + Net TL Tasarruf
   - Varsa Kupon veya Piyasa En Ucuz Rozeti
   - Eşleşecek sıradaki Meme adı
4. Kullanıcının seçtiği numara (`Örn: 3`) için video üretimi başlatılır.

---

## 2. "Bu Ürünü Şu Meme İle Üret" Akışı

Kullanıcı belirli bir ürün ve/veya belirli bir meme belirttiğinde:

1. `autopilot_engine.py` içindeki `run_autopilot_deal_cycle` fonksiyonu `custom_deal`, `meme_choice` ve `force=True` parametreleriyle çağrılır:
   ```python
   from autopilot_engine import run_autopilot_deal_cycle
   run_autopilot_deal_cycle(
       dry_run=False,
       slot_name="Manuel Seçim",
       force=True,
       custom_deal=selected_deal,
       meme_choice="piyano_davul.mp4"
   )
   ```
2. `process_deal_to_reel` otomatik olarak:
   - Canlı fiyat ve yüksek çözünürlüklü ürün görselini (`image_url` -> `image_path`) indirir,
   - Instagram ve YouTube Shorts videolarını üretir,
   - `video_content_validator.py` ile videonun ekran görüntüsünü alıp ürün görseli ve meme katmanını doğrular,
   - Onay butonlarıyla Telegram'a gönderir.

---

## 3. "Videoyu İptal Ettim / Değiştir" Akışı

Kullanıcı üretilen bir videoyu iptal ettiğinde:

1. `data/pending_deals.json` içindeki ilgili kaydın `status` alanı `"rejected"` yapılır.
2. Eğer iptal edilen ürün aynı oturumda farklı bir meme ile yeniden üretilecekse:
   - `history_deals.json` içinden o ürünün URL ve başlığı silinir (mükerrer engeline takılmaması için).
   - Eğer o videoda kullanılan meme harcanmamış sayılacaksa `data/meme_history.json` içindeki `next_index` bir adım geri alınır ve `recent_used` listesinden son eleman çıkarılır.
