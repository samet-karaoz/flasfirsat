import os
import re
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
from dotenv import load_dotenv

load_dotenv()

# Affiliate Kimlik ve Etiketleri (.env üzerinden okunur)
AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "").strip() or "flasfirsat04-21"
TRENDYOL_AFFILIATE_TAG = os.getenv("TRENDYOL_AFFILIATE_TAG", "").strip()
HEPSIBURADA_AFFILIATE_TAG = os.getenv("HEPSIBURADA_AFFILIATE_TAG", "").strip()

# Affiliate Ağları (Admitad / Gelir Ortakları / ReklamAction vb.)
GELIR_ORTAKLARI_SUBID = os.getenv("GELIR_ORTAKLARI_SUBID", "").strip()
ADMITAD_WEBSITE_ID = os.getenv("ADMITAD_WEBSITE_ID", "").strip()

def detect_store(url: str) -> str:
    """URL'den e-ticaret mağazasını tespit eder."""
    if not url:
        return "Bilinmeyen"
    u = url.lower()
    if "amazon.com.tr" in u or "amzn." in u:
        return "Amazon TR"
    if "trendyol.com" in u or "ty.gl" in u:
        return "Trendyol"
    if "hepsiburada.com" in u or "app.hb.biz" in u:
        return "Hepsiburada"
    if "n11.com" in u:
        return "N11"
    if "ciceksepeti.com" in u:
        return "ÇiçekSepeti"
    if "teknosa.com" in u:
        return "Teknosa"
    if "mediamarkt.com.tr" in u:
        return "MediaMarkt"
    return "Diğer"

def resolve_redirect_url(url: str, timeout: int = 5) -> str:
    """Kısaltılmış yönlendirme linklerini (amzn.to, ty.gl, app.hb.biz vb.) çözer."""
    if not url:
        return ""
    url_str = url.strip()
    short_domains = ["amzn.to", "ty.gl", "app.hb.biz", "bit.ly", "t.me", "fenom.io", "link.tl"]
    if any(sd in url_str.lower() for sd in short_domains):
        try:
            res = requests.head(
                url_str,
                allow_redirects=True,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            if res.url and res.url != url_str:
                return res.url
        except Exception:
            pass
    return url_str

def clean_tracking_params(url: str) -> str:
    """Üçüncü taraf takip parametrelerini (ref, crid, utm_*, fbclid vb.) temizler."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        junk_keys = [
            "ref", "ref_", "crid", "sprefix", "keywords", "th", "psc",
            "fbclid", "gclid", "gbraid", "wbraid", "_gl",
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"
        ]
        for jk in junk_keys:
            qs.pop(jk, None)
        new_query = urlencode(qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return url

def get_affiliate_url(url: str, store_name: str = "") -> str:
    """
    Herhangi bir ürün linkini ilgili mağazanın resmi affiliate (gelir ortaklığı) linkine dönüştürür.
    Amazon TR, Trendyol ve Hepsiburada mağazalarını otomatik destekler.
    """
    if not url:
        return ""

    resolved_url = resolve_redirect_url(url)
    cleaned_url = clean_tracking_params(resolved_url)
    store = store_name or detect_store(cleaned_url)

    # 1. Amazon Türkiye
    if store == "Amazon TR" or "amazon.com.tr" in cleaned_url:
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", cleaned_url, re.IGNORECASE)
        if asin_match:
            asin = asin_match.group(1).upper()
            return f"https://www.amazon.com.tr/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
        sep = "&" if "?" in cleaned_url else "?"
        return f"{cleaned_url}{sep}tag={AMAZON_AFFILIATE_TAG}"

    # 2. Trendyol
    if store == "Trendyol" or "trendyol.com" in cleaned_url:
        if TRENDYOL_AFFILIATE_TAG:
            sep = "&" if "?" in cleaned_url else "?"
            return f"{cleaned_url}{sep}utm_source=aff_{TRENDYOL_AFFILIATE_TAG}&utm_medium=affiliate&utm_campaign={TRENDYOL_AFFILIATE_TAG}"
        # İleride Gelir Ortakları / Admitad ağı eklenirse:
        if GELIR_ORTAKLARI_SUBID:
            encoded_target = quote(cleaned_url, safe="")
            return f"https://gelirortaklari.com/go?subid={GELIR_ORTAKLARI_SUBID}&url={encoded_target}"
        return cleaned_url

    # 3. Hepsiburada
    if store == "Hepsiburada" or "hepsiburada.com" in cleaned_url:
        if HEPSIBURADA_AFFILIATE_TAG:
            sep = "&" if "?" in cleaned_url else "?"
            return f"{cleaned_url}{sep}hb_partner={HEPSIBURADA_AFFILIATE_TAG}&utm_source=affiliate"
        if GELIR_ORTAKLARI_SUBID:
            encoded_target = quote(cleaned_url, safe="")
            return f"https://gelirortaklari.com/go?subid={GELIR_ORTAKLARI_SUBID}&url={encoded_target}"
        return cleaned_url

    # 4. Diğer Mağazalar (N11, Teknosa vb. için affiliate ağ köprüsü)
    if GELIR_ORTAKLARI_SUBID:
        encoded_target = quote(cleaned_url, safe="")
        return f"https://gelirortaklari.com/go?subid={GELIR_ORTAKLARI_SUBID}&url={encoded_target}"

    return cleaned_url

def is_affiliate_active(store_name: str) -> bool:
    """Belirtilen mağaza için aktif bir affiliate kimliği olup olmadığını bildirir."""
    s = store_name.lower()
    if "amazon" in s:
        return bool(AMAZON_AFFILIATE_TAG)
    if "trendyol" in s:
        return bool(TRENDYOL_AFFILIATE_TAG or GELIR_ORTAKLARI_SUBID)
    if "hepsiburada" in s:
        return bool(HEPSIBURADA_AFFILIATE_TAG or GELIR_ORTAKLARI_SUBID)
    return bool(GELIR_ORTAKLARI_SUBID)

def get_affiliate_status() -> dict:
    """Tüm platformların gelir ortaklığı konfigürasyon özetini döner."""
    return {
        "Amazon TR": {
            "status": "AKTİF" if AMAZON_AFFILIATE_TAG else "Eksik",
            "tag": AMAZON_AFFILIATE_TAG or "Belirtilmemiş",
            "source": "Resmi Amazon Associates"
        },
        "Trendyol": {
            "status": "AKTİF" if (TRENDYOL_AFFILIATE_TAG or GELIR_ORTAKLARI_SUBID) else "Beklemede (10k Takipçi Hedefi)",
            "tag": TRENDYOL_AFFILIATE_TAG or "(Henüz girilmedi)",
            "source": "Influencer Programı / Gelir Ortakları"
        },
        "Hepsiburada": {
            "status": "AKTİF" if (HEPSIBURADA_AFFILIATE_TAG or GELIR_ORTAKLARI_SUBID) else "Beklemede (10k Takipçi Hedefi)",
            "tag": HEPSIBURADA_AFFILIATE_TAG or "(Henüz girilmedi)",
            "source": "İş Ortaklığı / Gelir Ortakları"
        }
    }
