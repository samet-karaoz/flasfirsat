Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Samet\Desktop\Otomasyon"
WshShell.Run """C:\Users\Samet\AppData\Local\Programs\Python\Python314\pythonw.exe"" -u telegram_bot_service.py", 0, False
Set WshShell = Nothing
