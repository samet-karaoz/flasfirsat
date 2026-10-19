---
name: meme-pool-manager
description: "Viral meme havuzunu (assets/memes) yönetme, sosyal medya linklerinden yeni meme indirme, 1080x960 blur-pad formatına dönüştürme ve MEME_ROTATION_ORDER sırasını düzenleme rehberi."
---

# Meme Pool Manager (Viral Meme Havuzu ve Rotasyon Yönetimi)

Bu skill, `split_composer.py` tarafından kullanılan viral meme kütüphanesinin (`assets/memes/*.mp4`) yönetimini, sıralamasını ve yeni meme ekleme standartlarını belirler.

---

## 1. Rotasyon Mimarisi (`MEME_ROTATION_ORDER` & `meme_history.json`)

- Tüm meme sıralaması `split_composer.py` içindeki `MEME_ROTATION_ORDER` listesinde tutulur.
- Sıradaki meme indeksi ve son kullanılan memeler `data/meme_history.json` dosyasında (`next_index` ve `recent_used`) saklanır.
- **Round-Robin + Cooldown Kuralı:** `select_smart_meme()` sıradaki meme'i seçer; ancak son 3 videoda (`cooldown_set`) kullanılmışsa bir sonrakine atlar.
- Kullanıcı **"Bundan sonraki ilk N videonun meme sıralaması şu olsun"** dediğinde:
  1. İstenen meme dosyaları `MEME_ROTATION_ORDER` listesinin en başına (indeks `0, 1, 2...`) taşınır.
  2. `data/meme_history.json` içinde `"next_index": 0` yapılır ve `"recent_used"` listesinde bu memeler varsa temizlenir (cooldown engeline takılmamaları için).

---

## 2. Yeni Meme Ekleme ve Formatlama Standardı (1080x960)

Instagram Reels, TikTok veya YouTube'dan yeni bir meme ekleneceğinde:

1. **İndirme:** `yt-dlp` (`safe_run_subprocess` ile) kullanılarak video indirilir.
2. **Standartlaştırma (1080x960, 30 FPS, Blur-Pad):**
   - Meme videoları split-screen'in alt yarısını (`1080x960`) doldurur.
   - Orijinal video dikey veya kare ise görüntüyü kesmemek (kafaları/yazıları uçurmamak) için arka plana bulanıklaştırılmış kopya (blur-pad), merkeze ise tam boy orijinal video yerleştirilir:
     ```powershell
     ffmpeg -y -i raw_meme.mp4 -filter_complex "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,boxblur=20:10[bg];[0:v]scale=1080:960:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k assets/memes/yeni_meme.mp4
     ```
3. **Süre Standardı:** İdeal meme süresi **6 ile 15 saniye** arasıdır.
4. **Kayıt:** Dosya `assets/memes/` altına anlamlı bir Türkçe/ASCII isimle (`snake_case.mp4`) kaydedilir ve `split_composer.py` içindeki `MEME_ROTATION_ORDER` listesine eklenir.
