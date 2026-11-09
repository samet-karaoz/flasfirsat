import os
import json
import re
import subprocess
import requests
from config import GEMINI_API_KEY, TEMP_DIR, get_curl_cmd, SITE_URL, safe_run_subprocess

MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest"
]

def generate_viral_caption(product_title: str, old_price: str, new_price: str, discount_pct: str, deal_details: str = "", store_url: str = "", bank_campaign: str = "", net_cost: str = "", coupon_info: str = "", deal_code: str = "") -> str:
    """
    Instagram Reels ve TikTok için etkileşimi patlatan, merak uyandıran,
    yoruma teşvik eden açıklama metni (caption) üretir.
    
    YASAL VE ALGORİTMA KURALLARI:
    1. Ticaret Bakanlığı Reklam Kurulu gereği: '#işbirliği #reklam' ibaresi ilk kancanın hemen altında (ilk 2 satırda, fold öncesi) yer alır.
    2. Kesin Etiket Sınırı: Açıklamada TOPLAMDA EN FAZLA 5 ADET ETİKET (HASHTAG) bulunabilir (2 yasal + en fazla 3 kategori etiketi).
    3. Fırsat kodu (#105 vb.) etiket kotasını harcamaması için metin içinde yalın formatta (Fırsat Kodu: 105) verilir.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    coupon_clean = str(coupon_info).strip() if coupon_info else ""
    code_raw = str(deal_code).strip() if deal_code else ""
    code_clean = code_raw.lstrip("#") if code_raw else ""
    
    system_prompt = """Sen Instagram, TikTok ve YouTube Shorts'ta yüz binlerce takipçisi olan, aşırı samimi, sıcak, esprili ve içten bir fırsat sayfası yöneticisisin. Takipçilerinle sanki WhatsApp grubundaki en yakın arkadaşınla konuşuyormuş gibi konuşursun.

Görevin: Verilen indirimli ürün için izleyicinin durup okuyacağı, yapay zeka tarafından yazıldığı ASLA belli olmayan, tamamen insan eliyle yazılmış gibi aşırı samimi, doğal ve kışkırtıcı bir açıklama metni (caption) üretmek.

ÖNEMLİ YAZIM VE YASAL KURALLAR:
1. İLK SATIR (AŞIRI SAMİMİ VE DOĞAL KANCA - HOOK):
   - Asla soğuk veya yapay zeka klişeleri kullanma ('İnanılmaz fırsat kapınızda!', 'Fırsat fırtınası!', 'Kaçırmayın üzülürsünüz!').
   - Kategoriye göre en sıcak, samimi hitapla başla:
     * Kadın bakım / Kozmetik / Saç: "Kızlar koşun, stoklar tükenmeden bu fiyata kapın derim, fiyata inanamayacaksınız 👇" / "Çeyize veya banyoya stok yapmak isteyenler kesinlikle baksın..."
     * Oyuncu / Teknoloji / Gaming: "Beyler şaka değil, bu canavar bu fiyata gerçekten bedavadan biraz pahalı..." / "Setup'ını yenilemek isteyen varsa bu fiyata kaçmaz, stok bitmeden bakın..."
     * Kahve / Mutfak / Yaşam: "Sabahları güne mis gibi kahveyle başlamak isteyenler buraya, fiyatı inanılmaz düşmüş..." / "Mutfakta hayat kurtaran o alet dip fiyata inmiş, arkadaşına haber et..."
     * Genel Fırsatlar: "Fiyatı yanlış girmişler kesin, bu fiyata görünce sepete fırlattım..." / "İhtiyacı olan arkadaşına acil gönder, bu fiyata bir daha asla düşmez 👇"
2. YASAL ZORUNLULUK (REKLAM KURULU UYUMU):
   - Kancanın (ilk satırın) hemen altına MUTLAKA '#işbirliği #reklam' ibaresini ekle.
   - Ticaret Bakanlığı mevzuatı gereği bu etiketler 'devamını gör' katlamasının arkasına (metnin sonuna) saklanamaz, en başta açıkça görünür olmalıdır.
3. FİYAT VE TASARRUF VURGUSU (Eski Fiyat ❌ -> Yeni Fiyat ✅ ve Net Kazanç / İndirim Oranı).
4. Varsa Kupon ve Taksit bilgisini net belirt (🎟️ Kupon Uyarısı, 💳 Peşin fiyatına 3 taksit).
5. Eylem Çağrısı (Samimi Etkileşim Kancası):
   - '👉 Yoruma "LİNK" yaz, satın alma linkini anında DM kutuna gönderelim! 📩'
   - "📌 Fiyat tekrar uçmadan videoyu KAYDET, lazım olur diye arkadaşına GÖNDER! ✈️"
   - "💬 Sizce bu fiyata değer mi, kullanan var mı? Yorumlarda buluşalım 👇"
   - "🔗 Ürün bağlantısı Hikayemizde (Story) ve profilimizdeki bağlantıda aktif!"
   - KESİNLİKLE AÇIKLAMAYA LİNK (URL / HTTP / HTTPS / WWW) YAZMA! Instagram ve TikTok açıklamalarında linkler tıklanamaz.
