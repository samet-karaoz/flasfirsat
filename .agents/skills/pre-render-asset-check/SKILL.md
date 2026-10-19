---
name: pre-render-asset-check
description: "FFmpeg video derlemesi başlamadan önce ürün görselinin varlığını, çözünürlüğünü, rembg arka plan kesiminin sağlamlığını ve banner metinlerinin font uyumluluğunu denetleyen ön kontrol rehberi."
---

# Pre-Render Asset Check (Render Öncesi Varlık Doğrulama)

Bu skill, FFmpeg ile ağır video render işlemine girmeden önce tüm girdi varlıklarının (ürün görseli, dekupe maskesi, metin alanları, meme ve ses dosyaları) eksiksiz ve hatasız olmasını garanti eder.

---

## 1. Ürün Görseli Ön Kontrolleri

1. **Dosya Varlığı ve Boyut:**
   - `deal["image_path"]` diskte mevcut olmalı ve boyutu **en az 2 KB (2048 byte)** olmalıdır.
   - Manuel URL (`--url`) veya özel fırsat (`custom_deal`) ile gelen ürünlerde `image_path` boşsa, `product_verifier.py` içinden dönen `image_url` mutlaka `config.download_file()` ile `temp/prod_<slug>.jpg` olarak indirilmelidir.
2. **Dekupe (`rembg`) Alfa Maskesi Kontrolü:**
   - `rembg` bazen beyaz renkli ürünleri (termos, kulaklık, beyaz eşya) arka plan sanıp tamamen silebilir.
   - Kesim sonrası oluşan `_cutout.png` dosyasının alfa kanalı (`alpha.getbbox()`) kontrol edilmeli; eğer dolu alan **60x60 pikselden küçükse** kesim iptal edilip orijinal ürün görseli kullanılmalıdır (`create_product_banner` içinde otomatik uygulanır).

---

## 2. Tipografi ve Tofu (`▢`) Önleyici Temizlik

Standart Windows TrueType fontları (`segoeuib.ttf`, `arialbd.ttf`) renkli Unicode emojileri desteklemez ve bunları içi boş dikdörtgen kutu (`▢` - tofu) olarak çizer.
- Banner üzerine çizilen **tüm metin alanları** (`title`, `badge_text`, `seller_badge_text`, `market_badge`, `feature_text`, `coupon_text`, `installment`, `old_price`, `new_price`) çizimden önce `_clean_ttf()` filtresinden geçirilmelidir:
  ```python
  re.sub(r'[\U00010000-\U0010ffff\u2600-\u27BF\ufe00-\ufe0f\u200d\ufffd]', '', text)
  ```
- İkon ihtiyaçları emoji karakteriyle değil, `split_composer.py` içindeki vektör çizim fonksiyonlarıyla (`draw_vector_bolt`, `draw_vector_shield_check`, `draw_vector_trend_down`, `draw_vector_link`) karşılanmalıdır.

---

## 3. Meme ve Ses Kaynağı Kontrolü

- Seçilen meme videosu (`assets/memes/<meme>.mp4`) diskte mevcut olmalıdır.
- Meme videosunun kendi ses akışı (`Audio:`) varsa harici müzik eklenmez; meme'in orijinal viral sesi korunur.
