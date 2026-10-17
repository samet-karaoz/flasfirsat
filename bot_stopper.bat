@echo off
chcp 65001 >nul
echo 🛑 Fla$ Firsat Telegram Bot Servisi durduruluyor...

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot_service.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Durdurulan Process ID:' $_.ProcessId }"

echo.
echo ✅ Bot servisi basariyla durduruldu.
timeout /t 3 >nul
