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

    # Sıralama teması (Hatasız ve net tipografi)
    if rank == 1:
        rank_text = "1. GÜNÜN BOMBASI"
        badge_fill = (220, 38, 38) # Kırmızı
    elif rank == 2:
        rank_text = "2. GÜNÜN FIRSATI"
        badge_fill = (234, 88, 12) # Turuncu
    else:
        rank_text = "3. GÜNÜN FIRSATI"
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
    cta_text = "Yoruma 'LİNK' yaz, 3 fırsatın da linkini anında yollayalım!"
    cw = draw.textlength(cta_text, font=cta_font)
    draw.text(((W - cw) // 2, 902), cta_text, font=cta_font, fill=(100, 116, 139))


    img.save(output_path, "PNG")
    return output_path

def build_top3_video(
    deals: list,
    meme_name: str = None,
    output_filename: str = "top3_deals.mp4"
) -> str:
    """
    Kullanıcı İsteklerine Özel Tasarım:
    - Üst Yarı (1080x960): 3 fırsatın görselleri ve indirim kartları sırayla geçer (1 -> 2 -> 3).
    - Alt Yarı (1080x960): TEK BİR viral meme videosu baştan sona kesintisiz oynar.
    - Ses: Phonk müzik yerine meme'in kendi ikonik orijinal müziği/sesi kullanılır.
    - Kedi videoları kesinlikle hariç tutulmuştur (Limon Davulcu, Çiftetelli, CJ vb. kullanılır).
    """
    if len(deals) < 3:
        raise ValueError("Top 3 videosu için en az 3 fırsat gereklidir!")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1. Kedi olmayan, orijinal müzikli Türk viral meme havuzu
    valid_memes = [
        "limon_davulcu.mp4",
        "bicerdover_ciftetelli.mp4",
        "degirmenci_dayi_cj.mp4",
        "angaraya_mi_geldin.mp4",
        "limon_halay.mp4"
    ]
    # Kütüphanedeki mevcut olanları filtrele
    existing_memes = [m for m in valid_memes if os.path.exists(os.path.join(MEMES_DIR, m))]
    if not existing_memes:
        # Fallback: Kedi olmayan herhangi bir mp4
        existing_memes = [f for f in os.listdir(MEMES_DIR) if f.endswith(".mp4") and "cat" not in f.lower()]

    if meme_name and os.path.exists(os.path.join(MEMES_DIR, meme_name)):
        chosen_meme = meme_name
    elif existing_memes:
        chosen_meme = random.choice(existing_memes)
    else:
        chosen_meme = "limon_davulcu.mp4"

    bottom_meme_path = os.path.join(MEMES_DIR, chosen_meme)
    print(f"[Top3] 🎬 Seçilen Tek Kesintisiz Meme: {chosen_meme}")

    # 2. Meme süresini ve ses durumunu al
    p = subprocess.run(["ffmpeg", "-i", bottom_meme_path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    duration = float(m.group(3)) + int(m.group(2))*60 if m else 11.50
    has_audio = "Audio:" in p.stderr
    print(f"[Top3] ⏱️ Toplam Video Süresi: {duration:.2f}s (Orijinal Ses: {has_audio})")

    slide_dur = duration / 3.0
    d1 = round(slide_dur, 2)
    d2 = round(slide_dur, 2)
    d3 = round(duration - (d1 + d2), 2)

    # 3. Üst kartları üret (1. Fırsat, 2. Fırsat, 3. Fırsat)
    card_files = []
    for rank in [1, 2, 3]:
        deal = deals[rank - 1]
        card_out = os.path.join(TEMP_DIR, f"top3_single_card_{rank}.png")
        create_top3_card(
            rank=rank,
            product_image_path=deal.get("image_path") or deal.get("local_img") or deal.get("image_url"),
            title=deal.get("title", f"Fırsat Ürünü #{rank}"),
            old_price=deal.get("old_price", "0 TL"),
            new_price=deal.get("new_price", "0 TL"),
            discount_pct=deal.get("discount_pct", "-30%"),
            output_path=card_out
        )
        card_files.append(card_out)

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # 4. FFmpeg Montajı:
    # [0:v], [1:v], [2:v] -> 3 slayt üstte sırayla (1080x960)
    # [3:v] -> Tek meme altta (1080x960)
    # Ses -> [3:a] meme'in kendi orijinal sesi
    filter_complex = (
        f"[0:v]scale=1080:960[c1];"
        f"[1:v]scale=1080:960[c2];"
        f"[2:v]scale=1080:960[c3];"
        f"[c1][c2][c3]concat=n=3:v=1:a=0[top];"
        f"[3:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(d1), "-i", card_files[0],
        "-loop", "1", "-t", str(d2), "-i", card_files[1],
        "-loop", "1", "-t", str(d3), "-i", card_files[2],
        "-i", bottom_meme_path,
        "-filter_complex", filter_complex,
        "-map", "[v]"
    ]

    if has_audio:
        cmd += ["-map", "3:a", "-c:a", "aac", "-b:a", "192k"]
    else:
        # Eğer meme'de ses yoksa alternatif Türk müziği
        pass

    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        output_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        print(f"[Top3] 🎬 Video başarıyla üretildi: {output_path}")
        return output_path
    else:
        print("[Top3] FFmpeg hatası:", res.stderr)
        raise RuntimeError(f"Video derlenemedi: {res.stderr}")


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
