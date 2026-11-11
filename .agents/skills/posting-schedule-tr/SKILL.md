---
name: posting-schedule-tr
description: "Türkiye saat dilimine (UTC+3) göre Instagram Reels, YouTube Shorts ve Telegram'da en yüksek organik erişim ve tıklama getiren paylaşım kuşakları rehberi."
---

# Posting Schedule TR (Türkiye Algoritmik Paylaşım Saatleri ve Kuşak Stratejisi)

Bu skill, Türkiye'deki sosyal medya ve e-ticaret kullanıcılarının aktif olduğu saatlere göre günlük paylaşım kuşaklarını ve kategori seçimini optimize eder.

---

## 1. Altın Paylaşım Kuşakları (UTC+3 Türkiye Saati)

| Kuşak | Saat (TSİ) | Platform | Hedef Kitle & Algoritma Durumu | En İyi Ürün Kategorisi |
|---|---|---|---|---|
| **1. Kuşak (Sabah Tech)** | **11:05** | 📺 YouTube Shorts | Masa başı başlangıç, ilk mola | F/P Oyuncu Ekipmanları, Kulaklık, Taşınabilir SSD |
| **2. Kuşak (Öğle Molası / Makyaj)** | **13:05** | 🎵 TikTok (1. Video) | Yemek & alışveriş molası (Kadın / Genç kitle) | **Viral Maskara & Dudak Parlatıcı (Gloss)** (100–350 TL) |
| **3. Kuşak (İkindi F/P Donanım)** | **15:05** | 📺 YouTube Shorts | Çay/kahve molası, donanım meraklıları | F/P Sneaker, Gaming Monitör, Mouse/Klavye |
| **4. Kuşak (Mesai / Okul Çıkışı)** | **18:35** | 🎵 TikTok (2. Video) | Metrobüs, servis, eve dönüş hızlı akış | **Likit Allık, Glotion, Kapatıcı veya F/P Sneaker** |
| **5. Kuşak (Akşam Prime Time Tech)** | **20:05** | 📺 YouTube Shorts | Evde dinlenme, masa başı YouTube gezintisi | Akıllı Saat, Bluetooth Hoparlör, Gamepad |
| **6. Kuşak (Gece Prime Time Makyaj)** | **21:35** | 🎵 TikTok (3. Video) | Yatakta kaydırma, Keşfet (FYP) tepe noktası | **İkonik F/P Parfümler & Gece Makyajı / Lip Oil** |

---

## 2. Frekans ve Anti-Spam Kuralları

- İki paylaşım arasında **en az 45-90 dakika** boşluk bırakılmalıdır (`autopilot_engine.py` içindeki 45 dakikalık mükerrer paylaşım kilidi bunu korur).
- Günde **2 ile 4 video** arası paylaşım, hem Instagram Reels hem de YouTube Shorts algoritmasında kanal otoritesini en üst seviyede tutar.
- Üst üste iki kuşakta **asla aynı alt kategoriden** (Örn: arka arkaya iki termos veya arka arkaya iki mouse) ürün paylaşılmaz (`last_subtype.txt` kontrolü).
