import os
import sys
import subprocess
import random
import re
from PIL import Image, ImageDraw
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR, safe_run_subprocess
from split_composer import (
    get_font, wrap_text, MEMES_DIR, AUDIO_DIR,
    AVAILABLE_MEMES, AVAILABLE_AUDIOS,
    create_product_banner, create_reaction_hook_overlay,
    select_smart_meme
)

def create_top3_card(
    rank: int,
    product_image_path: str,
    title: str,
    old_price: str,
    new_price: str,
    discount_pct: str,
    output_path: str,
    store_name: str = "Amazon TR",
    bank_campaign: str = "",
    net_cost: str = "",
    installment: str = "",
    feature_text: str = "",
    is_lowest_30d: bool = False,
    has_verified_old_price: bool = True,
    seller_badge_text: str = "",
    coupon_text: str = "",
    market_badge: str = ""
) -> str:
    """
    Kullanıcı talebi doğrultusunda tekli videolardaki standart ajans kalitesindeki
    şablon ile birebir aynı tasarımı (fiyat kutuları, DM bandı, rozetler) üretir.
    """
    badge_title = f"#{rank} GÜNÜN BOMBASI" if rank == 1 else f"#{rank} GÜNÜN FIRSATI"
    return create_product_banner(
        product_image_path=product_image_path,
        title=title,
        old_price=old_price,
        new_price=new_price,
        discount_pct=discount_pct,
        badge_text=badge_title,
        store_name=store_name,
        bank_campaign=bank_campaign,
        net_cost=net_cost,
        installment=installment,
        feature_text=feature_text,
        is_lowest_30d=is_lowest_30d,
        has_verified_old_price=has_verified_old_price,
        seller_badge_text=seller_badge_text,
        coupon_text=coupon_text,
        market_badge=market_badge,
        output_path=output_path
    )

