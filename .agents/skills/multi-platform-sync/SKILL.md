---
name: multi-platform-sync
description: "Tek bir indirim fırsatının aynı anda 5 farklı yüzeye (Instagram Reels, YouTube Shorts, Instagram Story, Telegram/WhatsApp Kanalı ve Web Vitrini + Fırsat Kodu) uyumlu CTA ve formatlarla senkronize üretimi rehberi."
---

# Multi-Platform Sync (5 Yüzeyli Senkronize İçerik ve Fırsat Kodu Mimarisi)

Bu skill, yakalanan her fırsatın tek bir komutta 5 farklı platformun kurallarına ve kullanıcı alışkanlıklarına tam uyumlu şekilde üretilmesini ve senkronize edilmesini sağlar.

---

## 1. Platforma Özel Banner ve CTA Ayrımı

Instagram ve YouTube Shorts'ta link paylaşım kuralları farklı olduğu için `deal_bot.py` her fırsat için **iki ayrı banner ve iki ayrı video** üretir:

1. **Instagram Reels Varyantı (`<base_name>.mp4`):**
   - Alt CTA Bandı: `Ürün linki PROFİLDE & HİKAYEDE • KOD: #10X`
   - İzleyiciyi profildeki bio linkine (Web Vitrini) ve aktif Instagram Hikayesine yönlendirir.
2. **YouTube Shorts Varyantı (`<base_name>_youtube.mp4`):**
   - Alt CTA Bandı: `İndirim linkine BİO'DAN ulaşın • KOD: #10X`
   - YouTube kanal açıklaması ve vitrin linkine yönlendirir.
3. **Instagram Story Kartı (`story_<id>.jpg` - 1080x1920):**
   - `story_composer.py` tarafından üretilir.
   - İçinde interaktif **Anket Çıkartması Alanı (`y: 1350..1500`)** ve doğrudan tıklanabilir **Link Çıkartması Alanı (`y: 1535..1715`)** hazır ayrılmıştır.

---

## 2. Fırsat Kodu (`#101`, `#102`...) ve Web Vitrini Senkronizasyonu

- Her fırsata `web_showcase.get_next_deal_code()` ile sıralı ve benzersiz bir **Fırsat Kodu** (`#101`, `#102`...) atanır.
- Bu kod aynı anda:
  1. Instagram Reels üst banner'ına,
  2. YouTube Shorts üst banner'ına,
  3. Instagram Story kartına,
  4. Video açıklama metnine (`caption_text`),
  5. Web Vitrini (`data/deals.json` ve `index.html`) arama kutusuna
  işlenir. Böylece videoyu birkaç gün sonra izleyen bir takipçi bile vitrinde `#104` yazarak ürünü saniyeler içinde bulabilir.
