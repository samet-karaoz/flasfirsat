---
name: deal-truthfulness
description: "Fiyat, rozet ve ürün verilerinin doğruluğunu garanti eden etik ve yasal kurallar bütünü. Gerçek veriye dayanmayan iddiaları, uydurma piyasa fiyatlarını ve teyit edilmemiş satıcı rozetlerini kesin olarak yasaklar."
---

# Deal Truthfulness (Fırsat Doğruluk ve Dürüstlük Protokolü)

Bu skill, Fırsat Avcısı otomasyonunda üretilen veya paylaşılan tüm içeriklerin (video banner'ları, açıklamalar, rozetler) gerçeğe %100 uygun olmasını sağlar. Takipçi güveni ve tüketici mevzuatına uyum en temel önceliktir.

---

## 1. Altın Kurallar (Asla Taviz Verilmez)

### Kural A: "Son 30 Günün En Düşüğü" Rozeti
- **Şart:** Ürünün yerel veritabanında (`price_tracker.py` veya `watchlist.py`) **en az 30 günlük düzenli fiyat geçmişi kaydı** bulunmalıdır.
- **Yasak:** Sistemde sadece birkaç saatlik veya 1-2 günlük veri varken bu rozet **KESİNLİKLE BASILAMAZ**.
- **Varsayılan Durum:** 30 günlük kayıt yoksa rozet gizlenir veya yerine genel `GÜNÜN FIRSATI` rozeti kullanılır.

### Kural B: Piyasa / Önceki Fiyat (Old Price)
- **Doğrulama:** Üstü çizilecek olan "eski fiyat", sadece e-ticaret sitesinin resmi sayfasından çekilen gerçek önceki fiyattan (`has_verified_old_price=True`) alınabilir.
- **Yasak:** Yapay zeka (LLM) tahminiyle veya "bu ürün genelde şu kadardır" varsayımıyla eski fiyat uydurulamaz.
- **Eski Fiyat Yoksa:** Eski fiyat teyit edilemiyorsa, banner'da "üstü çizili eski fiyat kutusu" gösterilmez; doğrudan net indirimli fiyat dev hero formatında gösterilir.

### Kural C: Satıcı ve Garanti Rozetleri
- **"Resmi Satıcı" Rozeti:** Yalnızca ürün sayfasında satıcının doğrudan platformun kendisi olduğu (ör. "Satıcı: Amazon.com.tr") teyit edilmişse basılabilir.
- **"Doğrulanmış Ürün" / "Resmi Garanti":** Ürün açıklamasında resmi Türkiye distribütör garantisi açıkça yazmıyorsa varsayımsal garanti rozeti basılamaz.

### Kural D: Ürün Özellik Maddesi (Feature Pill)
- **Doğruluk:** Banner'daki hap rozet metni, ürünün gerçek teknik özelliklerinden (Gemini Vision veya sayfa özeti) üretilmelidir.
- **Yasak:** Başlıktaki tek bir kelimeye bakarak ezbere şablon metin (örneğin her monitör kolu metnini monitöre basmak veya her prize '13.500A' yazmak) kesinlikle yasaktır. Bilgi bulunamıyorsa rozet alanı boş bırakılır.

---

## 2. Yayın Öncesi Kontrol Listesi (Checklist)

Her video derleme adımında şu 4 soru EVET olmalıdır:
1. [ ] Satış fiyatı canlı olarak teyit edildi mi ve stok mevcut mu?
2. [ ] Varsa eski fiyat resmi mağaza verisiyle eşleşiyor mu?
3. [ ] Kullanılan rozetler doğrulanmış verilere dayanıyor mu?
4. [ ] Açıklamadaki tasarruf miktarı gerçek matematiksel farkı yansıtıyor mu?
