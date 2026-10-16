import sys
sys.path.append('.')
from split_composer import create_product_banner

create_product_banner(
    product_image_path='assets/products/dell_200hz_gaming_monitor.jpg',
    title='Dell 24" 200Hz 1ms IPS Gaming Monitör',
    old_price='5.999 TL',
    new_price='4.449 TL',
    discount_pct='-26%',
    badge_text='DEV İNDİRİM',
    store_name='Amazon TR',
    installment='Peşin Fiyatına 3 Taksit x 1.483 TL',
    feature_text='4.449 TL\'YE 200Hz 1ms IPS OYUNCU MONİTÖRÜ!',
    is_lowest_30d=True,
    has_verified_old_price=True,
    seller_badge_text='AMAZON TR RESMİ SATICI',
    output_path='temp/ornek_yeni_urun_banner_duzeltilmis.png'
)
print('BANNER_RENDERED')
