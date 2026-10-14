# YouTube Shorts Otomasyonu Kurulum Rehberi

YouTube Data API v3 ile videoları kanalınıza otomatik olarak **YouTube Shorts** formatında yükleyebilirsiniz.

---

## 1. Google Cloud Console'da Proje Açın

1. [Google Cloud Console](https://console.cloud.google.com/)'a gidin.
2. Yeni bir proje oluşturun (örneğin: `Firsat-Avcisi`).
3. Sol menüden **APIs & Services (API'ler ve Hizmetler) > Library (Kitaplık)** bölümüne girin.
4. **"YouTube Data API v3"** arayın ve **Enable (Etkinleştir)** butonuna basın.

---

## 2. OAuth İstemci Kimliği Oluşturun

1. **APIs & Services > Credentials (Kimlik Bilgileri)** sekmesine gidin.
2. **Create Credentials (Kimlik Bilgisi Oluştur) > OAuth client ID (OAuth istemci kimliği)** seçeneğine tıklayın.
3. Uygulama türü olarak: **Desktop App (Masaüstü Uygulaması)** seçin.
4. İsim verin (örnek: `Shorts-Bot`) ve **Create (Oluştur)** deyin.
5. Açılan pencerede **Download JSON (JSON İndir)** butonuna tıklayın.

---

## 3. Dosyayı Projeye Ekleyin

1. İndirdiğiniz `.json` dosyasının adını **`client_secrets.json`** olarak değiştirin.
2. Bu dosyayı doğrudan projenin ana klasörüne (`c:\Users\Samet\Desktop\Otomasyon\client_secrets.json`) yapıştırın.

---

## 4. İlk Bağlantı ve Test

Terminalde şu komutu çalıştırın:
```bash
python youtube_publisher.py
```
- Tarayıcınızda bir defaya mahsus Google ile oturum açma sayfası açılacaktır.
- YouTube kanalınızın bağlı olduğu hesabı seçip izin verin.
- Giriş başarılı olduğunda sistem `data/youtube_token.json` dosyasını oluşturur ve bir daha oturum açmanız gerekmez.

---

## Ayarlar (.env)

İsteğe bağlı olarak `.env` dosyanıza şu parametreyi ekleyebilirsiniz:
```env
# public (herkese açık) veya unlisted (liste dışı test için)
YOUTUBE_PRIVACY_STATUS=public
```
