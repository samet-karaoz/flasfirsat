with open('product_verifier.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    price_el = (
        soup.select_one(".priceToPay") or
        soup.select_one("#corePriceDisplay_desktop_feature_div .a-price") or
        soup.select_one("#corePrice_desktop .a-price") or
        soup.select_one("#corePrice_feature_div .a-price") or
        soup.select_one(".apexPriceToPay .a-offscreen") or
        soup.select_one("#apex_desktop .a-price .a-offscreen") or
        soup.select_one("#priceblock_dealprice") or
        soup.select_one("#priceblock_ourprice") or
        soup.select_one(".a-price .a-offscreen")
    )"""

replacement = """    price_el = (
        soup.select_one(".priceToPay") or
        soup.select_one("#corePriceDisplay_desktop_feature_div .a-price") or
        soup.select_one("#corePrice_desktop .a-price") or
        soup.select_one("#corePrice_feature_div .a-price") or
        soup.select_one(".apexPriceToPay .a-offscreen") or
        soup.select_one("#apex_desktop .a-price .a-offscreen") or
        soup.select_one("#priceblock_dealprice") or
        soup.select_one("#priceblock_ourprice") or
        soup.select_one("#desktop_buybox .a-price .a-offscreen")
    )"""

if target in c:
    c = c.replace(target, replacement)
    with open('product_verifier.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Safely removed global .a-price fallback!")
else:
    print("Target not found, checking with stripped lines")
