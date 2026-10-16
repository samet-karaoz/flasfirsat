from deal_hunter import call_gemini

title = "Dell G2422HS 23.8 inç 200Hz 0.5ms Fast IPS Full HD Gaming Monitör"
new_price = "4.449 TL"
old_price = "5.999 TL"
discount_pct = "-26%"
specs = "200Hz yenileme hızı, 0.5 ms tepki süresi, Fast IPS panel, AMD FreeSync Premium, sRGB %99 renk doğruluğu, pivot ve yükseklik ayarlı ayak, HDMI 2.0 ve DisplayPort 1.4"

prompt = f"""Sen viral kısa video (Reels, TikTok, Shorts) içerik üreticisisin.
Verilen indirimli e-ticaret ürününün o anki GERÇEK teknik/fiziksel özelliklerini ve satış fiyatını incele.
İzleyicinin videoda ilk saniyede görüp 'Bu fiyata bu özellik inanılmaz!' diyerek dikkatini çekecek, o ürüne ÖZGÜ, EN VURUCU tek satırlık dikkat çekici başlığı yaz.

ZORUNLU KURALLAR:
1. YALNIZCA bu ürünün gerçek özelliklerini kullan (Asla başka bir ürünün özelliğini uydurma veya yazma!).
2. Ürünün en can alıcı 1 veya 2 teknik özelliğini, varsa fiyat avantajıyla vurucu şekilde birleştir.
3. Maksimum 35 karakter uzunluğunda olsun. Kısa, tok ve büyük harflerle vurucu olsun.
4. Başında veya sonunda gereksiz tırnak, emoji, ön ek veya açıklama olmasın. Sadece tek satır metni döndür.

Örnek Çıktılar:
- Kamera (999 TL): 1.000 TL ALTINA 2K 360° KAMERA!
- Monitör (4.449 TL): 4.449 TL'YE 200Hz 0.5ms FAST IPS!
- Mousepad (659 TL): 90x40 CM SU GEÇİRMEZ MİKRO DOKUMA!
- Airfryer (1.399 TL): 1.400 TL ALTINA 8L DİJİTAL AİRFRYER!

Ürün Başlığı: {title}
Satış Fiyatı: {new_price}
Eski Fiyat: {old_price}
İndirim Oranı: {discount_pct}
Ürün Detayları/Teknik Veriler:
{specs}

SADECE tek satırlık vurucu başlığı döndür:"""

res = call_gemini(prompt, json_mode=False)
print("GEMINI RESULT:", repr(res))
