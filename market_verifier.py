import os
import re
import json
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from config import DATA_DIR
from deal_hunter import parse_price_to_float

CACHE_FILE = os.path.join(DATA_DIR, "market_price_cache.json")
CACHE_TTL = 86400  # 24 saat

def _load_cache() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_cache(cache: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Market Verifier] Önbellek yazılamadı: {e}")

def _clean_search_query(title: str) -> str:
    """Arama motorunun tam modeli bulabilmesi için parantezleri ve gereksiz kelimeleri ayıklar."""
    if not title:
        return ""
    # Parantez içlerini ve teknik standart kodlarını sadeleştir
    t = re.sub(r'\(.*?\)', ' ', title)
    t = re.sub(r'\[.*?\]', ' ', t)
    # İlk 5 anlamlı kelimeyi al
    words = [w for w in t.split() if len(w) > 1 and not w.startswith(('http', '%', '₺'))]
    return " ".join(words[:5])

def verify_market_price(product_title: str, current_price) -> dict:
    """
    Ürünün Akakçe üzerindeki piyasa en ucuz fiyatını doğrular.
    Piyasanın altındaysa rozet ve psikolojik tetikleyici metin üretir.
    deal-truthfulness skill kuralına uygun: Yalnızca gerçek ve doğrulanmış veriyle çalışır.
    """
    cur_val = parse_price_to_float(str(current_price)) if isinstance(current_price, (str, int, float)) else 0.0
    if not product_title or cur_val <= 0:
        return {"verified": False, "is_market_lowest": False, "badge_text": "", "savings_vs_market": 0}

    cache = _load_cache()
    cache_key = f"{_clean_search_query(product_title)}_{int(cur_val)}"
    now = time.time()

    if cache_key in cache:
        item = cache[cache_key]
        if now - item.get("time", 0) < CACHE_TTL:
            return item.get("data", {})

    clean_q = _clean_search_query(product_title)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    result = {
        "verified": False,
        "is_market_lowest": False,
        "market_lowest": 0.0,
        "current_price": cur_val,
        "savings_vs_market": 0.0,
        "badge_text": "",
        "highlight_text": "",
        "source": "akakce"
    }

    try:
        q_enc = urllib.parse.quote(f"site:akakce.com {clean_q} En Ucuz")
        url = f"https://html.duckduckgo.com/html/?q={q_enc}"

        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            snippets = soup.select(".result__snippet")

            prices_found = []
            for s in snippets:
                text = s.get_text()
                # 'En Ucuz 1.148,00 TL', 'En Ucuz %9 1.999,00 TL' veya '... incele, 1.454,00 TL'den başlayan'
                matches = re.findall(r'(?:En\s*Ucuz\s*(?:%\d+\s*)?|incele,\s*)([\d\.]+,\d{2}|[\d\.]+)\s*TL', text, re.IGNORECASE)
                for p_str in matches:
                    try:
                        raw_p = p_str.replace(".", "").replace(",", ".")
                        val = float(raw_p)
                        if val > 10:  # makul bir fiyat eşiği
                            prices_found.append(val)
                    except Exception:
                        pass

            if prices_found:
                market_p = min(prices_found)
                diff = market_p - cur_val

                result["verified"] = True
                result["market_lowest"] = market_p
                result["savings_vs_market"] = diff

                if diff >= 50:
                    diff_int = int(round(diff))
                    result["is_market_lowest"] = True
                    result["badge_text"] = f"PİYASANIN {diff_int:,} TL ALTINDA".replace(",", ".")
                    result["highlight_text"] = f"🔥 Akakçe piyasa verilerine göre şu an Türkiye'nin en dip fiyatında (Tam {diff_int:,} TL daha ucuz)!".replace(",", ".")
                elif diff >= 0:
                    result["is_market_lowest"] = True
                    result["badge_text"] = "TÜRKİYE'DE EN DİP FİYAT"
                    result["highlight_text"] = "🔥 Akakçe verilerine göre şu an Türkiye genelinde en dip fiyatta!"
                else:
                    result["is_market_lowest"] = False
                    result["badge_text"] = ""

                print(f"[Market Verifier] ✅ Piyasa Doğrulandı: {clean_q} -> Akakçe En Ucuz: {market_p:.2f} TL | Bizim Fiyat: {cur_val:.2f} TL (Fark: {diff:+.2f} TL)")

    except Exception as e:
        print(f"[Market Verifier] Doğrulama hatası ({clean_q}): {e}")

    # Önbelleğe kaydet
    cache[cache_key] = {"time": now, "data": result}
    _save_cache(cache)

    return result

if __name__ == "__main__":
    test_title = "North Bayou NB F80 Monitör Kolu"
    test_price = 799.0
    res = verify_market_price(test_title, test_price)
    print("Test Sonucu:", json.dumps(res, indent=2, ensure_ascii=False))
