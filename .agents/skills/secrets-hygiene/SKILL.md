---
name: secrets-hygiene
description: "API anahtarları, bot şifreleri, OAuth istemci kimlikleri, oturum token'ları ve çalışma zamanı verilerinin asla kod içine yazılmamasını ve Git/GitHub'a sızmamasını sağlayan güvenlik rehberi."
---

# Secrets Hygiene (Gizli Bilgi ve Anahtar Güvenliği Protokolü)

Bu skill, projede kullanılan tüm hassas kimlik bilgilerinin (Telegram Bot Token, Instagram Graph API Token, Gemini API Key, YouTube OAuth Secrets vb.) mutlak güvenliğini sağlar.

---

## 1. Temel Prensipler

### A. Kod İçine Asla Gizli Bilgi Yazılamaz
- Tüm token ve anahtarlar **yalnızca `.env` dosyasından** `os.getenv("KEY")` ile okunmalıdır.
- Kod dosyalarına, test komutlarına veya yorum satırlarına gerçek API token'ları yazılamaz.

### B. Çalışma Zamanı Veritabanları ve Dosyalar
- `data/` klasöründeki hiçbir JSON dosyası (`pending_deals.json`, `user_alarms.json` vb.) **Git'e commit edilemez**.
- Bu dosyalar kullanıcılara, siparişlere veya oturumlara özel veri içerebilir.
- Token içeren hiçbir web linki (örneğin Telegram `https://api.telegram.org/file/bot<TOKEN>/...`) diske JSON formatında yazılmamalıdır; sadece bellekte (RAM) dinamik üretilmelidir.

### C. OAuth ve Kimlik Dosyaları
- `client_secrets.json`, `*.pickle`, `youtube_token.json`, `credentials.json` dosyaları `.gitignore` içinde yer almalıdır ve asla depoya eklenemez.

---

## 2. Commit Öncesi Güvenlik Kontrol Listesi

Git üzerinde `git add .` veya `git commit` yapmadan önce zorunlu kontrol:
1. [ ] `git status -s` çalıştırıldığında `data/`, `.env`, `client_secrets.json` veya log dosyaları var mı?
2. [ ] Yapılan kod değişikliklerinde sert kodlanmış (hardcoded) token, key veya şifre var mı?
3. [ ] `.gitignore` dosyası güncel ve eksiksiz mi?

---

## 3. Olası Sızıntı Durumunda Acil Eylem Planı
Eğer bir token yanlışlıkla depoya yüklenirse:
1. **İptal Et (Revoke):** İlgili platformdan (Telegram BotFather, Meta Developer, Google Cloud) sızan anahtar anında iptal edilir ve yenisi üretilir.
2. **Geçmişi Temizle:** Dosya `git rm --cached <dosya>` ile indeksten çıkarılır, `.gitignore` güncellenir ve yeni commit ile depoya gönderilir.
3. **.env Güncelle:** Yeni anahtar yalnızca yerel `.env` dosyasına yazılır.
