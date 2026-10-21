import os
import sys
import subprocess
from motion_composer import build_motion_deal_video
from video_content_validator import validate_rendered_video

OUTPUT_DIR = r"C:\Users\Samet\Desktop\Otomasyon\output"
ARTIFACT_DIR = r"C:\Users\Samet\.gemini\antigravity\brain\ce08c93e-02bf-4712-9558-caff694cab2c"

deal = {
    "title": "Aula F75 RGB Kablosuz Mekanik Klavye",
    "old_price": "3.499 TL",
    "new_price": "2.799 TL",
    "discount_pct": "%20",
    "store_name": "Amazon TR",
    "badge": "SON 30 GÜNÜN EN DÜŞÜK FİYATI",
    "installment": "3 x 933 TL Taksit",
    "coupon_info": "Kupon İndirimi",
    "deal_code": "#134",
    "killer_hook": "Tri-Mode Kablosuz & Hot-Swap",
    "is_lowest_30d": True,
    "market_badge": "Piyasa: 3.499 TL",
    "seller_badge": "Amazon TR Resmi Satıcı",
    "image_path": r"C:\Users\Samet\Desktop\Otomasyon\temp\prod_aula_f75_rgb_kablosuz_mekanik_.jpg",
    "has_verified_old_price": True,
}

print("=== 1. FORMAT A: MEME VİDEOSU OLUŞTURULUYOR ===")
video_a_path = build_motion_deal_video(
    deal=deal,
    meme_name="knight_cat.mp4",
    reaction_text="FİYATI GÖRENLER ŞOKTA! 🙀🔥",
    output_filename="sample_format_a_meme.mp4",
    cta_type="instagram",
    duration=6.8
)
print("Video A hazır:", video_a_path)

print("\n=== 2. FORMAT B: KUTU AÇILIŞ / ASMR VİDEOSU OLUŞTURULUYOR ===")
video_b_path = build_motion_deal_video(
    deal=deal,
    meme_name="unboxing_aula_f75.mp4",
    reaction_text="SESİ VE KALİTESİ ŞAKA MI? ⌨️🔥",
    output_filename="sample_format_b_unboxing.mp4",
    cta_type="instagram",
    duration=6.8
)
print("Video B hazır:", video_b_path)

print("\n=== 3. VİDEOLAR DOĞRULANIYOR ===")
res_a = validate_rendered_video(video_a_path, deal=deal)
print(f"Format A Doğrulama: Geçti={res_a['passed']}, Süre={res_a['duration']}s, Hatalar={res_a['issues']}")

res_b = validate_rendered_video(video_b_path, deal=deal)
print(f"Format B Doğrulama: Geçti={res_b['passed']}, Süre={res_b['duration']}s, Hatalar={res_b['issues']}")

print("\n=== 4. KARŞILAŞTIRMA KARELERİ ALINIYOR ===")
# Kare 1: 1.5s (Gizemli Fiyat / Mystery Countdown Fazı)
# Kare 2: 3.8s (Açılmış İndirimli Fiyat Fazı)
pairs = [
    (video_a_path, "sample_a_meme_mystery.png", "00:00:01.50"),
    (video_a_path, "sample_a_meme_revealed.png", "00:00:03.80"),
    (video_b_path, "sample_b_unboxing_mystery.png", "00:00:01.50"),
    (video_b_path, "sample_b_unboxing_revealed.png", "00:00:03.80"),
]

for vid, out_name, ts in pairs:
    out_path = os.path.join(ARTIFACT_DIR, out_name)
    cmd = ["ffmpeg", "-ss", ts, "-i", vid, "-vframes", "1", "-q:v", "2", out_path, "-y"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Kare kaydedildi: {out_name} (Zaman: {ts})")

print("\nTüm işlem başarıyla tamamlandı!")
