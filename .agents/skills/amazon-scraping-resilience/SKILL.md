---
name: amazon-scraping-resilience
description: "Amazon TR ürün sayfalarından CAPTCHA'ya takılmadan canlı fiyat, stok, kupon, resmi satıcı rozeti ve yüksek çözünürlüklü ürün görseli çekme ve doğrulama rehberi."
---

# Amazon Scraping Resilience (Amazon TR Dayanıklı Veri ve Görsel Çekimi)

Bu skill, `deal_hunter.py` ve `product_verifier.py` modüllerinin Amazon Türkiye (`amazon.com.tr`) sayfalarından veri çekerken bot korumasına takılmamasını ve hiçbir ürün verisini (özellikle HD ürün görselini ve kuponları) kaçırmamasını sağlar.

---

## 1. Yüksek Çözünürlüklü Görsel Yakalama Sırası (`image_url`)

Amazon ürün sayfalarında görsel seçicileri kategoriye göre değişebilir. `product_verifier.py` ve `deal_hunter.py` şu öncelik sırasıyla görsel aramalıdır:

1. `#landingImage` veya `#imgBlkFront` etiketindeki **`data-old-hires`** özniteliği (Doğrudan 1500px HD görsel verir).
2. Aynı etiketlerdeki **`data-a-dynamic-image`** JSON sözlüğü (İçindeki en yüksek çözünürlüklü URL seçilir).
3. Etiketin standart `src` özniteliği (URL içindeki `._AC_SX300_.` gibi küçültme ekleri `._AC_SL1500_.` ile değiştirilerek HD'ye yükseltilir).
4. Sayfa üstverisindeki `meta[property="og:image"]` etiketi.

İndirilen görselin boyutu mutlaka kontrol edilmeli (`> 1.5 KB`), boş veya 1x1 piksel placeholder görseller reddedilmelidir.

---

## 2. Bot Koruması (CAPTCHA) ve Başlık Rotasyonu

- İsteklerde gerçekçi Türkçe masaüstü ve mobil `User-Agent` başlıkları (`Accept-Language: tr-TR,tr;q=0.9`) kullanılır.
- Yanıt içinde `"api-services-support@amazon.com"`, `"validateCaptcha"` veya `"Robot Check"` tespit edilirse:
  1. Farklı bir `User-Agent` (Mobil Safari / Chrome Android) ile 1 kez yedek istek atılır.
  2. Hâlâ CAPTCHA dönüyorsa sahte/eski fiyatla video üretmek yerine fırsat güvenli şekilde atlanır ve Telegram'a uyarı düşülür.

---

## 3. Fiyat, Kupon ve Satıcı Ayrıştırma

- **Güncel Fiyat:** `span.priceToPay`, `#corePriceDisplay_desktop_feature_div .a-price-whole`, `#corePrice_feature_div` sırasıyla kontrol edilir.
- **Eski/Liste Fiyatı:** `span[data-a-strike="true"] .a-offscreen` üzerinden alınır. Güncel fiyattan en az **%8 daha yüksek** değilse eski fiyat gösterilmez.
- **Kupon:** `#couponBadgeRegularVpc`, `label[id*="coupon"]` içinde `%` veya `TL` indirimi aranır ve sadece metin kısmı (emojisiz) `coupon_info` alanına yazılır.
