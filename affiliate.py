"""
Affiliate URL Dönüştürücü ve Yönetici Köprüsü.
Detaylı ve çoklu mağaza altyapısı affiliate_manager.py üzerinden sağlanır.
"""
from affiliate_manager import (
    get_affiliate_url,
    detect_store,
    is_affiliate_active,
    get_affiliate_status,
    clean_tracking_params,
    resolve_redirect_url
)

__all__ = [
    "get_affiliate_url",
    "detect_store",
    "is_affiliate_active",
    "get_affiliate_status",
    "clean_tracking_params",
    "resolve_redirect_url"
]
