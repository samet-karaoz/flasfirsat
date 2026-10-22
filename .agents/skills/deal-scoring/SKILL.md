---
name: deal-scoring
description: "Taranan yüzlerce indirim arasından hangi ürünlerin öncelikli olarak video yapılacağını belirleyen puanlama, kategori çeşitliliği ve performans ağırlıklandırma rehberi."
---

# Deal Scoring (Fırsat Puanlama ve Seçim Algoritması)

Bu skill, botun rastgele veya niş ürün seçmesini engelleyerek her zaman **en geniş kitleye hitap eden (Mass-Appeal)**, en yüksek izlenme ve en yüksek satış potansiyeline sahip fırsatların video haline getirilmesini yönetir.

---

## 1. 1. ÖNCELİK VE KURAL: GENİŞ KİTLEYE HİTAP (MASS-APPEAL DIRECTIVE)

Her aday ürünün öncelikle **kitlesel talep ve bilinirlik** filtresinden geçmesi zorunludur:
- **Hedef Kitle:** Milyonlarca insanın evinde, cebinde, masasında kullanabileceği veya görünce heves edeceği genel tüketici elektroniği, popüler kahve/mutfak aletleri, Stanley termos, gaming ekipmanları.
- **Yasaklı Niş Ürünler:** Sanayi aparatları, yedek parça, filtre kiti, conta, spesifik araba parçası, profesyonel sunucu kablosu gibi dar kitle ürünleri indirim oranı %90 olsa bile **0 puan alır ve elenir.**

---

## 2. Puanlama Kriterleri ve Ağırlıklar

Her aday ürün için 0-100 arasında bir `Deal Score` hesaplanır:

| Kriter | Ağırlık | Açıklama |
| :--- | :--- | :--- |
| **Geniş Kitleye Hitap (Kitlesellik)** | **%35 (1. Öncelik)** | Tüketici elektroniği, trend mutfak, popüler gaming ve termos gibi herkesin ilgisini çeken kategoriler tam puan alır. |
| **İndirim Oranı & Derinliği** | **%25** | %30-%50 arası yüksek oranlar ve 500 TL+ net TL tasarrufu. |
| **Marka Bilinirliği (Tier-1)** | **%20** | A-Sınıfı küresel markalar (Apple, Sony, Philips, Stanley, Logitech, Karaca, Anker vb.). |
| **Satıcı Güvenilirliği** | **%10** | Doğrudan Amazon TR veya Resmi Distribütör yetkili satıcısı. |
| **Kupon / Ek Avantaj** | **%10** | Kupon, peşin fiyatına taksit veya Prime hızlı kargo avantajı. |

---

## 3. Çeşitlilik ve Tekrar Koruması (Anti-Fatigue)

Takipçilerin sıkılmaması ve sayfanın monotonlaşmaması için zorunlu filtreler:
1. **Ard Arda Aynı Alt Kategori Yasağı:** Son paylaşılan video bir "Tost Makinesi" ise, bir sonraki video kesinlikle bir tost makinesi olamaz; farklı bir alt kategoriye (kulaklık, termos, gaming mouse, kahve makinesi vb.) geçilir.
2. **Aynı Ürün Tekrarı:** Son 7 gün içinde paylaşılan ürünler geçmiş listesinden (`history_deals.json`) elenir.
3. **Müzik ve Görsel Çeşitliliği:** Warm ambient müzik ve markanın kendi resmi B-Roll renk paleti kullanılır.

---

## 4. Performans Geri Bildirim Döngüsü
- `performance_tracker.py` dosyasına kaydedilen tıklama, izlenme ve etkileşim verilerine göre en çok ilgi gören kitlesel kategorilerin seçim puanı zaman içinde otomatik artırılır.
