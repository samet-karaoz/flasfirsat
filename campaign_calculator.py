import re

def parse_price_number(price_str: str) -> float:
    """
    '1.219 TL', '4.857,50 TL', '899 TL' gibi metinlerden saf sayısal değeri float olarak döndürür.
    """
    if not price_str:
        return 0.0
    
    cleaned = re.sub(r'[^0-9.,]', '', str(price_str))
    if not cleaned:
        return 0.0

    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned and len(cleaned.split(".")[-1]) == 3:
        cleaned = cleaned.replace(".", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except Exception:
        return 0.0

def calculate_campaign_and_net_cost(price_str: str, store_name: str = "Amazon TR") -> dict:
    """
    Ürünün mağaza avantajını (Prime, Hızlı Kargo vb.) ve taksit imkanını hesaplar.
    Nays tamamen kaldırılmıştır; sadece net ve gerçek satın alma koşulları sunulur.
    """
    price_val = parse_price_number(price_str)
    store = (store_name or "").lower()

    def fmt(val: float) -> str:
        if val >= 1000:
            return f"{val:,.0f} TL".replace(",", ".")
        return f"{int(round(val))} TL"

    installment = "Peşin Fiyatına 3 Taksit"
    if price_val >= 900:
        installment = f"Peşin Fiyatına 3 Taksit x {fmt(price_val / 3)}"

    if "amazon" in store:
        campaign = "Prime ile Hızlı & Ücretsiz Kargo"
    elif "trendyol" in store:
        campaign = "Trendyol Güvencesi"
    elif "hepsi" in store:
        campaign = "Hepsiburada Satıcı Güvencesi"
    else:
        campaign = "Resmi Satıcı Güvencesi"

    return {
        "bank_campaign": campaign,
        "net_cost": "",
        "benefit_text": f"⚡ {installment} • 📦 {campaign}",
        "savings": "",
        "installment": installment
    }
