import os
import sys
sys.path.append('.')
from split_composer import create_product_banner
from story_composer import create_story_card

deal = {
    'title': 'Dell 24" 200Hz 1ms IPS Gaming Monitör',
    'old_price': '5.999 TL',
    'new_price': '4.449 TL',
    'discount_pct': '-26%',
    'discount_val': 26,
    'store_name': 'Amazon TR',
    'store_url': 'https://www.amazon.com.tr/dp/B0FHHVD75B?tag=flasfirsat04-21',
    'seller_badge': 'AMAZON TR RESMİ SATICI',
    'image_path': 'assets/products/dell_200hz_gaming_monitor.jpg',
    'installment': 'Peşin Fiyatına 3 Taksit x 1.483 TL',
    'killer_hook': '⚡ 4.449 TL\'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ! ⚡',
    'feature_pill': '4.449 TL\'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ!',
    'has_verified_old_price': True,
    'is_lowest_30d': True,
    'market_badge': 'SON 30 GÜNÜN EN DÜŞÜĞÜ'
}

banner_out = 'temp/ornek_yeni_urun_banner.png'
story_out = 'temp/ornek_yeni_urun_story.jpg'

create_product_banner(
    product_image_path=deal['image_path'],
    title=deal['title'],
    old_price=deal['old_price'],
    new_price=deal['new_price'],
    discount_pct=deal['discount_pct'],
    badge_text='DEV İNDİRİM',
    store_name=deal['store_name'],
    installment=deal['installment'],
    feature_text=deal['feature_pill'],
    is_lowest_30d=True,
    has_verified_old_price=True,
    seller_badge_text=deal['seller_badge'],
    output_path=banner_out
)

create_story_card(deal, output_path=story_out)
print('ALL_DONE_SUCCESSFULLY')