6. KESİNLİKLE EN FAZLA 5 ETİKET (HASHTAG LİMİTİ):
   - Başta yer alan '#işbirliği #reklam' dahil olmak üzere açıklamada TOPLAMDA EN FAZLA 5 ETİKET bulunabilir.
   - En sona sadece 2-3 adet ürünle doğrudan ilgili kategori etiketi ekle (Örn: #indirim #fırsat #teknoloji).
   - Asla 5'ten fazla etiket yazma!

Sadece açıklamayı yaz, başka hiçbir selamlama, tırnak işareti veya ön ek ekleme."""

    extra_info = ""
    if coupon_clean:
        extra_info += f"\nKupon Bilgilendirmesi (Zorunlu Vurgula): {coupon_clean} (İzleyiciye ürün sayfasındaki kuponu aktif etmesi gerektiğini açıkça yaz)"
    if code_clean:
        extra_info += f"\nFırsat Kodu: {code_clean} (İzleyiciye profilimizdeki sitemizde arama kutusuna {code_clean} yazarak da ürünü saniyeler içinde bulabileceğini belirt)"
    price_clause = f"Eski Fiyat (Doğrulanmış Liste): {old_price}\n" if old_price else "Eski Fiyat: Bilinmiyor (Yalnızca güncel indirimli fiyatı vurgula)\n"
    user_prompt = (
        f"Ürün: {product_title}\n{price_clause}Yeni Fiyat: {new_price}\nİndirim Oranı: {discount_pct}\nDetay: {deal_details}{extra_info}\n"
        f"ÖNEMLİ: Açıklamaya KESİNLİKLE web linki/URL yazma (tıklanmıyor). İzleyiciyi yoruma 'LİNK' yazmaya veya Hikayeye yönlendir.\n"
        f"YASAL VE ETİKET KURALI: İlk satır kancasının hemen altına '#işbirliği #reklam' ekle. Açıklamada bu iki etiket dahil TOPLAMDA EN FAZLA 5 ETİKET yer almalıdır (en sonda 2-3 kategori etiketi, asla 5'i geçme)."
    )

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]}
    }

    req_file = os.path.join(TEMP_DIR, "caption_req.json")
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    def sanitize_caption(text: str) -> str:
        """
        1. Tıklanamayan tüm URL'leri temizler.
        2. Reklam Kurulu kuralına göre '#işbirliği #reklam' ibaresini ilk satır kancasının hemen altına yerleştirir.
        3. Fırsat kodunu (#158 yerine 158) etiket kotasını harcamayacak şekilde temizler.
        4. TOPLAM ETİKET SAYISINI KESİNLİKLE EN FAZLA 5 ADET İLE SINIRLAR (2 yasal + en fazla 3 kategori).
        """
        # Tıklanamayan web linklerini (URL) açıklamadan temizle
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        text = re.sub(r'flasfirsat\.com\.tr\S*', 'profilimizdeki bağlantı', text)

        # Mevcut tüm etiketleri tara
        all_found_tags = re.findall(r'#[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+', text)
        general_tags = []
        for t in all_found_tags:
            tl = t.lower()
            if tl not in ["#işbirliği", "#reklam", "#isbirligi"] and not re.match(r'^#\d+$', t):
                if t not in general_tags:
                    general_tags.append(t)

        # Gövdedeki tüm etiketleri temizle (tekrar ve fazlalıkları önlemek için düzenli yerleştireceğiz)
        cleaned_body = re.sub(r'#[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+', '', text)
        lines = [l.strip() for l in cleaned_body.split('\n') if l.strip()]

        if not lines:
            lines = [f"🔥 {product_title} fırsatı yayında!"]

        hook = lines[0]
        body_lines = lines[1:]

        # Kupon uyarısı gövdede yoksa ekle
        body_full_text = " ".join(body_lines).lower()
        if coupon_clean and "kupon" not in body_full_text:
            body_lines.insert(0, f"🎟️ KUPON BİLGİSİ: Bu fiyata düşmesi için ürün sayfasındaki '{coupon_clean}' kuponunu aktif etmeyi unutmayın!")

        # Fırsat kodu gövdede yoksa etiket formatı OLMADAN ekle
        if code_clean and code_clean.lower() not in body_full_text:
            body_lines.append(f"🔢 Fırsat Kodu: {code_clean} (Profilimizdeki sitede arama kutusuna {code_clean} yazarak da bulabilirsiniz!)")

        # DM ve LİNK yorum kancası yoksa ekle
        if "yoruma" not in body_full_text or "link" not in body_full_text:
            body_lines.append('👉 Yoruma "LİNK" yaz, satın alma linkini anında DM kutuna gönderelim! 📩')

        # Kaydet ve Paylaş kancası yoksa ekle
        if "kaydet" not in body_full_text and "gönder" not in body_full_text:
            body_lines.append("📌 Fiyat tekrar yükselmeden videoyu KAYDET, lazım olur diye arkadaşına GÖNDER! ✈️")

        # Toplam 5 etiket kuralı: 2 adet zorunlu yasal (#işbirliği #reklam) + EN FAZLA 3 ADET kategori etiketi
        selected_content_tags = general_tags[:3]
        if not selected_content_tags:
            selected_content_tags = ["#indirim", "#fırsat", "#keşfet"]

        # Final metin inşası:
        # 1. Satır: Hook (Kanca)
        # 2. Satır: Yasal reklam bildirimi (Fold öncesi)
        # Gövde satırları
        # En son satır: En fazla 3 kategori etiketi (Toplam tam 5 etiket!)
        final_caption = (
            f"{hook}\n"
            f"#işbirliği #reklam\n\n"
            + "\n\n".join(body_lines)
            + f"\n\n{' '.join(selected_content_tags)}"
        )

        # Kesin Güvenlik Kilidi: Toplam etiket sayısı 5'i ASLA geçemez
        tags_check = re.findall(r'#[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+', final_caption)
        if len(tags_check) > 5:
            # 5'ten sonraki fazla etiketleri temizle
            for extra_tag in tags_check[5:]:
                final_caption = re.sub(re.escape(extra_tag) + r'\b', '', final_caption)
            final_caption = re.sub(r'[ \t]+', ' ', final_caption).strip()

        return final_caption

    for model in MODEL_CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        data = None
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                data = r.json()
        except Exception:
            pass

        if not data:
            cmd = get_curl_cmd(["--max-time", "15", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", f"@{req_file}", url])
            res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
            try:
                data = json.loads(res.stdout)
            except Exception:
                continue

        try:
            if data and "candidates" in data and len(data["candidates"]) > 0:
                caption = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return sanitize_caption(caption)
        except Exception:
            continue

    # Fallback Caption if all API models fail
    coupon_line = f"🎟️ KUPON BİLGİSİ: Ürün sayfasındaki '{coupon_clean}' kuponunu aktif etmeyi unutmayın!\n" if coupon_clean else ""
    code_line = f"🔢 Fırsat Kodu: {code_clean} (Sitede arama kutusuna {code_clean} yazarak anında bulabilirsiniz)\n" if code_clean else ""
    old_line = f"❌ Eski Fiyat: {old_price}\n" if old_price else ""
    pct_line = f" ({discount_pct} İndirim)" if discount_pct and discount_pct != "0%" else ""

    fallback = (
        f"🔥 {product_title} fırsatı yayında!\n"
        f"#işbirliği #reklam\n\n"
        f"{old_line}"
        f"✅ Satış Fiyatı: {new_price}{pct_line}\n"
        f"{coupon_line}"
        f"{code_line}\n"
        f"👉 Yoruma \"LİNK\" yaz, ürün linkini anında DM ile gönderelim! 📩\n"
        f"💬 Sizce bu fiyata değer mi, alınır mı? Yorumlarda buluşalım 👇\n"
        f"🔗 Ürün bağlantısı şu an Hikayemizde (Story) ve profilimizdeki bağlantıda aktif! ⚡\n"
        f"📌 Fiyatı tekrar kontrol etmek için videoyu KAYDET, arkadaşına GÖNDER! ✈️\n\n"
        f"#indirim #fırsat #keşfet"
    )
    return sanitize_caption(fallback)


if __name__ == "__main__":
    c = generate_viral_caption(
        product_title="Sinoz Spf50+ Stick Güneş Kremi 4'lü",
        old_price="340 TL",
        new_price="94 TL",
        discount_pct="-72%",
        deal_details="Adeti sadece 94 TL'ye geliyor, normalde tek tanesi 300 TL!",
        coupon_info="Sepette 40 TL Kupon",
        deal_code="#158"
    )
    print("--- ÜRETİLEN AÇIKLAMA ---\n")
    print(c)
    print("\n--- ETİKET KONTROLÜ ---")
    tags = re.findall(r'#[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+', c)
    print(f"Toplam Etiket Sayısı: {len(tags)} (İzin verilen: En fazla 5)")
    print("Etiketler:", tags)
