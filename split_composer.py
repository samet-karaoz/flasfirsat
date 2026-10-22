"""
split_composer.py - Legacy Archive Proxy
Bu dosya Option A (Resmi Marka Reklamı) gereğince legacy_archive klasörüne taşınmıştır.
Geriye dönük uyumluluk için yönlendirici proxy olarak çalışır.
"""
import sys
import os

archive_path = os.path.join(os.path.dirname(__file__), "legacy_archive")
if archive_path not in sys.path:
    sys.path.insert(0, archive_path)

try:
    from legacy_archive.split_composer import *
except ImportError:
    pass
