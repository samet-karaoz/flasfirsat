import os
import sys

from unboxing_manager import get_deal_unboxing_video
from motion_composer import build_motion_deal_video
from video_content_validator import validate_rendered_video

deal_tech = {
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

deal_grocery = {
    "title": "Omo Active Sıvı Çamaşır Deterjanı 1950 ml",
    "old_price": "289 TL",
    "new_price": "169 TL",
    "discount_pct": "%41",
    "store_name": "Amazon TR",
    "badge": "DEV İNDİRİM",
    "deal_code": "#135",
    "image_path": r"C:\Users\Samet\Desktop\Otomasyon\temp\prod_aula_f75_rgb_kablosuz_mekanik_.jpg",
    "has_verified_old_price": True,
}

print("=== TEST 1: TEKNOLOJİ ÜRÜNÜ (AULA F75) ===")
res_tech = get_deal_unboxing_video(deal_tech)
assert res_tech is not None, "Teknoloji ürünü için unboxing bulunmalıydı!"
video_file, hook = res_tech
print(f"Format B Başarılı -> Kutu Açılış: {video_file} | Kanca: {hook}")

print("\n=== TEST 2: GIDA / DETERJAN ÜRÜNÜ (OMO ACTIVE) ===")
res_grocery = get_deal_unboxing_video(deal_grocery)
assert res_grocery is None, "Deterjan ürünü None dönmeli ve Meme'e fallback yapmalıydı!"
print("Format A (Meme Fallback) Başarılı -> res_grocery is None (Doğrudan Meme'e yönlendirildi)")

print("\n=== TÜM TESTLER BAŞARIYLA GEÇTİ! HİBRİT MOTOR AKTİF! ===")
