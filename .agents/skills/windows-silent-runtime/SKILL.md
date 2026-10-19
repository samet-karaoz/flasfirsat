---
name: windows-silent-runtime
description: "Windows üzerinde çalışırken açılıp kapanan siyah CMD, curl.exe veya ffmpeg.exe pencerelerini %100 engelleyen sessiz çalışma zamanı (CREATE_NO_WINDOW) ve ağ indirme kuralları."
---

# Windows Silent Runtime (Sessiz Arka Plan Çalışma Standardı)

Kullanıcının masaüstünde oyun oynarken veya çalışırken ekranda anlık açılıp kapanan siyah konsol pencerelerini (`cmd.exe`, `curl.exe`, `ffmpeg.exe`, `git.exe`) tamamen engellemek bu projenin temel sistem kuralıdır.

---

## 1. Alt Süreç (Subprocess) Kuralı

- Projede **asla** doğrudan `subprocess.run()`, `subprocess.Popen()` veya `os.system()` çağrılmaz.
- Tüm harici komutlar (`ffmpeg`, `ffprobe`, `git`, `yt-dlp`) yalnızca `config.py` içindeki **`safe_run_subprocess(cmd, ...)`** üzerinden çalıştırılmalıdır:
  ```python
  from config import safe_run_subprocess
  res = safe_run_subprocess(["ffmpeg", "-y", "-i", input_path, output_path], capture_output=True, text=True)
  ```
- `safe_run_subprocess` Windows üzerinde otomatik olarak:
  - `creationflags = subprocess.CREATE_NO_WINDOW` (`0x08000000`)
  - `startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW` (`SW_HIDE = 0`)
  parametrelerini enjekte ederek konsol penceresi oluşmasını işletim sistemi seviyesinde engeller.

---

## 2. Dosya ve Ağ İndirme Kuralı (`curl.exe` Yasağı)

- Görsel veya web sayfası indirmek için **asla** `curl.exe` veya harici CLI indirme araçları çağrılmaz.
- Tüm dosya indirmeleri `config.py` içindeki **`download_file(url, dest_path)`** veya **`safe_http_get(url)`** fonksiyonlarıyla saf Python içinde yapılır.
- Python 3.14 ortamında oluşabilecek `PermissionError` / SSL sertifika deposu hatalarına karşı `download_file` otomatik olarak `ssl._create_unverified_context()` yedek yolunu (fallback) kullanır.
