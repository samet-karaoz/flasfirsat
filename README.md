# 🚀 Viral İndirim & Fırsat Video Otomasyonu (İndirim Kaplanı Formatı)

Bu sistem; Instagram Reels ve TikTok'ta yüksek izlenme ve affiliate/reklam geliri sağlayan **Split-Screen İndirim + Viral Meme Reaksiyon** formatındaki 1080x1920 dikey videoları ve etkileşim patlatan açıklamalarını uçtan uca otomatik üretir.

---

## 📐 Video Mimarisi ve Formatı

* **Format**: 9:16 Dikey Video (1080x1920)
* **Üst Bölüm (1080x960)**: Ultra modern, minimalist fırsat afişi:
  * Ürün adı ve kart içi yüksek çözünürlüklü fotoğraf
  * İndirim rozeti ("GÜNÜN FIRSATI", "DEV İNDİRİM", "ÇÖKÜŞ FİYAT")
  * Kırmızı üstü çizili eski fiyat ve büyük canlı yeşil indirimli fiyat
  * İndirim yüzdesi rozeti (%-50 vb.)
* **Alt Bölüm (1080x960)**: 10 adet hazır viral popüler meme reaksiyon klibi (Bruce Shark zoom, Patrick Bateman, Homelander, Pedro Pascal, Vince McMahon, Walter White, The Rock, Shocked Cat, Cillian Murphy, Christian Bale).
* **Ses**: Viral slowed phonk / TikTok trend beat'leri.
* **Açıklama (Caption)**: Gemini AI tarafından yazılan merak uyandırıcı soru, fiyat karşılaştırması, takipçiyi yoruma sürükleyen tartışma kancası, Telegram/profil linki yönlendirmesi ve popüler hashtag'ler.

---

## 🎬 Nasıl Kullanılır?

### 1. Otomatik Mod (Autonomous Deal Hunter)
İnternetten (Telegram sıcak fırsat kanallarından) en son düşen taze indirimleri kendi bulur, ürün fotoğraflarını indirir, videoyu montajlar ve açıklamayı hazırlar:

```bash
# Tek bir sıcak fırsat videosu ve açıklaması üretir:
python deal_bot.py --auto

# Tek seferde 3 farklı fırsat videosu üretir:
python deal_bot.py --auto --count 3
```

### 2. Kendi Ekran Görüntünle Üret (AI Vision Modu)
Bir e-ticaret sitesinde (Amazon, Hepsiburada, Trendyol vb.) indirim gördün ve ekran görüntüsü aldın:

```bash
python deal_bot.py --image "ekran_goruntusu.png"
```
*(Gemini Vision ekran görüntüsünü okur, ürün adını, eski fiyatı ve yeni fiyatı otomatik doldurarak videoyu derler!)*

### 3. Web Sitesi Linkiyle Üret
```bash
python deal_bot.py --url "https://www.amazon.com.tr/dp/B0..."
```

### 4. Tamamen Manuel Detay Girişi
```bash
python deal_bot.py --manual --title "ASUS RTX 4060 Ti Gaming Sistem" --old "44.999 TL" --new "31.999 TL" --discount "-29%" --badge "GÜNÜN FIRSATI" --hook "SSD ve RAM bedavaya geliyor"
```

### 5. Özel Meme veya Müzik Seçimi (İsteğe Bağlı)
İstediğin özel bir meme klibini belirtebilirsin:
```bash
python deal_bot.py --auto --meme bateman_walk
# Seçenekler: bale_nod, bateman_walk, cillian_murphy, homelander_stare, pedro_pascal, shark_nemo, shocked_cat, the_rock, vince_mcmahon, walter_white
```

---

## 📁 Çıktılar

Tüm hazırlanan içerikler `output/` klasörüne aynı isimle kaydedilir:
* `output/20261012_..._urun_adi.mp4` -> Hazır montajlı 1080x1920 video
* `output/20261012_..._urun_adi_aciklama.txt` -> Kopyalayıp paylaşıma yapıştıracağın hazır açıklama ve etiketler

---

## 🔑 Dosya Yapısı
* [deal_bot.py](file:///c:/Users/Samet/Desktop/Otomasyon/deal_bot.py) : Ana orkestratör CLI motoru.
* [deal_hunter.py](file:///c:/Users/Samet/Desktop/Otomasyon/deal_hunter.py) : Otomatik indirim tarayıcı, Telegram & Vision entegrasyonu.
* [split_composer.py](file:///c:/Users/Samet/Desktop/Otomasyon/split_composer.py) : Üst afiş oluşturucu ve split-screen FFmpeg montaj motoru.
* [caption_generator.py](file:///c:/Users/Samet/Desktop/Otomasyon/caption_generator.py) : Gemini viral açıklama ve etkileşim yazarı.
* `assets/memes/` : 10 adet standart 1080x960 viral tepki klibi.
* `assets/audio/` : Viral arka plan müzikleri.
