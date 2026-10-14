---
name: ad-compliance-tr
description: "Ticaret Bakanlığı Tüketicinin Korunması ve Piyasa Gözetimi Genel Müdürlüğü ile Reklam Kurulu'nun 'Sosyal Medya Etkileyicileri Tarafından Yapılan Ticari Reklam ve Haksız Ticari Uygulamalar Hakkında Kılavuz'una tam yasal uyum rehberi."
---

# Ad Compliance TR (Sosyal Medya Reklam ve Mevzuat Uyumu)

Bu skill, üretilen ve paylaşılan her içeriğin Türkiye Cumhuriyeti tüketici koruma mevzuatına, Reklam Kurulu ilke kararlarına ve affiliate (gelir ortaklığı) beyan kurallarına %100 uygun olmasını sağlar.

---

## 1. Zorunlu Etiketler ve Konumlandırma

### A. Metin Açıklaması (Caption)
- Paylaşılan içerik bir affiliate (gelir ortaklığı) bağlantısı içeriyorsa veya bir e-ticaret platformuna yönlendiriyorsa, metnin başında veya görünür kısmında şu etiketlerden en az biri **zorunludur**:
  - `#işbirliği`
  - `#reklam`
  - `#ortaklık`
- **Konum:** Bu etiketler onlarca anlamsız etiketin arasına gizlenemez; açıklama metninin görünür alanında açık ve seçik yer almalıdır.

### B. Hikaye (Story) ve Video İçi Görsel Beyan
- Instagram Story veya video üzerinde yönlendirici bağlantı paylaşıldığında (çıkartma ile):
  - Hikaye üzerinde kolayca okunabilir biçimde `#işbirliği` veya `#reklam` ibaresi bulunmalıdır.

---

## 2. Fiyat İndirimi ve İndirimli Satış Kuralları

### A. Gerçek Önceki Fiyat Zorunluluğu
- Fiyat İndirimi Yönetmeliği uyarınca; bir mal veya hizmetin indirimden önceki satış fiyatının tespitinde, **indirimin uygulandığı tarihten önceki otuz gün içinde uygulanan en düşük fiyat** esas alınır.
- Bu nedenle, botumuzun 30 günlük teyit edilmiş fiyat geçmişi olmayan ürünlerde "30 günün en düşüğü" veya yanıltıcı "önceki fiyat" iddialarında bulunması hukuken yasaktır.

### B. "Fiyat Hatası" İddiası Sınırlandırması
- Tüketiciyi yanıltmak amacıyla yapay olarak "fiyat hatası olabilir, koşun" gibi gerçeğe aykırı aciliyet yaratıcı ifadeler kullanılamaz; yalnızca gerçek piyasa verisiyle teyit edilmiş olağanüstü fırsatlarda ölçülü bir dille ifade edilmelidir.

---

## 3. Kod Tarafı Denetim Standardı

`caption_generator.py` ve `sanitize_caption` fonksiyonları her zaman:
1. `#işbirliği` veya `#reklam` etiketinin metinde var olduğunu teyit etmelidir.
2. Toplam hashtag sayısını 3-5 adetle sınırlı tutarak spam algısını ve mevzuat ihlalini önlemelidir.
