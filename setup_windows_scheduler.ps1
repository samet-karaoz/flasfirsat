$pythonPath = "C:\Users\Samet\AppData\Local\Programs\Python\Python314\python.exe"
$scriptPath = "C:\Users\Samet\Desktop\Otomasyon\autopilot_engine.py"
$workingDir = "C:\Users\Samet\Desktop\Otomasyon"

$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 1. Görev: 12:30 Öğle Molası
$action1230 = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --now --slot `"Öğle Molası (12:30)`"" -WorkingDirectory $workingDir
$trigger1230 = New-ScheduledTaskTrigger -Daily -At "12:30PM"
Register-ScheduledTask -TaskName "FlasFirsat_Ogle_1230" -Action $action1230 -Trigger $trigger1230 -Settings $settings -Force

# 2. Görev: 20:00 Akşam Prime Time
$action2000 = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --now --slot `"Akşam Prime Time (20:00)`"" -WorkingDirectory $workingDir
$trigger2000 = New-ScheduledTaskTrigger -Daily -At "8:00PM"
Register-ScheduledTask -TaskName "FlasFirsat_Aksam_2000" -Action $action2000 -Trigger $trigger2000 -Settings $settings -Force

Write-Host "✅ Windows Görev Zamanlayıcısı başarıyla ayarlandı!"
Write-Host "• 12:30 ve 20:00 için görevler eklendi."
Write-Host "• 'Bilgisayarı Uyandır' (WakeToRun) özelliği aktif edildi."
