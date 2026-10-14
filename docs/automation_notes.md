# Otomatik Yayın Notları (TikTok & Instagram)

## TikTok — Content Posting API (resmi)

TikTok'un resmi bir **Content Posting API**'si var (developers.tiktok.com). İki modu bulunuyor:

| Mod | Ne yapar | Denetim (audit) |
|-----|----------|-----------------|
| **Upload (Taslak)** | Video, TikTok uygulamasında bildirim/taslak olarak düşer. Paylaşımı kullanıcı uygulamadan tamamlar (trend müzik eklenebilir). | Daha kolay |
| **Direct Post** | Video doğrudan profilde yayınlanır. | Zorunlu. Denetlenmemiş uygulamalarda videolar sadece **gizli (SELF_ONLY)** olarak yayınlanır. |

Kurallar ve sınırlar:
- Uygulama kaydı + `video.publish` / `video.upload` izinleri + kullanıcı OAuth onayı gerekir.
- TikTok UX kuralları; gizlilik seçiminin kullanıcı tarafından yapılmasını, önizleme gösterilmesini ve ticari içerik beyanını (marka/affiliate içerik) şart koşar. Bu yüzden insan onaysız tam otomatik yayın kurallara aykırı düşebilir. **Telegram'dan onay butonu** ile yarı otomatik akış önerilir.
- Kullanıcı başına günlük gönderim sınırı vardır.

Kaçınılması gerekenler: Selenium/Playwright ile giriş yaparak yükleme, resmi olmayan kütüphaneler. Bunlar TikTok şartlarına aykırıdır ve hesabın kapatılmasına yol açabilir.

## Instagram — Graph API (`instagram_publisher.py`)

Resmi API ile yapılan paylaşımlar, algoritmada elle yapılanlardan farklı muamele görmez. Asıl riskler şunlar:

1. **Trend müzik eklenemez.** API ile Instagram müzik kütüphanesi kullanılamaz, sadece videodaki kendi ses kullanılır. Bu da erişimi düşürebilir.
2. **Tekrarlayan şablon / orijinallik.** Instagram, birbirine çok benzeyen ve "aggregator" tarzı içeriklerin erişimini kısıyor. Hook, meme ve şablon çeşitliliği gerekir.
3. **Aşırı sık paylaşım.** API limiti 24 saatte 50 gönderidir. Pratikte günde 2-4 Reel yeterlidir; daha fazlası spam sinyali verir.
4. **Token süresi.** Uzun ömürlü erişim token'ı yaklaşık 60 günde biter, yenilenmesi gerekir.
5. **Video herkese açık bir URL'de olmalı** (barındırma gerekir).
6. **Yanlış fiyat riski.** Telegram'da elle kontrol olmadan yayına çıkar. Yayın öncesi fiyat/stok doğrulaması (`product_verifier.py`) zorunlu tutulmalıdır.
7. **Reklam beyanı.** Açıklamada `#reklam` / `#işbirliği` bulunmalı (otomatik ekleniyor).

## Önerilen akış

Video üretilir → Telegram'a önizleme + **[Onayla] [İptal]** butonları → onaylanınca:
- Instagram: Graph API ile doğrudan Reel paylaşımı
- TikTok: Content Posting API ile **taslak** olarak gönderim (trend müzik uygulamadan eklenip paylaşılır)
