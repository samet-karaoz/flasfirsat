import os
import sys
import subprocess
import random
import re
from PIL import Image, ImageDraw
from config import BASE_DIR, TEMP_DIR, OUTPUT_DIR
from split_composer import (
    get_font, wrap_text, MEMES_DIR, AUDIO_DIR,
    AVAILABLE_MEMES, AVAILABLE_AUDIOS
)

def create_top3_card(
    rank: int,
    product_image_path: str,
    title: str,
    old_price: str,
    new_price: str,
    discount_pct: str,
    output_path: str
) -> str:
    """
    Top 3 formatına özel, 1080x960 ebatlarında sıralama rozetli (1., 2., 3.) afiş üretir.
    """
    W, H = 1080, 960
    img = Image.new("RGB", (W, H), (244, 246, 250))
    draw = ImageDraw.Draw(img)

    f_badge = get_font("segoeuib", 28)
    f_title = get_font("segoeuib", 38)
    f_old_price = get_font("segoeuib", 40)
    f_new_price = get_font("segoeuib", 66)
    f_pct = get_font("segoeuib", 28)

    # Sıralama teması
    if rank == 1:
        rank_text = "🥇 #1 GÜNÜN BOMBASI"
        badge_fill = (220, 38, 38) # Kırmızı
    elif rank == 2:
        rank_text = "🥈 #2 GÜNÜN FIRSATI"
        badge_fill = (234, 88, 12) # Turuncu
    else:
        rank_text = "🥉 #3 GÜNÜN FIRSATI"
        badge_fill = (13, 148, 136) # Teal / Zümrüt

    # Sol Üst Sıralama Rozeti
    rw = draw.textlength(rank_text, font=f_badge)
    draw.rounded_rectangle((40, 24, 40 + rw + 40, 76), radius=14, fill=badge_fill)
    draw.text((60, 35), rank_text, font=f_badge, fill=(255, 255, 255))

    # Sağ Üst İndirim Rozeti
    clean_pct = discount_pct.strip()
    if clean_pct and not clean_pct.endswith("İNDİRİM"):
        clean_pct = f"{clean_pct} İNDİRİM"
    pw = draw.textlength(clean_pct, font=f_pct)
    draw.rounded_rectangle((W - 40 - pw - 40, 24, W - 40, 76), radius=14, fill=(225, 29, 72))
    draw.text((W - 40 - pw - 20, 35), clean_pct, font=f_pct, fill=(255, 255, 255))

    # Ürün Başlığı (2 satır)
    title_lines = wrap_text(title, max_chars_per_line=36)
    ty = 94
    for line in title_lines:
        draw.text((40, ty), line, font=f_title, fill=(15, 23, 42))
        ty += 46

    # Ürün Fotoğrafı
    card_top = max(156, ty + 10)
    card_bottom = 746
    card_box = (40, card_top, W - 40, card_bottom)
    draw.rounded_rectangle(card_box, radius=24, fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    if product_image_path and os.path.exists(product_image_path):
        try:
            p_img = Image.open(product_image_path).convert("RGBA")
            max_w = card_box[2] - card_box[0] - 60
            max_h = card_box[3] - card_box[1] - 50
            p_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            px = card_box[0] + (card_box[2] - card_box[0] - p_img.width) // 2
            py = card_box[1] + (card_box[3] - card_box[1] - p_img.height) // 2
            img.paste(p_img, (px, py), p_img)
        except Exception as e:
            print(f"[Top3 Card] Görsel hatası: {e}")

    # Alt Fiyat Kutuları
    old_box = (40, 764, 400, 874)
    draw.rounded_rectangle(old_box, radius=18, fill=(241, 245, 249))
    draw.text((56, 774), "ESKİ FİYAT", font=get_font("segoeuib", 20), fill=(148, 163, 184))
    draw.text((56, 804), str(old_price), font=f_old_price, fill=(148, 163, 184))
    
    # Çizgi çek
    line_y = 828
    ow = draw.textlength(str(old_price), font=f_old_price)
    draw.line((54, line_y, 56 + ow + 4, line_y), fill=(239, 68, 68), width=4)

    new_box = (420, 764, W - 40, 874)
    draw.rounded_rectangle(new_box, radius=18, fill=(236, 253, 245), outline=(167, 243, 208), width=2)
    draw.text((440, 774), "YENİ İNDİRİMLİ FİYAT", font=get_font("segoeuib", 22), fill=(5, 150, 105))
    draw.text((440, 800), str(new_price), font=f_new_price, fill=(4, 120, 87))

    # CTA Alt Şerit
    cta_font = get_font("segoeuib", 23)
    cta_text = "👉 Yoruma 'LİNK' yaz, 3 fırsatın da linkini anında yollayalım! 📩"
    cw = draw.textlength(cta_text, font=cta_font)
    draw.text(((W - cw) // 2, 902), cta_text, font=cta_font, fill=(100, 116, 139))

    img.save(output_path, "PNG")
    return output_path

def build_top3_video(
    deals: list,
    output_filename: str = "top3_deals.mp4"
) -> str:
    """
    3 üründen oluşan, 15 saniyelik (3. fırsat -> 2. fırsat -> 1. fırsat)
    arka plan phonk müziği ve ses efektli viral video üretir.
    """
    if len(deals) < 3:
        raise ValueError("Top 3 videosu için en az 3 fırsat gereklidir!")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Sıralamayı ayarla: 3 -> 2 -> 1 (Merak ve retention'ı tavan yaptırmak için)
    # deals listesinin ilk 3 elemanı: deals[0]=#1, deals[1]=#2, deals[2]=#3
    sequence = [
        (3, deals[2]),
        (2, deals[1]),
        (1, deals[0])
    ]

    # Her segment için meme seç
    meme_pool = [
        "cat_vibing.mp4",
        "bicerdover_ciftetelli.mp4",
        "limon_davulcu.mp4",
        "knight_cat.mp4",
        "angaraya_mi_geldin.mp4"
    ]
    random.shuffle(meme_pool)

    segment_files = []
    for idx, (rank, deal) in enumerate(sequence):
        seg_card = os.path.join(TEMP_DIR, f"top3_card_{rank}.png")
        create_top3_card(
            rank=rank,
            product_image_path=deal.get("image_path") or deal.get("local_img"),
            title=deal.get("title", f"Fırsat Ürünü #{rank}"),
            old_price=deal.get("old_price", "0 TL"),
            new_price=deal.get("new_price", "0 TL"),
            discount_pct=deal.get("discount_pct", "-30%"),
            output_path=seg_card
        )

        meme_name = meme_pool[idx % len(meme_pool)]
        meme_path = os.path.join(MEMES_DIR, meme_name)
        if not os.path.exists(meme_path):
            meme_path = os.path.join(MEMES_DIR, "knight_cat.mp4")

        seg_output = os.path.join(TEMP_DIR, f"seg_{rank}.mp4")
        
        # 5 saniyelik dikey montaj (Üst meme, Alt kart)
        filter_str = (
            f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
            f"[1:v]scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(1080-iw)/2:(960-ih)/2:color=0xF4F6FA[bottom];"
            f"[top][bottom]vstack=inputs=2[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", meme_path,
            "-loop", "1", "-i", seg_card,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-t", "5.0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            seg_output
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        segment_files.append(seg_output)

    # 3 segmenti birleştir
    concat_list_file = os.path.join(TEMP_DIR, "top3_concat.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for sf in segment_files:
            # ffmpeg concat dosya yolları
            escaped_path = sf.replace("\\", "/")
            f.write(f"file '{escaped_path}'\n")

    merged_video_temp = os.path.join(TEMP_DIR, "top3_video_no_audio.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_file,
        "-c", "copy",
        merged_video_temp
    ]
    subprocess.run(cmd_concat, check=True, capture_output=True)

    # Ses miksajı: 15s Phonk + 5. ve 10. saniyelerde Whoosh geçiş sesi
    bg_music = os.path.join(AUDIO_DIR, "brazilian_phonk.m4a")
    if not os.path.exists(bg_music):
        bg_music = os.path.join(AUDIO_DIR, "phonk_meme.m4a")

    whoosh_sfx = os.path.join(AUDIO_DIR, "whoosh.wav")
    final_output = os.path.join(OUTPUT_DIR, output_filename)

    if os.path.exists(whoosh_sfx):
        # Müziğe geçiş efektlerini ekle
        audio_filter = (
            f"[1:a]volume=0.9[music];"
            f"[2:a]adelay=4900|4900,volume=0.8[w1];"
            f"[3:a]adelay=9900|9900,volume=0.8[w2];"
            f"[music][w1][w2]amix=inputs=3:duration=first:dropout_transition=2[a]"
        )
        cmd_final = [
            "ffmpeg", "-y",
            "-i", merged_video_temp,
            "-stream_loop", "-1", "-i", bg_music,
            "-i", whoosh_sfx,
            "-i", whoosh_sfx,
            "-filter_complex", audio_filter,
            "-map", "0:v", "-map", "[a]",
            "-t", "15.0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            final_output
        ]
    else:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", merged_video_temp,
            "-stream_loop", "-1", "-i", bg_music,
            "-map", "0:v", "-map", "1:a",
            "-t", "15.0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            final_output
        ]

    subprocess.run(cmd_final, check=True, capture_output=True)
    print(f"[Top3] 🎬 Video başarıyla üretildi: {final_output}")
    return final_output

def generate_top3_caption(deals: list) -> str:
    """Top 3 videosu için DM teşvikli viral açıklama metni üretir."""
    d1 = deals[0]
    d2 = deals[1]
    d3 = deals[2]

    caption = (
        f"🔥 GÜNÜN EN İYİ 3 İNDİRİMİ RESMEN ÇÖKTÜ!\n\n"
        f"🥉 #3: {d3.get('title')[:35]}...\n"
        f"   💸 {d3.get('old_price')} ➔ {d3.get('new_price')} ({d3.get('discount_pct')})\n\n"
        f"🥈 #2: {d2.get('title')[:35]}...\n"
        f"   💸 {d2.get('old_price')} ➔ {d2.get('new_price')} ({d2.get('discount_pct')})\n\n"
        f"🥇 #1: {d1.get('title')[:35]}...\n"
        f"   💸 {d1.get('old_price')} ➔ {d1.get('new_price')} ({d1.get('discount_pct')})\n\n"
        f"👉 Yoruma 'LİNK' yaz, 3 fırsatın da linkini anında DM kutuna yollayalım! 📩\n"
        f"🔗 Tüm linkler profilimizdeki sitede ve Telegram kanalımızda!\n\n"
        f"#indirim #fırsat #teknoloji #kampanya #keşfet"
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
