import os
import json
import subprocess
from config import GEMINI_API_KEY, TEMP_DIR, get_curl_cmd

MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest"
]

def generate_viral_caption(product_title: str, old_price: str, new_price: str, discount_pct: str, deal_details: str = "", store_url: str = "", bank_campaign: str = "", net_cost: str = "") -> str:
    """
    Instagram Reels ve TikTok için etkileşimi patlatan, merak uyandıran,
    yoruma teşvik eden açıklama metni (caption) ve viral hashtag'ler üretir.
    Banka kampanyası ve net maliyet bilgisini de içerir.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    system_prompt = """Sen Instagram ve TikTok'ta milyonlarca izlenen viral fırsat ve indirim sayfalarını yöneten dahi bir sosyal medya uzmanısın.

Görevin: Verilen indirimli ürün için izleyicinin durup okuyacağı, yoruma ve paylaşıma koşacağı bir Reel/TikTok açıklaması yazmak.

Açıklama Kuralları:
1. İlk satır: Dikkat çekici bir soru veya iddialı bir hook (Örn: "DDR5 sistem bedavaya mı geliyor?!", "Bu fiyata alan yaşadı!").
2. Fiyat avantajını açıkça göster (Eski Fiyat ❌ -> Yeni Fiyat ✅ ve İndirim Oranı).
3. Varsa Banka/İade Kampanyası ile Net Maliyeti vurgula (Örn: "💳 Nays ile %10 iadeyle Net 1.097 TL!").
4. Yoruma teşvik: Tartışma yaratacak bir soru sor ("Sizce bu fiyata değer mi, yoksa çöp mü?", "Bu paraya daha iyisi var mı?").
5. Eylem Çağrısı (CTA): Biyografideki linke veya Telegram'a yönlendir ("Satın alma linki profilimizdeki sitede ve Telegram kanalımızda!").
6. Hashtag Kuralı: KESİNLİKLE EN FAZLA 5 ADET etiket yaz (Asla 5'ten fazla yazma! Örn: #indirim #fırsat #teknoloji #gaming #keşfet).

Sadece açıklamayı yaz, başka hiçbir açıklama veya ön ek ekleme."""

    extra_info = f"\nBanka Kampanyası: {bank_campaign}\nNet Maliyet: {net_cost}" if net_cost else ""
    user_prompt = f"Ürün: {product_title}\nEski Fiyat: {old_price}\nYeni Fiyat: {new_price}\nİndirim Oranı: {discount_pct}\nDetay: {deal_details}{extra_info}\nÜrün Linki: {store_url}"

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]}
    }

    req_file = os.path.join(TEMP_DIR, "caption_req.json")
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    def sanitize_max_hashtags(text: str) -> str:
        """Metindeki hashtag sayısını kesinlikle maksimum 5 ile sınırlar."""
        import re
        tags = re.findall(r"(#[^\s#]+)", text)
        if len(tags) > 5:
            extra_tags = tags[5:]
            for t in extra_tags:
                text = re.sub(re.escape(t) + r"\b", "", text)
            # Fazla boşlukları temizle
            text = re.sub(r"[ \t]+", " ", text).strip()
        return text

    for model in MODEL_CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        cmd = get_curl_cmd(["--max-time", "15", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", f"@{req_file}", url])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        
        try:
            data = json.loads(res.stdout)
            if "candidates" in data and len(data["candidates"]) > 0:
                caption = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return sanitize_max_hashtags(caption)
        except Exception:
            continue

    # Fallback Caption if all API models fail (Tam 5 etiket)
    net_line = f"💳 {bank_campaign} ile Net Maliyet: {net_cost}\n" if net_cost else ""
    fallback = (
        f"🔥 {product_title} fiyatı çöktü!\n\n"
        f"❌ Eski Fiyat: {old_price}\n"
        f"✅ Yeni Fiyat: {new_price} ({discount_pct} İndirim)\n"
        f"{net_line}\n"
        f"{deal_details}\n\n"
        f"Sizce bu fiyata akar mı? Alacak arkadaşına hemen gönder 👇\n"
        f"🔗 Satın alma linki hikayede ve profildeki linkte!\n\n"
        f"#indirim #fırsat #teknoloji #kampanya #keşfet"
    )
    return sanitize_max_hashtags(fallback)

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
