import re

def parse_price_number(price_str: str) -> float:
    """
    '1.219 TL', '4.857,50 TL', '899 TL' gibi metinlerden saf sayısal değeri float olarak döndürür.
    """
    if not price_str:
        return 0.0
    
    # Sadece rakam, nokta ve virgülleri koru
    cleaned = re.sub(r'[^0-9.,]', '', str(price_str))
    if not cleaned:
        return 0.0

    # 1.219,50 formatı veya 1.219 formatı
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned and len(cleaned.split(".")[-1]) == 3:
        # Binlik ayracı olarak nokta (örn: 1.219)
        cleaned = cleaned.replace(".", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except Exception:
        return 0.0

def calculate_campaign_and_net_cost(price_str: str, store_name: str = "Amazon TR") -> dict:
    """
    Türkiye'deki güncel e-ticaret ve banka/fintech kampanyalarına (Nays, Axess, Maximum vb.) göre
    ürünün tahmini NET maliyetini ve kazandıracağı ekstra avantajı hesaplar.
    """
    price_val = parse_price_number(price_str)
    store = (store_name or "").lower()

    if price_val <= 0:
        return {
            "bank_campaign": "Nays ile %10 Nakit İade",
            "net_cost": price_str,
            "benefit_text": "Fırsatı Yakala",
            "savings": "0 TL",
            "installment": "Peşin Fiyatına Taksit"
        }

    # 1. Nays İadesi (%10 nakit iade, maksimum 250 TL)
    nays_refund = min(250.0, price_val * 0.10)
    net_val = max(1.0, price_val - nays_refund)

    # Biçimlendirme
    def fmt(val: float) -> str:
        if val >= 1000:
            return f"{val:,.0f} TL".replace(",", ".")
        return f"{int(round(val))} TL"

    net_cost_str = fmt(net_val)
    savings_str = fmt(nays_refund)

    # Mağazaya göre özel kampanya kurgusu
    if "amazon" in store:
        if price_val >= 2500:
            campaign = "Nays ile 250 TL İade + Prime Kargo"
            installment = f"3 Taksit x {fmt(price_val / 3)}"
        elif price_val >= 1000:
            campaign = f"Nays ile {savings_str} Nakit İade"
            installment = f"3 Taksit x {fmt(price_val / 3)}"
        else:
            campaign = f"Nays ile %10 İade ({savings_str})"
            installment = "Peşin Fiyatına 3 Taksit"
    elif "trendyol" in store:
        if price_val >= 1500:
            campaign = f"Nays ile {savings_str} İade + Kupon"
            installment = f"3 Taksit x {fmt(price_val / 3)}"
        else:
            campaign = f"Nays ile %10 Nakit İade ({savings_str})"
            installment = "Peşin Fiyatına 3 Taksit"
    elif "hepsi" in store:
        if price_val >= 1500:
            campaign = f"Hepsipay & Nays ile {savings_str} İade"
            installment = f"3 Taksit x {fmt(price_val / 3)}"
        else:
            campaign = f"Nays ile %10 Nakit İade ({savings_str})"
            installment = "Peşin Fiyatına 3 Taksit"
    else:
        campaign = f"Nays ile %10 İade ({savings_str})"
        installment = f"3 Taksit x {fmt(price_val / 3)}"

    return {
        "bank_campaign": campaign,
        "net_cost": net_cost_str,
        "benefit_text": f"💳 Net Maliyet: {net_cost_str} ({campaign})",
        "savings": savings_str,
        "installment": installment
    }
