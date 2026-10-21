with open('product_verifier.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if 'elif live_p > 0:' in line and i > 0 and 'orig_p > 0 and live_p > orig_p * 1.15' in lines[i-3]:
        # replace this block
        pass

with open('product_verifier.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            if orig_p > 0 and live_p > orig_p * 1.15:
                print(f"[Doğrulama] ❌ FİYAT DEĞİŞMİŞ/İNDİRİM BİTMİŞ! (Eski: {orig_p} TL -> Canlı: {live_p} TL). Paylaşım iptal ediliyor.")
                return {"valid": False, "reason": "Fiyat artmış / indirim bitmiş"}
            elif live_p > 0:
                deal["new_price"] = f"{int(live_p):,} TL".replace(",", ".") if live_p.is_integer() else f"{live_p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")"""

replacement = """            if orig_p > 0 and live_p > orig_p * 1.15:
                print(f"[Doğrulama] ❌ FİYAT DEĞİŞMİŞ/İNDİRİM BİTMİŞ! (Eski: {orig_p} TL -> Canlı: {live_p} TL). Paylaşım iptal ediliyor.")
                return {"valid": False, "reason": "Fiyat artmış / indirim bitmiş"}
            elif orig_p > 0 and live_p < orig_p * 0.40:
                print(f"[Doğrulama] ⚠️ Canlı fiyat ({live_p} TL), ürün fiyatından ({orig_p} TL) aşırı düşük (yedek parça/aksesuar tuzağı). Orijinal fiyat korunuyor.")
                live_p = orig_p
                deal["new_price"] = f"{int(orig_p):,} TL".replace(",", ".") if orig_p.is_integer() else f"{orig_p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
            elif live_p > 0:
                deal["new_price"] = f"{int(live_p):,} TL".replace(",", ".") if live_p.is_integer() else f"{live_p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")"""

# normalize line endings for replace
target_crlf = target.replace('\n', '\r\n')
replacement_crlf = replacement.replace('\n', '\r\n')

if target_crlf in content:
    content = content.replace(target_crlf, replacement_crlf)
    print("Replaced CRLF")
elif target in content:
    content = content.replace(target, replacement)
    print("Replaced LF")
else:
    print("Target not found directly, checking partial")

with open('product_verifier.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
