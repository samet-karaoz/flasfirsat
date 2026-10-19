---
name: posting-schedule-tr
description: "Türkiye saat dilimine (UTC+3) göre Instagram Reels, YouTube Shorts ve Telegram'da en yüksek organik erişim ve tıklama getiren paylaşım kuşakları rehberi."
---

# Posting Schedule TR (Türkiye Algoritmik Paylaşım Saatleri ve Kuşak Stratejisi)

Bu skill, Türkiye'deki sosyal medya ve e-ticaret kullanıcılarının aktif olduğu saatlere göre günlük paylaşım kuşaklarını ve kategori seçimini optimize eder.

---

## 1. Altın Paylaşım Kuşakları (UTC+3 Türkiye Saati)

| Kuşak | İdeal Saat Aralığı | Hedef Kitle Durumu | En İyi Ürün Kategorileri |
|---|---|---|---|
| **1. Kuşak (Sabah / Kafein & Ofis)** | **10:00 – 10:45** | İşe/okula başlangıç, masa başı mola | Termos (Stanley), Kahve Makinesi, Ofis/Bilgisayar Aksesuarları, Kişisel Bakım |
| **2. Kuşak (Öğle Molası - Ana Pik)** | **12:15 – 13:00** | Öğle yemeği ve alışveriş molası | Mutfak & Ev Aletleri (Airfryer, Blender), Süpermarket/Deterjan, Genel Teknoloji |
| **3. Kuşak (Akşamüstü / Mesai Çıkışı)** | **17:30 – 18:30** | Toplu taşıma, eve dönüş yolu | Kulaklık, Powerbank, Giyim/Ayakkabı, Kamp & Outdoor |
| **4. Kuşak (Prime Time - Rekor Etkileşim)** | **20:00 – 21:30** | Evde dinlenme, uzun Reels/Shorts kaydırma | Gaming & Setup (Monitör, Mouse, Klavye, PS5), Fiyat Hataları (%40+ Dev İndirimler), TOP 3 Liste Videoları |

---

## 2. Frekans ve Anti-Spam Kuralları

- İki paylaşım arasında **en az 45-90 dakika** boşluk bırakılmalıdır (`autopilot_engine.py` içindeki 45 dakikalık mükerrer paylaşım kilidi bunu korur).
- Günde **2 ile 4 video** arası paylaşım, hem Instagram Reels hem de YouTube Shorts algoritmasında kanal otoritesini en üst seviyede tutar.
- Üst üste iki kuşakta **asla aynı alt kategoriden** (Örn: arka arkaya iki termos veya arka arkaya iki mouse) ürün paylaşılmaz (`last_subtype.txt` kontrolü).
