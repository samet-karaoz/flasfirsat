import os
import json
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
    yoruma teşvik eden açıklama metni (caption) ve viral hashtag'ler üretir.
    Banka kampanyası, kupon bilgilendirmesi, fırsat kodu (#10X) ve net maliyet bilgisini de içerir.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    coupon_clean = str(coupon_info).strip() if coupon_info else ""
    code_clean = str(deal_code).strip() if deal_code else ""
    
    system_prompt = """Sen Instagram, TikTok ve YouTube Shorts'ta yüz binlerce takipçisi olan, aşırı samimi, doğal ve popüler bir fırsat sayfası yöneticisisin.

Görevin: Verilen indirimli ürün için izleyicinin durup okuyacağı, yapay zeka tarafından yazıldığı ASLA belli olmayan, tamamen insan eliyle yazılmış gibi doğal, samimi ve kışkırtıcı bir açıklama metni (caption) üretmek.

ÖNEMLİ YAZIM KURALLARI:
1. İLK SATIR (SERT VE DOĞAL KANCA - HOOK):
   - Asla yapay zeka klişeleri kullanma ('İnanılmaz fırsat kapınızda!', 'Fırsat fırtınası!', 'Kaçırmayın üzülürsünüz!').
   - Tamamen gerçek bir insanın arkadaşına yazacağı gibi merak uyandırıcı, doğrudan ve net ol:
     * "Şaka gibi bir fiyata düşmüş, ihtiyacı olan arkadaşına acil haber et 👇"
     * "Fiyatı görünce fake sandım ama Amazon direkt kendisi satıyor..."
     * "Bu fiyata bu ayarda ekipman bulmak artık imkansız gibi bir şeydi."
     * "Grupta paylaştılar baktım gerçekten bu fiyata düşmüş, stok bitmeden bakın."
2. FİYAT AVANTAJINI GÖSTER (Eski Fiyat ❌ -> Yeni Fiyat ✅ ve İndirim Oranı).
3. Varsa Kupon ve Taksit bilgisini net belirt (🎟️ Kupon Uyarısı, 💳 Peşin fiyatına 3 taksit).
4. Eylem Çağrısı (Kaydet & Paylaş & Yorum):
   - "💬 Sizce bu fiyata değer mi, kullanan var mı? Yorumlarda buluşalım 👇"
   - "📌 Fiyat tekrar artmadan videoyu KAYDET, indirim arayan arkadaşına GÖNDER! ✈️"
   - "🔗 Ürün linki Hikayemizde (Story) ve profildeki sitede aktif!"
5. En fazla 4-5 odaklı etiket (#indirim #teknoloji #gaming #fırsat). En sona zorunlu '#işbirliği #reklam' ekle.

Sadece açıklamayı yaz, başka hiçbir selamlama, tırnak işareti veya ön ek ekleme."""


    extra_info = ""
    if coupon_clean:
        extra_info += f"\nKupon Bilgilendirmesi (Zorunlu Vurgula): {coupon_clean} (İzleyiciye ürün sayfasındaki kuponu aktif etmesi gerektiğini açıkça yaz)"
    if code_clean:
        extra_info += f"\nFırsat Kodu: {code_clean} (İzleyiciye profilimizdeki sitemizde arama kutusuna {code_clean} yazarak da ürünü saniyeler içinde bulabileceğini belirt)"
    price_clause = f"Eski Fiyat (Doğrulanmış Liste): {old_price}\n" if old_price else "Eski Fiyat: Bilinmiyor (Yalnızca güncel indirimli fiyatı vurgula)\n"
    user_prompt = f"Ürün: {product_title}\n{price_clause}Yeni Fiyat: {new_price}\nİndirim Oranı: {discount_pct}\nDetay: {deal_details}{extra_info}\nÜrün Linki: {store_url}\nYasal Zorunluluk: Açıklamanın en sonuna mutlaka '#işbirliği #reklam' etiketlerini ekle."

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]}
    }

    req_file = os.path.join(TEMP_DIR, "caption_req.json")
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    def sanitize_caption(text: str) -> str:
        """Metindeki hashtag sayısını dengeler, kupon uyarısını, fırsat kodunu ve #işbirliği zorunluluğunu garanti eder."""
        import re
        if coupon_clean and "kupon" not in text.lower():
            coupon_notice = f"\n🎟️ KUPON BİLGİSİ: Bu fiyata düşmesi için ürün sayfasındaki '{coupon_clean}' kuponunu aktif etmeyi unutmayın!\n"
            lines = text.split("\n")
            if len(lines) > 2:
                lines.insert(2, coupon_notice.strip())
                text = "\n".join(lines)
            else:
                text = coupon_notice + text
        if code_clean and code_clean.lower() not in text.lower():
            code_notice = f"🔢 Fırsat Kodu: {code_clean} (Profilimizdeki sitede arama kutusuna {code_clean} yazarak da bulabilirsiniz!)"
            if "#işbirliği" in text:
                text = text.replace("#işbirliği", f"{code_notice}\n\n#işbirliği", 1)
            else:
                text += f"\n{code_notice}"
        # Yasal uyum: #işbirliği yoksa ekle
        if "#işbirliği" not in text.lower():
            text += "\n\n#işbirliği #reklam"
        tags = re.findall(r"(#[^\s#]+)", text)
        # Reklam etiketleri ve fırsat kodu (#105 vb.) hariç en fazla 5 genel etiket
        general_tags = [t for t in tags if t.lower() not in ["#işbirliği", "#reklam"] and not re.match(r"^#\d+$", t)]
        if len(general_tags) > 5:
            for t in general_tags[5:]:
                text = re.sub(re.escape(t) + r"\b", "", text)
            text = re.sub(r"[ \t]+", " ", text).strip()
        return text

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
        f"🔥 {product_title} fırsatı yayında!\n\n"
        f"{old_line}"
        f"✅ Satış Fiyatı: {new_price}{pct_line}\n"
        f"{coupon_line}"
        f"{code_line}"
        f"🚨 Sınırlı süreli fırsat, stoklar tükenmeden inceleyin!\n\n"
        f"💬 Sizce bu fiyata değer mi, alınır mı? Yorumlarda buluşalım 👇\n"
        f"🔗 Ürün linki şu an Hikayemizde (Story) ve profilimizdeki sitede aktif! 24 saat dolmadan Hikayemizden direkt ürüne gidebilirsiniz ⚡\n"
        f"📌 Fiyatı tekrar kontrol etmek için videoyu KAYDET, arkadaşına GÖNDER! ✈️\n"
        f"🌐 Canlı Vitrin: {SITE_URL}?utm_source=instagram&utm_medium=reels\n\n"
        f"#işbirliği #reklam #indirim #fırsat #teknoloji"
    )
    return sanitize_caption(fallback)


if __name__ == "__main__":
    c = generate_viral_caption(
        product_title="Sinoz Spf50+ Stick Güneş Kremi 4'lü",
        old_price="340 TL",
        new_price="94 TL",
        discount_pct="-72%",
        deal_details="Adeti sadece 94 TL'ye geliyor, normalde tek tanesi 300 TL!"
    )
    print("--- ÜRETİLEN AÇIKLAMA ---\n")
    print(c)
