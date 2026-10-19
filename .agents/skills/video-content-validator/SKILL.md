---
name: video-content-validator
description: "Üretilen MP4 videolarından otomatik kare (frame) çıkarıp ürün görseli varlığını, meme katmanı hareketini, tipografi/fiyat kutusu okunurluğunu ve kutucuk (tofu) hatalarını görüntü işleme ile analiz eden, sorun bulursa varlıkları onarıp videoyu otomatik yeniden render eden denetim rehberi."
---

# Video Content Validator (Render Sonrası Görüntü Analizi ve Otomatik Onarım)

Bu skill, her video render işleminden hemen sonra (`deal_bot.py` -> `process_deal_to_reel` adım 2.5) `video_content_validator.py` modülünü devreye sokarak videonun gerçek ekran görüntüsünü inceler ve kusurlu videoların Telegram'a veya sosyal medyaya gitmesini %100 engeller.

---

## 1. Otomatik Kontrol Katmanları (`validate_rendered_video`)

### A. Akış ve Dosya Sağlamlığı (`check_video_streams`)
- Dosya boyutu en az **50 KB** olmalıdır.
- Çözünürlük tam olarak **1080x1920** (9:16 dikey) olmalıdır.
- Hem `Video: h264` hem de `Audio: aac` akışları mevcut olmalı, süre **3.0 saniyeden** uzun olmalıdır.

### B. Ürün Görseli Varlık Analizi (`analyze_product_region`)
- Videonun `1.20.` saniyesinden çıkarılan karede üst banner'ın beyaz stüdyo kartı merkezi (`x: 200..880, y: 265..665`) kırpılır.
- `ImageFilter.FIND_EDGES` ile kenar yoğunluğu (`edge_mean`) ve güçlü kenar pikseli oranı (`strong_edge_ratio`) ölçülür:
  - **Boş Kart (Görsel Yok):** Sadece yumuşak spotlight gradyanı bulunduğu için `edge_mean < 1.2` ve `strong_edge_ratio < 0.001` çıkar -> **`MISSING_PRODUCT_IMAGE`** hatası tetiklenir.
  - **Sağlam Ürün Görseli:** `edge_mean >= 1.8` ve `strong_edge_ratio >= 0.008` (veya `edge_mean >= 2.5`) şartını sağlar.

### C. Alt Meme Katmanı ve Hareket Kontrolü (`analyze_meme_region`)
- Videonun `1.20.` ve `2.40.` saniyelerindeki iki karenin alt yarısı (`y: 960..1900`) karşılaştırılır.
- Parlaklık standart sapması (`luma_std > 10.0`) ile siyah/bozuk ekran olmadığı doğrulanır.
- İki kare arasındaki piksel farkı (`motion_score > 0.4`) ile meme videosunun donmadığı ve aktif oynadığı teyit edilir.
- Üst-orta alandaki (`x: 200..880, y: 986..1054`) Reaksiyon Başlığı (Hook Overlay) varlığı kontrol edilir.

### D. Tipografi, Fiyat Kutusu ve Tofu (`▢`) Kontrolü (`analyze_banner_typography_and_layout`)
- Fiyat kutusu alanının (`x: 54..1026, y: 750..888`) kontrastı (`price_box_std >= 14.0`) denetlenir.
- Sol (`x: 2..26`) ve sağ (`x: 1054..1078`) güvenli kenar boşluklarında metin taşması olup olmadığı kontrol edilir.
- Tüm metin alanları (`title`, `coupon_info`, `killer_hook`, `market_badge` vb.) TTF fontlarda kutucuk (`▢`) çıkaran emoji ve özel Unicode karakterlere karşı taranır.

---

## 2. Otomatik Onarım Mekanizması (`auto_repair_deal_for_rerender`)

Herhangi bir kontrol başarısız olduğunda sistem kullanıcıya sormadan **en fazla 2 kez** otomatik onarım uygulayıp videoyu yeniden üretir:

1. **`MISSING_PRODUCT_IMAGE` Onarımı:**
   - Bozuk `rembg` önbelleği (`_cutout.png`) silinir.
   - Görsel dosyası eksikse `product_verifier.py` ve `parse_deal_from_url` üzerinden Amazon/mağaza sayfasındaki yüksek çözünürlüklü görsel (`data-old-hires` / `og:image`) yeniden indirilir.
   - Beyaz bir ürün `rembg` tarafından silinmişse `skip_rembg = True` bayrağı açılarak orijinal ürün görseli doğrudan stüdyo kartına yerleştirilir.
2. **`MEME_LAYER_DEFECT` Onarımı:**
   - `select_smart_meme()` ile meme havuzundaki bir sonraki sağlam meme videosuna geçilir.
3. **`TEXT_MARGIN_OVERFLOW` & Tofu Onarımı:**
   - `sanitize_ttf_text()` ile tüm metinlerdeki desteklenmeyen karakterler temizlenir, taşan başlıklar kelime sınırından kısaltılır.

---

## 3. Manuel Çalıştırma Komutu

Üretilmiş herhangi bir videoyu tek başına test etmek için:
```powershell
python video_content_validator.py "output/video_dosyasi.mp4"
```
Sonuç raporu hem ekrana basılır hem de `data/validation_reports/last_validation.json` dosyasına kaydedilir.
