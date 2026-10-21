---
name: video-quality-check
description: "Dikey (9:16) video ve üst banner görsel kalitesini, tipografi hizalamasını, çizgi konumlarını, metin taşmalarını ve video render sağlamlığını denetleyen kalite kontrol rehberi."
---

# Video Quality Check (Görsel ve Video Kalite Güvencesi)

Bu skill, üretilen 1080x1920 dikey split-screen videoların ve 1080x960 üst ürün banner'larının görsel kusursuzluğunu garanti eder.

---

## 1. Banner ve Tipografi Standartları (1080x960 Üst Alan)

### A. Fiyat Kutusu ve Hiyerarşi
- **Fırsat / Yeni Fiyat:** Her zaman banner'ın en baskın, en büyük ve en yüksek kontrastlı öğesidir (Örn: Sarı kutu üzerine siyah kalın font veya koyu arka planda parlak neon yazı).
- **Piyasa / Eski Fiyat Kutusu:** Yeni fiyat kutusundan belirgin şekilde daha küçük ve geri planda olmalıdır.
- **Kırmızı Çizgi Hizalaması (Strike-through):** Eski fiyatın üzerindeki kırmızı çizgi (`draw.line`), fiyat metninin tam düşey merkezinden geçmelidir (`text_bbox` koordinatları hesaplanarak metnin üstünde veya altında kalması önlenmelidir).

### B. Başlık ve Metin Taşması (Text Overflow)
- Ürün başlıkları maksimum 2 satırda tutulmalıdır.
- Uzun marka ve model isimleri için dinamik font küçültme (font scaling) veya `textwrap` uygulanmalıdır.
- Metinler asla ekranın güvenli kenar boşluklarının (safe margins: sol/sağ 40px) dışına taşmamalıdır.

### C. Ürün Görseli ve Dekupe (rembg)
- Ürün görselleri temizlenmiş arka planla (şeffaf PNG) veya beyaz/nötr arka planda merkezi olarak konumlandırılmalıdır.
- Görsel sıkıştırma veya pikselleşme olmamalıdır; en az 600x600 çözünürlük korunmalıdır.

### D. Fiyat Gizleme (Mystery Reveal) ve Spoiler Önleme Kuralı
- **Kart Altı Özellik Rozeti (Feature Pill / Killer Hook):**
  - Ürün görseli altındaki özellik rozetinde (Örn: `⚡ 6 DİLİM İNOX DÖKÜM TOST!`) KESİNLİKLE hiçbir indirimli fiyat tutarı (`3.999 TL vb.`) erken gösterilemez.
  - Bu rozet yalnızca ürünün teknik/fiziksel üstünlüklerini (kapasite, panel tipi, watt, malzeme, pil ömrü vb.) vurgulamak içindir.
  - İndirimli fiyat tutarı videonun ilk 2.85 saniyesinde gizlidir (`??? TL`). Erken fiyat bilgisi vermek animasyonun merak/kanca (suspense & retention) etkisini tamamen yok eder.
  - `product_verifier.py`, `motion_composer.py` ve `split_composer.py` üzerindeki otomatik regex filtreleri rozet metnindeki tüm fiyat kalıntılarını zorunlu olarak ayıklar.

---

## 2. Video ve Ses Derleme Standartları (FFmpeg)

- **Çözünürlük:** 1080 x 1920 (9:16 dikey format).
- **Kare Hızı (FPS):** Sabit 30 FPS.
- **Video Codec:** `libx264` (yuv420p) - Tüm mobil cihazlar ve sosyal medya platformlarıyla %100 uyumluluk.
- **Ses Codec:** `aac` (192 kbps stereo).
- **Ses Seviyesi:** Arka plan meme sesi ve seslendirme (TTS) dengeli olmalı; ses patlaması veya aşırı kısık ses engellenmelidir.

---

## 3. Görsel Doğrulama Testi (Smoke Test)
Yeni bir şablon veya kod değişikliği yapıldığında:
1. Video üretildikten sonra FFmpeg ile örnek bir kare (`output/test_frame.png`) çıkarılmalıdır.
2. Yazıların hizası, fiyat kutularının kontrastı ve çizgi konumu gözle teyit edilmelidir.
