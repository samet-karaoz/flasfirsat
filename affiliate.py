import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

load_dotenv()

def get_affiliate_url(url: str, store_name: str = "") -> str:
    """
    Ürün linkine kullanıcının affiliate (gelir ortaklığı) kimlik kodunu ekler.
    Amazon TR, Trendyol ve Hepsiburada mağazalarını otomatik algılar ve
    üçüncü taraf takip kodlarını temizleyerek resmi affiliate formatına dönüştürür.
    """
    if not url:
        return ""

    url_str = url.strip()

    # 1. Amazon Türkiye
    amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG", "").strip() or "flasfirsat04-21"
    if "amazon.com.tr" in url_str or "amzn." in url_str:
        try:
            parsed = urlparse(url_str)
            qs = parse_qs(parsed.query)
            # Eski veya yabancı tag'leri temizle, bizimkini ekle
            qs["tag"] = [amazon_tag]
            # Gereksiz şişkin parametreleri temizle
            for junk in ["ref", "ref_", "crid", "sprefix", "keywords"]:
                qs.pop(junk, None)
            new_query = urlencode(qs, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        except Exception:
            sep = "&" if "?" in url_str else "?"
            return f"{url_str}{sep}tag={amazon_tag}"

    # 2. Trendyol
    trendyol_tag = os.getenv("TRENDYOL_AFFILIATE_TAG", "").strip()
    if "trendyol.com" in url_str or "ty.gl" in url_str:
        if trendyol_tag:
            try:
                parsed = urlparse(url_str)
                qs = parse_qs(parsed.query)
                qs["utm_source"] = [f"aff_{trendyol_tag}"]
                qs["utm_medium"] = ["affiliate"]
                qs["utm_campaign"] = [trendyol_tag]
                new_query = urlencode(qs, doseq=True)
                return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            except Exception:
                sep = "&" if "?" in url_str else "?"
                return f"{url_str}{sep}utm_source=aff_{trendyol_tag}&utm_medium=affiliate"
        return url_str

    # 3. Hepsiburada
    hb_tag = os.getenv("HEPSIBURADA_AFFILIATE_TAG", "").strip()
    if "hepsiburada.com" in url_str or "app.hb.biz" in url_str:
        if hb_tag:
            try:
                parsed = urlparse(url_str)
                qs = parse_qs(parsed.query)
                qs["hb_partner"] = [hb_tag]
                qs["utm_source"] = ["affiliate"]
                new_query = urlencode(qs, doseq=True)
                return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            except Exception:
                sep = "&" if "?" in url_str else "?"
                return f"{url_str}{sep}hb_partner={hb_tag}"
        return url_str

    return url_str