def draw_top3_step_tabs(card_path: str, rank: int) -> str:
    """
    Ürün kartının en üstüne (y=18..54) Instagram Story tarzı 3 adımlı
    canlı sayaç sekmeleri ekler ([ 1. FIRSAT (AKTİF) ] [ 2. FIRSAT (SIRADA) ] [ 3. FIRSAT (SIRADA) ]).
    İzleyicinin gözü hemen 3 fırsat olduğunu anlar ve video sonuna kadar izlenir.
    """
    img = Image.open(card_path).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    f_bold = get_font("segoeuib", 17)
    f_idle = get_font("segoeuib", 16)

    W = 1080
    margin = 54
    gap = 12
    tab_w = (W - (margin * 2) - (gap * 2)) // 3
    tab_h = 36
    tab_y1 = 20
    tab_y2 = tab_y1 + tab_h

    tabs_data = [
        {"active_title": "1. FIRSAT (AKTİF)", "color": (245, 158, 11, 245), "fg": (15, 23, 42)},
        {"active_title": "2. FIRSAT (AKTİF)", "color": (14, 165, 233, 245), "fg": (15, 23, 42)},
        {"active_title": "3. FIRSAT (AKTİF)", "color": (244, 63, 94, 245), "fg": (255, 255, 255)}
    ]

    for i in range(3):
        x1 = margin + i * (tab_w + gap)
        x2 = x1 + tab_w
        is_active = (i + 1 == rank)
        is_past = (i + 1 < rank)

        if is_active:
            draw.rounded_rectangle((x1, tab_y1, x2, tab_y2), radius=10, fill=tabs_data[i]["color"], outline=(255, 255, 255, 220), width=2)
            lbl = tabs_data[i]["active_title"]
            draw.text(((x1 + x2) // 2, (tab_y1 + tab_y2) // 2), lbl, font=f_bold, fill=tabs_data[i]["fg"], anchor="mm")
        elif is_past:
            draw.rounded_rectangle((x1, tab_y1, x2, tab_y2), radius=10, fill=(6, 78, 59, 210), outline=(16, 185, 129, 160), width=1)
            lbl = f"{i+1}. FIRSAT (GEÇTİ)"
            draw.text(((x1 + x2) // 2, (tab_y1 + tab_y2) // 2), lbl, font=f_idle, fill=(167, 243, 208), anchor="mm")
        else:
            draw.rounded_rectangle((x1, tab_y1, x2, tab_y2), radius=10, fill=(15, 23, 42, 170), outline=(71, 85, 105, 110), width=1)
            lbl = f"{i+1}. FIRSAT (SIRADA)"
            draw.text(((x1 + x2) // 2, (tab_y1 + tab_y2) // 2), lbl, font=f_idle, fill=(148, 163, 184), anchor="mm")

    img.convert("RGB").save(card_path, "PNG")
    return card_path


def create_dynamic_reaction_hook(rank: int, title: str, output_path: str) -> str:
    """Her ürün için renk ve metin değiştiren akıllı orta reaksiyon kancası üretir."""
    # Kısa ürün kancası üret (Örn: STANLEY TERMOS, MONİTÖR KOLU, BUHARLI ÜTÜ)
    t_clean = re.sub(r"[^\w\s]", " ", title).strip()
    words = [w for w in t_clean.split() if len(w) > 2]
    short_hook = " ".join(words[:3]).upper() if words else "FIRSAT ÜRÜNÜ"
    if len(short_hook) > 22:
        short_hook = short_hook[:22].strip()

    reaction_text = f"#{rank} • {short_hook} FİYATINI GÖREN BEN:"
    return create_reaction_hook_overlay(reaction_text, output_path=output_path)


def build_top3_video(
    deals: list,
    meme_name: str = None,
    output_filename: str = "top3_deals.mp4"
) -> str:
    """
    Gelişmiş Sinematik Top 3 Fırsat Derleme Videosu (5 Katmanlı Dinamik Hareket):
    1. Üstte Story Tarzı 3'lü İlerleme Sekmesi ([ 1. FIRSAT (AKTİF) ] [ 2. FIRSAT (SIRADA) ]...).
    2. Kartlar arası kesintisiz ve şık Whip-Slide sola kayma efekti (xfade=transition=slideleft:0.35s).
    3. Her ürün değiştiğinde senkronize değişen Dinamik Orta Kanca Bandı (1/3 -> 2/3 -> 3/3).
    4. Kesintisiz alt viral meme ve dinamik neon ilerleme çubuğu.
    5. Xiaomi Redmi Note 11 Pro Android donanım metaverisi.
    """
    if len(deals) < 3:
        raise ValueError("Top 3 videosu için en az 3 fırsat gereklidir!")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1. Meme videosunu sıra sıra rotasyon havuzundan seç (Round-Robin)
    if meme_name and os.path.exists(os.path.join(MEMES_DIR, meme_name)):
        chosen_meme = meme_name
    else:
        chosen_meme = select_smart_meme(title="Top 3 Fırsat Bülteni")

    bottom_meme_path = os.path.join(MEMES_DIR, chosen_meme)
    print(f"[Top3] 🎬 Seçilen Tek Kesintisiz Meme: {chosen_meme}")

    # 2. Meme süresini ve ses durumunu al + Anti-Hash Rastgele Milisaniye Kırpması
    p = safe_run_subprocess(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    raw_duration = float(m.group(3)) + int(m.group(2))*60 if m else 11.50
    rnd_trim = round(random.uniform(0.15, 0.40), 3)
    duration = max(6.0, round(raw_duration - rnd_trim, 3))
    has_audio = "Audio:" in p.stderr
    print(f"[Top3] ⏱️ Toplam Video Süresi: {duration:.2f}s (Anti-Hash Kırpma: -{rnd_trim}s, Orijinal Ses: {has_audio})")

    # Geçiş hesaplamaları (Slide-Left Whip Swipe: 0.35 sn)
    trans_dur = 0.35
    seg_dur = duration / 3.0
    t1 = round(seg_dur + trans_dur, 2)
    t2 = round(seg_dur + trans_dur, 2)
    t3 = round(seg_dur + 0.15, 2)
    off1 = round(seg_dur, 2)
    off2 = round(seg_dur * 2.0, 2)

    # 3. Üst kartları üret ve Story tarzı 3'lü Sayaç Sekmelerini çiz
    card_files = []
    reaction_files = []
    contrasting_themes = ["emerald_gold", "cyber_gaming", "apple_warm"]

    for rank in [1, 2, 3]:
        deal = deals[rank - 1]
        card_out = os.path.join(TEMP_DIR, f"top3_motion_card_{rank}.png")
        badge_title = f"#{rank} GÜNÜN BOMBASI" if rank == 1 else f"#{rank} GÜNÜN FIRSATI"
        raw_img = deal.get("image_path") or deal.get("local_img") or deal.get("image_url") or ""
        if raw_img and not raw_img.startswith("http") and not os.path.isabs(raw_img):
            cand_img = os.path.join(BASE_DIR, raw_img)
            if os.path.exists(cand_img):
                raw_img = cand_img

        theme_pick = contrasting_themes[rank - 1]
        create_product_banner(
            product_image_path=raw_img,
            title=deal.get("title", f"Fırsat Ürünü #{rank}"),
            old_price=deal.get("old_price", ""),
            new_price=deal.get("new_price", ""),
            discount_pct=deal.get("discount_pct", "-30%"),
            badge_text=badge_title,
            store_name=deal.get("store_name", "Amazon TR"),
            bank_campaign=deal.get("bank_campaign", ""),
            net_cost=deal.get("net_cost", ""),
            installment=deal.get("installment", ""),
            feature_text=deal.get("killer_hook") or deal.get("feature_pill", ""),
            is_lowest_30d=deal.get("is_lowest_30d", False),
            has_verified_old_price=deal.get("has_verified_old_price", bool(deal.get("old_price"))),
            seller_badge_text=deal.get("seller_badge", ""),
            coupon_text=deal.get("coupon_info", ""),
            market_badge=deal.get("market_badge", ""),
            deal_code=deal.get("deal_code", ""),
            theme_name=theme_pick,
            output_path=card_out
        )

        # Kartın en üstüne canlı sekme sayaçlarını çiz
        draw_top3_step_tabs(card_out, rank)
        card_files.append(card_out)

        # Her ürüne özel dinamik orta kanca bandı üret
        react_out = os.path.join(TEMP_DIR, f"top3_dyn_reaction_{rank}.png")
        create_dynamic_reaction_hook(rank, deal.get("title", ""), react_out)
        reaction_files.append(react_out)

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # 4. Dynamic Progress Bar (Neon İlerleme Çubuğu)
    progress_bar_filter = (
        f"color=c=0x0F172A@0.8:s=1080x14:d={duration:.2f}[pbg];"
        f"color=c=0xFF5722:s=1080x14:d={duration:.2f}[pfill];"
        f"[stacked][pbg]overlay=0:1906[with_pbg];"
        f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{duration:.2f})':y=1906[v]"
    )

    # 5. FFmpeg Montajı (Whip-Slide Geçişleri + Reaksiyon Crossfade + Punch-in Zoom):
    rnd_bright = round(random.uniform(-0.012, 0.012), 4)
    rnd_sat = round(random.uniform(0.985, 1.025), 4)
    rnd_contrast = round(random.uniform(0.99, 1.015), 4)
    scale_bottom = (
        f"scale=w='1080*(1+0.05*max(0,1-t))':h='960*(1+0.05*max(0,1-t))':eval=frame,"
        f"crop=1080:960,"
        f"eq=brightness={rnd_bright}:saturation={rnd_sat}:contrast={rnd_contrast}"
    )

    filter_complex = (
        f"[0:v]settb=AVTB,fps=30,scale=1080:960[c0];"
        f"[1:v]settb=AVTB,fps=30,scale=1080:960[c1];"
        f"[2:v]settb=AVTB,fps=30,scale=1080:960[c2];"
        f"[c0][c1]xfade=transition=slideleft:duration={trans_dur}:offset={off1:.2f}[top_m1];"
        f"[top_m1][c2]xfade=transition=slideleft:duration={trans_dur}:offset={off2:.2f}[top];"
        f"[4:v]settb=AVTB,fps=30[r0];"
        f"[5:v]settb=AVTB,fps=30[r1];"
        f"[6:v]settb=AVTB,fps=30[r2];"
        f"[r0][r1]xfade=transition=fade:duration=0.25:offset={off1:.2f}[rm1];"
        f"[rm1][r2]xfade=transition=fade:duration=0.25:offset={off2:.2f}[reaction];"
        f"[3:v]{scale_bottom}[bottom_raw];"
        f"[bottom_raw][reaction]overlay=0:0[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"{progress_bar_filter}"
    )

    import datetime as _dt
    iso_now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(t1), "-i", card_files[0],
        "-loop", "1", "-t", str(t2), "-i", card_files[1],
        "-loop", "1", "-t", str(t3), "-i", card_files[2],
        "-i", bottom_meme_path,
        "-loop", "1", "-t", str(t1), "-i", reaction_files[0],
        "-loop", "1", "-t", str(t2), "-i", reaction_files[1],
        "-loop", "1", "-t", str(t3), "-i", reaction_files[2],
        "-filter_complex", filter_complex,
        "-map", "[v]"
    ]

    if has_audio:
        cmd += ["-map", "3:a", "-c:a", "aac", "-b:a", "192k"]

    cmd += [
        "-map_metadata", "-1",
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        "-brand", "mp42",
        "-metadata", "com.android.version=13",
        "-metadata", "com.android.manufacturer=Xiaomi",
        "-metadata", "com.android.model=Redmi Note 11 Pro",
        "-metadata:s:v:0", "handler_name=VideoHandle",
        "-metadata:s:a:0", "handler_name=SoundHandle",
        "-metadata", f"creation_time={iso_now}",
        "-movflags", "+faststart+use_metadata_tags",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        output_path
    ]

    res = safe_run_subprocess(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Top3] 🎬 Video başarıyla üretildi (Dinamik Whip-Slide & Sekme Sayaçlı): {output_path}")
        return output_path
    else:
        print("[Top3] FFmpeg hatası:", res.stderr)
        raise RuntimeError(f"Video derlenemedi: {res.stderr}")


def generate_top3_caption(deals: list) -> str:
    """Top 3 videosu için Fırsat Kodu (#10X) destekli viral açıklama metni üretir."""
    d1 = deals[0]
    d2 = deals[1]
    d3 = deals[2]
    c1 = f" [KOD: {d1.get('deal_code')}]" if d1.get("deal_code") else ""
    c2 = f" [KOD: {d2.get('deal_code')}]" if d2.get("deal_code") else ""
    c3 = f" [KOD: {d3.get('deal_code')}]" if d3.get("deal_code") else ""

    caption = (
        f"🔥 GÜNÜN EN İYİ 3 İNDİRİMİ RESMEN ÇÖKTÜ!\n\n"
        f"🥉 #3{c3}: {d3.get('title')[:35]}...\n"
        f"   💸 {d3.get('old_price')} ➔ {d3.get('new_price')} ({d3.get('discount_pct')})\n\n"
        f"🥈 #2{c2}: {d2.get('title')[:35]}...\n"
        f"   💸 {d2.get('old_price')} ➔ {d2.get('new_price')} ({d2.get('discount_pct')})\n\n"
        f"🥇 #1{c1}: {d1.get('title')[:35]}...\n"
        f"   💸 {d1.get('old_price')} ➔ {d1.get('new_price')} ({d1.get('discount_pct')})\n\n"
        f"👉 Ürün kodunu (#101 vb.) profilimizdeki sitemizin arama kutusuna yazarak veya Hikayemizden direkt ürüne ulaşabilirsiniz! 🌐\n"
        f"🔗 Tüm linkler profilimizdeki sitede ve Telegram kanalımızda (@flasfirsat)!\n\n"
        f"#işbirliği #reklam #indirim #fırsat #teknoloji #kampanya #keşfet"
    )
    return caption

if __name__ == "__main__":
    mock_deals = [
        {"title": "Sony PS5 DualSense Kol Beyaz", "old_price": "3.499 TL", "new_price": "2.299 TL", "discount_pct": "-34%", "local_img": ""},
        {"title": "SteelSeries Arctis Nova 1 Kulaklık", "old_price": "2.199 TL", "new_price": "1.349 TL", "discount_pct": "-38%", "local_img": ""},
        {"title": "Logitech G G102 Lightsync Mouse", "old_price": "899 TL", "new_price": "499 TL", "discount_pct": "-45%", "local_img": ""}
    ]
    out = build_top3_video(mock_deals)
    print("Generated Top 3 Video:", out)
    print("\n--- CAPTION ---\n", generate_top3_caption(mock_deals))
