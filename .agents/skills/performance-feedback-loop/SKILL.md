---
name: performance-feedback-loop
description: "Yayınlanan videoların izlenme, kaydetme ve etkileşim verilerini (performance_log.json) takip ederek hangi ürün kategorisi, meme ve kanca (hook) yapısının daha yüksek dönüşüm getirdiğini deal-scoring ağırlıklarına yansıtma rehberi."
---

# Performance Feedback Loop (Performans Geri Bildirimi ve Öz-Öğrenme Döngüsü)

Bu skill, `performance_tracker.py` ve `data/performance_log.json` üzerinden paylaşılan her fırsatın performansını izler ve gelecekteki ürün seçimi (`deal-scoring`) ile görsel tema seçimini veriye dayalı olarak optimize eder.

---

## 1. Kaydedilen Metrikler (`performance_tracker.py`)

Her üretilen ve paylaşılan fırsat için şu veriler kayıt altına alınır:
- Ürün başlığı, alt kategorisi (`subtype`), indirim yüzdesi (`discount_pct`) ve net TL tasarrufu (`savings_tl`).
- Kullanılan viral meme (`meme_name`), renk şablonu (`banner_theme`) ve reaksiyon kancası (`reaction_hook`).
- Paylaşım saati ve kuşağı (`slot_name`).
- Platform bazlı yayın durumu (Instagram Reels, YouTube Shorts, Telegram, Web Vitrini).

---

## 2. Ağırlık Güncelleme Kuralları (`deal-scoring` Entegrasyonu)

- **Yüksek Kaydetme (Save) Alan Kategoriler:** Stanley/Termos, Gaming Ekipman (Mouse, Kulaklık, Monitör) ve Mutfak/Airfryer ürünlerinde kaydetme oranı ortalamanın üzerindeyse `calculate_deal_viral_score` içinde kategori çarpanı (`+15..+25 puan`) korunur veya artırılır.
- **Düşük Etkileşimli Ürün Filtresi:** Arka arkaya düşük etkileşim alan jenerik/markasız ürünler otomatik olarak elenir; yalnızca bilinen A+ markalar ve doğrulanmış piyasa en ucuz fiyatları önceliklendirilir.
