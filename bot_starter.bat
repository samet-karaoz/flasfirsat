@echo off
chcp 65001 >nul
cd /d "C:\Users\Samet\Desktop\Otomasyon"
title Fla$ Firsat Telegram Bot Servisi

echo ========================================================
echo   ⚡ FLA$ FIRSAT TELEGRAM BOT & OTOPILOT SERVISI
echo ========================================================
echo.
echo Bot baslatiliyor...
echo Antigravity kapali olsa bile bu pencere acik kaldigi surece
echo veya arka planda calistigi surece bot aktif kalacaktir.
echo.
echo Durdurmak icin pencereyi kapatabilir veya Ctrl+C yapabilirsiniz.
echo ========================================================
echo.

"C:\Users\Samet\AppData\Local\Programs\Python\Python314\python.exe" -u telegram_bot_service.py
pause
