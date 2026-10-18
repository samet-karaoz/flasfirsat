import os
import sys
import subprocess
import random
import re
from PIL import Image, ImageDraw
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR
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

def build_top3_video(
    deals: list,
    meme_name: str = None,
    output_filename: str = "top3_deals.mp4"
) -> str:
    """
    Top 3 Fırsat Derleme Videosu:
    - Üst Yarı (1080x960): Normal videolarımızdaki standart ajans şablonu (1 -> 2 -> 3 sırayla geçer).
    - Orta Bölüm: Glassmorphic 'GÜNÜN EN İYİ 3 İNDİRİMİNİ GÖREN BEN:' reaksiyon kancası.
    - Alt Yarı (1080x960): Kesintisiz tek viral meme videosu baştan sona oynar.
    - Alt Kenar: Süreyle senkronize neon ilerleme çubuğu (progress bar).
    - Ses: SFX veya karmaşa yok; meme'in kendi ikonik orijinal müziği/sesi doğal netlikte kullanılır.
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
    p = subprocess.run(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    raw_duration = float(m.group(3)) + int(m.group(2))*60 if m else 11.50
    rnd_trim = round(random.uniform(0.15, 0.40), 3)
    duration = max(6.0, round(raw_duration - rnd_trim, 3))
    has_audio = "Audio:" in p.stderr
    print(f"[Top3] ⏱️ Toplam Video Süresi: {duration:.2f}s (Anti-Hash Kırpma: -{rnd_trim}s, Orijinal Ses: {has_audio})")

    slide_dur = duration / 3.0
    d1 = round(slide_dur, 2)
    d2 = round(slide_dur, 2)
    d3 = round(duration - (d1 + d2), 2)

    # 3. Üst kartları üret (1. Fırsat, 2. Fırsat, 3. Fırsat) - Standart Şablon ile
    card_files = []
    for rank in [1, 2, 3]:
        deal = deals[rank - 1]
        card_out = os.path.join(TEMP_DIR, f"top3_single_card_{rank}.png")
        badge_title = f"#{rank} GÜNÜN BOMBASI" if rank == 1 else f"#{rank} GÜNÜN FIRSATI"
        raw_img = deal.get("image_path") or deal.get("local_img") or deal.get("image_url") or ""
        if raw_img and not raw_img.startswith("http") and not os.path.isabs(raw_img):
            cand_img = os.path.join(BASE_DIR, raw_img)
            if os.path.exists(cand_img):
                raw_img = cand_img
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
            output_path=card_out
        )
        card_files.append(card_out)

    # 4. Orta Bölüm Reaksiyon Bandı (Tekli videolarla birebir aynı stil)
    reaction_overlay_path = os.path.join(TEMP_DIR, "top3_reaction_overlay.png")
    create_reaction_hook_overlay("GÜNÜN EN İYİ 3 İNDİRİMİNİ GÖREN BEN:", output_path=reaction_overlay_path)

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # 5. Dynamic Progress Bar (Neon İlerleme Çubuğu)
    progress_bar_filter = (
        f"color=c=0x0F172A@0.8:s=1080x14:d={duration:.2f}[pbg];"
        f"color=c=0xFF5722:s=1080x14:d={duration:.2f}[pfill];"
        f"[stacked][pbg]overlay=0:1906[with_pbg];"
        f"[with_pbg][pfill]overlay=x='-1080+1080*(t/{duration:.2f})':y=1906[v]"
    )

    # 6. FFmpeg Montajı (1. Saniyede Punch-in Zoom + Anti-Hash Özgünlük Kalkanı):
    rnd_bright = round(random.uniform(-0.012, 0.012), 4)
    rnd_sat = round(random.uniform(0.985, 1.025), 4)
    rnd_contrast = round(random.uniform(0.99, 1.015), 4)
    scale_bottom = (
        f"scale=w='1080*(1+0.05*max(0,1-t))':h='960*(1+0.05*max(0,1-t))':eval=frame,"
        f"crop=1080:960,"
        f"eq=brightness={rnd_bright}:saturation={rnd_sat}:contrast={rnd_contrast}"
    )

    filter_complex = (
        f"[0:v]scale=1080:960[c1];"
        f"[1:v]scale=1080:960[c2];"
        f"[2:v]scale=1080:960[c3];"
        f"[c1][c2][c3]concat=n=3:v=1:a=0[top];"
        f"[3:v]{scale_bottom}[bottom_raw];"
        f"[bottom_raw][4:v]overlay=0:0[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"{progress_bar_filter}"
    )

    import datetime as _dt
    iso_now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(d1), "-i", card_files[0],
        "-loop", "1", "-t", str(d2), "-i", card_files[1],
        "-loop", "1", "-t", str(d3), "-i", card_files[2],
        "-i", bottom_meme_path,
        "-loop", "1", "-t", str(duration), "-i", reaction_overlay_path,
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

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Top3] 🎬 Video başarıyla üretildi (Redmi Note 11 Pro Metadata): {output_path}")
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
