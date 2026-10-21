p = r"C:\Users\Samet\Desktop\Otomasyon\deal_bot.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

target = """    # 0. Akıllı Meme Seçimi (Tek Seferde Seçilir, Mükerrerliği Engeller & Her İki Varyantta Aynı Kalır)
    if not meme_choice:
        chosen_meme = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
    else:"""

replacement = """    # 0. Akıllı Alt Video Seçimi (Format B: Hibrit Model - Kutu Açılış / ASMR Öncelikli, Bulunamazsa Akıllı Meme)
    if not meme_choice:
        try:
            from unboxing_manager import get_deal_unboxing_video
            unboxing_res = get_deal_unboxing_video(deal)
            if unboxing_res:
                chosen_meme, unbox_hook = unboxing_res
                print(f"[Deal Bot] 📦 Format B Devrede: Gerçek ürün kutu açılış/ASMR klibi bağlandı -> {chosen_meme}")
                if not deal.get("reaction_text"):
                    deal["reaction_text"] = unbox_hook
            else:
                chosen_meme = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
                print(f"[Deal Bot] 🎭 Format A Devrede: Akıllı Meme seçildi -> {chosen_meme}")
        except Exception as ex_ub:
            print(f"[Deal Bot] ⚠️ Unboxing motoru istisnası ({ex_ub}), Meme formatına dönülüyor.")
            chosen_meme = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
    else:"""

c_norm = c.replace("\r\n", "\n")
if target in c_norm:
    c_norm = c_norm.replace(target, replacement, 1)
    with open(p, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(c_norm)
    print("deal_bot.py basariyla guncellendi!")
else:
    print("Hedef blok bulunamadi!")
