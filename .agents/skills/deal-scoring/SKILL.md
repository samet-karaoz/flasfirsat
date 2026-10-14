---
name: deal-scoring
description: "Taranan yüzlerce indirim arasından hangi ürünlerin öncelikli olarak video yapılacağını belirleyen puanlama, kategori çeşitliliği ve performans ağırlıklandırma rehberi."
---

# Deal Scoring (Fırsat Puanlama ve Seçim Algoritması)

Bu skill, botun rastgele ürün seçmesini engelleyerek her zaman en yüksek izlenme ve en yüksek satış potansiyeline sahip fırsatların video haline getirilmesini yönetir.

---

## 1. Puanlama Kriterleri ve Ağırlıklar

Her aday ürün için 0-100 arasında bir `Deal Score` hesaplanır:

| Kriter | Ağırlık | Açıklama |
| :--- | :--- | :--- |
| **İndirim Oranı** | %35 | %25 altı düşük puan, %40+ çok yüksek puan alır. |
| **Marka & Ürün Popülerliği** | %25 | Bilinen markalar (Sony, Philips, Stanley, Apple, Logitech vb.) bilinmeyen ürünlere göre önceliklidir. |
| **Satıcı Güvenilirliği** | %20 | Satıcısı doğrudan Amazon / Resmi Distribütör olan ürünler +20 puan kazanır. |
| **Fiyat Düşüş Derinliği** | %10 | Fiyatın TL cinsinden net düşüş miktarı (örn: 1.000 TL+ net kâr). |
| **Kupon / Ek Avantaj** | %10 | Sayfada kupon veya banka/Nays ek indirimi varsa bonus puan alır. |

---

## 2. Çeşitlilik ve Tekrar Koruması (Anti-Fatigue)

Takipçilerin sıkılmaması ve sayfanın monotonlaşmaması için zorunlu filtreler:
1. **Ard Arda Aynı Alt Kategori Yasağı:** Son paylaşılan video bir "Monitör Kolu" ise, bir sonraki video kesinlikle bir monitör kolu olamaz; farklı bir alt kategoriye (kulaklık, termos, kahve makinesi vb.) geçilir.
2. **Aynı Ürün Tekrarı:** Son 7 gün içinde paylaşılan ürünler geçmiş listesinden (`history_deals.json`) elenir.
3. **Meme ve Müzik Rotasyonu:** Üst üste aynı meme videosu veya aynı fon müziği seçilmez; `AVAILABLE_MEMES` havuzundan rotasyonlu seçim yapılır.

---

## 3. Performans Geri Bildirim Döngüsü
- `performance_tracker.py` dosyasına kaydedilen tıklama, izlenme ve etkileşim verilerine göre en çok ilgi gören kategorilerin (Örn: Gaming Ekipmanları veya Trend Ev Aletleri) seçim puanı zaman içinde otomatik artırılır.
