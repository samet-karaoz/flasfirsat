import os
import re
import sys
import time
import json
import random
import subprocess
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

from config import (
    BASE_DIR,
    DATA_DIR,
    TEMP_DIR,
    get_curl_cmd,
    safe_run_subprocess
)
TOKEN_PATH = os.path.join(DATA_DIR, "youtube_token.json")
CLIENT_SECRETS_PATH = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", os.path.join(BASE_DIR, "client_secrets.json"))
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip().lower()

def check_youtube_credentials() -> dict:
    """YouTube API kimlik ve yetkilendirme durumunu kontrol eder."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(CLIENT_SECRETS_PATH):
        token_ready_internally = False
        if os.path.exists(TOKEN_PATH):
            try:
                with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                    t_data = json.load(f)
                    if (t_data.get("refresh_token") or t_data.get("token")) and t_data.get("client_id") and t_data.get("client_secret"):
                        token_ready_internally = True
            except Exception:
                pass
        if not token_ready_internally:
            return {
                "configured": False,
                "token_ready": False,
                "error": "client_secrets.json bulunamadı. Lütfen Google Cloud'dan indirip proje klasörüne koyun."
            }

    if not os.path.exists(TOKEN_PATH):
        return {
            "configured": True,
            "token_ready": False,
            "message": "client_secrets.json mevcut ancak oturum açma (youtube_auth.py) bekleniyor."
        }

    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            if t_data.get("refresh_token") or t_data.get("token"):
                return {"configured": True, "token_ready": True, "message": "YouTube oturumu hazır."}
    except Exception:
        pass

    return {"configured": True, "token_ready": False, "message": "Token geçersiz, yeniden yetkilendirme gerekli."}

def get_valid_access_token() -> str:
    """Aktif access_token döner; süresi dolduysa curl ile yeniler."""
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError("data/youtube_token.json bulunamadı. Lütfen önce 'python youtube_auth.py' çalıştırın.")

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        t_data = json.load(f)

    refresh_token = t_data.get("refresh_token")
    client_id = t_data.get("client_id")
    client_secret = t_data.get("client_secret")

    # Access token'ı curl ile doğrudan yenile (OpenSSL bug'ına takılmaz)
    refresh_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    cmd = get_curl_cmd([
        "-s", "-X", "POST",
        "https://oauth2.googleapis.com/token",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-d", urllib.parse.urlencode(refresh_payload)
    ])
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        ref_json = json.loads(res.stdout)
        if "access_token" in ref_json:
            t_data["token"] = ref_json["access_token"]
            with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump(t_data, f, ensure_ascii=False, indent=2)
            return ref_json["access_token"]
        elif ref_json.get("error") == "invalid_grant":
            print("[YouTube Publisher] ⚠️ Refresh token süresi dolmuş veya iptal edilmiş!")
            try:
                from telegram_notifier import send_telegram_alert
                send_telegram_alert(
                    "⚠️ <b>YouTube Shorts Yetki Süresi Doldu!</b>\n\n"
                    "Google OAuth token'ının süresi dolmuş. Shorts yüklemelerinin devam etmesi için lütfen terminalde <code>python youtube_auth.py</code> çalıştırarak tek tıkla oturumu yenileyin."
                )
            except Exception:
                pass
    except Exception as e:
        print(f"[YouTube Publisher] Token yenileme uyarısı: {e}")

    # Mevcut token'ı döndür
    return t_data.get("token", "")

def sanitize_youtube_text(text: str) -> str:
    """YouTube Data API başlık ve açıklamalarda < ve > karakterlerini kabul etmez (HTML/XSS koruması)."""
    if not text:
        return ""
    t = text.replace("->", "➔").replace("<-", "⬅").replace("-->", "➔").replace("<--", "⬅")
    t = t.replace("<", "").replace(">", "")
    return t.strip()


def _extract_deal_code(deal_code: str = "", description: str = "") -> str:
    """Açıklama veya deal_code içinden yalın fırsat kodu numarasını (örn: '198') çıkarır."""
    raw = str(deal_code or "").strip()
    if raw:
        m = re.search(r"(\d+)", raw)
        if m:
            return m.group(1)
        return raw.lstrip("#").strip()
    if description:
        m = re.search(r"(?:F[ıi]rsat\s*Kodu|Kod)\s*[:#]?\s*#?(\d{2,5})", str(description), re.IGNORECASE)
        if m:
            return m.group(1)
        m2 = re.search(r"#(\d{3,5})\b", str(description))
        if m2:
            return m2.group(1)
    return ""


def _sanitize_youtube_comment(text: str) -> str:
    """Yorum metnini URL, gereksiz hashtag ve yasaklı karakterlerden temizleyerek doğal tutar."""
    if not text:
        return ""
    clean = str(text).strip().strip('"').strip("'").strip()
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"www\.\S+", "", clean)
    clean = re.sub(r"#[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+", "", clean)
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return sanitize_youtube_text(clean)


def generate_friendly_youtube_comment(
    title: str,
    new_price: str = "",
    discount_pct: str = "",
    deal_code: str = "",
    description: str = ""
) -> str:
    """
    Reklam botu gibi değil; izleyicilerle sohbet eden, cana yakın ve samimi
    bir indirim kanalı topluluğu tonunda otomatik ilk yorum metni üretir.
    """
    clean_title = sanitize_youtube_text(title or "bu ürün").replace("#Shorts", "").replace("#shorts", "").strip()
    code_num = _extract_deal_code(deal_code, description)

    if code_num:
        code_hint = f"(Soranlar olursa ürün kodu {code_num}, kanal profilimizdeki sitemizden arama kutusuna {code_num} yazarak direkt bakabilirsiniz.)"
    else:
        code_hint = "(Merak edip incelemek isteyenler kanal profilimizdeki sitemizden güncel haline ulaşabilir.)"

    # 1. Önce Gemini ile ürüne özel samimi bir ilk yorum üretmeyi dene
    try:
        from deal_hunter import call_gemini
        price_note = f" (Şu an {new_price})" if new_price else ""
        disc_note = f" | İndirim: {discount_pct}" if discount_pct else ""
        style_seed = random.choice([
            "Girişte samimi bir gözlemle başla (ör. 'Açık konuşayım...', 'Dürüst olalım...')",
            "Girişte sıcak bir topluluk selamıyla başla (ör. 'Selam millet...', 'Merhaba ekip...')",
            "Girişte bütçe/deneyim odağıyla başla (ör. 'Ekipçe listeleri tararken...', 'Bu ara benzer model bakanlar için...')",
            "Girişte kısa bir kullanıcı sorusu havasıyla başla (ör. 'Aramızda bunu deneyimleyen var mı...', 'Fiyat/performans açısından...')",
        ])
        prompt = f"""Sen @flasfirsat.tr YouTube kanalının samimi, esprili ve cana yakın indirim/teknoloji dostusun.
Görevin: Az önce paylaştığımız Shorts videosunun altına izleyicilerle sohbet başlatacak, ASLA soğuk bir reklam botu gibi durmayan çok sıcak bir İLK YORUM yazmak.

Ürün: {clean_title}{price_note}{disc_note}
Fırsat Kodu: {code_num if code_num else "Yok (profildeki siteye yönlendir)"}
Üslup Önerisi: {style_seed} (aynı kalıp girişi tekrar etme, doğal ol).

KESİN TON VE KURALLAR:
1. Sadece satış/reklam cümlesi kurma; sanki arkadaş grubuna "Bunu denk getirdim, kullanan var mı?" der gibi konuş.
2. "HEMEN ALIN", "KAÇIRMAYIN", "ŞOK FİYAT", "PATLAYIN" gibi bağırgan pazarlama klişelerini KESİNLİKLE KULLANMA.
3. İlk 1-2 cümlede ürüne dair samimi bir gözlem yap ve izleyicilere mutlaka doğal bir deneyim/fikir sorusu sor ("Aranızda bu seriyi kullanan var mı, memnun musunuz?", "Sizce bu fiyata değer mi?").
4. Son cümlede veya parantez içinde nazikçe yardımcı ol: Fırsat kodu varsa "{code_num}" kodunu profilimizdeki sitede arama kutusuna yazarak direkt Amazon sayfasına bakabileceklerini söyle (kod yoksa profilimizdeki linke yönlendir).
5. Tuhaf/mecazi kelimeler veya mevsime uymayan ifadeler kullanma; sade, akıcı ve doğal Türkçe kullan. Asla URL/link (http/www) ve asla #hashtag kullanma. Toplam 2-3 cümle, en fazla 1-2 sade emoji olsun.
Sadece yorum metnini yaz."""

        ai_cmt = call_gemini(prompt, json_mode=False)
        if isinstance(ai_cmt, str):
            ai_clean = _sanitize_youtube_comment(ai_cmt)
            bad_hype = any(b in ai_clean.lower() for b in ("hemen al", "kaçırma", "şok fiyat", "acele et"))
            if len(ai_clean) >= 35 and not bad_hype:
                if code_num and code_num not in ai_clean:
                    ai_clean = f"{ai_clean} {code_hint}"
                return ai_clean[:500]
    except Exception:
        pass

    # 2. Akıllı Kategoriye Göre Samimi Fallback Şablonları
    subtype = "general"
    try:
        from deal_hunter import get_product_subtype
        subtype = get_product_subtype(clean_title)
    except Exception:
        pass

    if subtype in ("mouse", "keyboard", "headset", "gamepad", "mousepad"):
        pool = [
            f"Selamlar dostlar! Setup dizenler veya ekipman yenilemek isteyenler için {clean_title} fiyat/performans açısından güzel denk geldi. Aranızda bu modeli aktif kullanan varsa artısını eksisini yoruma yazabilir mi, alacaklara çok fikir olur 👇 {code_hint}",
            f"Açık konuşayım, ekipçe fırsatları tararken {clean_title} fiyatını görünce bizim bile dikkatimizi çekti. Kullananlar memnun mu, sizce bu bütçede daha mantıklı bir alternatif var mı? {code_hint}",
        ]
    elif subtype == "monitor":
        pool = [
            f"Selamlar! Monitör tarafında fiyatların arttığı şu dönemde {clean_title} mantıklı bir seviyeye inmiş gibi görünüyor. Panel kalitesi ve günlük deneyimi hakkında fikri olanlar yoruma yazarsa herkes faydalanır 🙌 {code_hint}",
        ]
    elif subtype == "shoes":
        pool = [
            f"Selam millet! Günlük giyimde hem rahat hem de bütçeyi üzmeyen bir model arayanlar için {clean_title} güzel indirime girmiş. Daha önce bu markayı/seriyi giyenler tam numara mı yoksa yarım numara büyük mü önerir? 👟 {code_hint}",
            f"Merhaba arkadaşlar! Spor ayakkabı tarafında fırsat denk geldikçe seçmeye çalışıyoruz, {clean_title} de bayağı temiz fiyata düşmüş. Tasarımı ve rahatlığı nasıl sizce, günlük kullanıma gider mi? {code_hint}",
        ]
    elif subtype == "lego":
        pool = [
            f"Koleksiyoncular burada mı? Yapım keyfi ayrı, rafa dizmesi ayrı güzel olan {clean_title} setini indirimde yakalayınca paylaşmadan geçemedik. Sizce bu fiyata koleksiyona eklenir mi, favori seriniz hangisi? 🧱 {code_hint}",
        ]
    else:
        pool = [
            f"Selamlar dostlar! Günlük hayatta gerçekten iş gören ve kullanıcı yorumları da sağlam olan {clean_title} güzel bir fiyata inmiş. Aranızda daha önce deneyip memnun kalan ya da fikir paylaşmak isteyen var mı? ✨ {code_hint}",
            f"Merhaba arkadaşlar! Bizim kanalda sadece denk gelip içimize sinen F/P ürünleri paylaşmaya çalışıyoruz. {clean_title} hakkında siz ne düşünüyorsunuz, bu fiyata hakkını verir mi? 💬 {code_hint}",
        ]

    return sanitize_youtube_text(random.choice(pool))[:500]


def post_first_comment_to_youtube(
    video_id: str,
    comment_text: str,
    access_token: str = None
) -> dict:
    """YouTube Data API v3 commentThreads.insert ile videonun altına otomatik ilk yorumu gönderir."""
    if not video_id or not comment_text:
        return {"success": False, "error": "video_id veya comment_text eksik."}

    if not access_token:
        access_token = get_valid_access_token()

    os.makedirs(TEMP_DIR, exist_ok=True)
    comment_temp = os.path.join(TEMP_DIR, "yt_comment_temp.json")
    payload = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": sanitize_youtube_text(comment_text)
                }
            }
        }
    }
    with open(comment_temp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    cmd = get_curl_cmd([
        "-s", "-X", "POST",
        "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json; charset=UTF-8",
        "--data-binary", f"@{comment_temp}"
    ])
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        resp_json = json.loads(res.stdout)
        if resp_json.get("id"):
            return {
                "success": True,
                "comment_id": resp_json["id"],
                "text": comment_text
            }
        err_obj = resp_json.get("error", {})
        err_msg = err_obj.get("message") or res.stdout
        err_low = str(resp_json).lower()
        needs_reauth = any(k in err_low for k in ("insufficient", "permission", "scope", "unauthorized", "invalid_grant"))
        return {
            "success": False,
            "needs_reauth": needs_reauth,
            "error": err_msg
        }
    except Exception as e:
        return {"success": False, "needs_reauth": False, "error": f"{e} | {res.stdout[:200]}"}


def publish_shorts_to_youtube(
    video_path: str,
    title: str,
    description: str,
    privacy_status: str = None,
    tags: list = None,
    deal_code: str = "",
    new_price: str = "",
    discount_pct: str = "",
    auto_comment: bool = True
) -> dict:
    """
    Hazırlanan MP4 dikey videosunu doğrudan YouTube Shorts olarak kanala yükler.
    
    Özellikler:
    - 9:16 format ve #Shorts etiketiyle otomatik YouTube Shorts sınıflandırması.
    - Windows Python 3.14 SSL bug'ından etkilenmeyen yüksek hızlı curl.exe Resumable Upload mimarisi.
    - 1080x1920 dikey video desteği.
    """
    if not video_path:
        return {"success": False, "error": "Video dosya yolu belirtilmedi."}

    # 🛑 YOUTUBE KESİN GÜVENLİK FİLTRESİ:
    # YouTube Shorts KESİNLİKLE F/P Teknoloji, Gaming Donanım ve Popüler Sneaker kanalıdır.
    # Kozmetik, makyaj veya onaylanmamış kategorideki ürünler KESİNLİKLE yüklenemez!
    try:
        from deal_hunter import is_beauty_product, is_youtube_approved_product
        check_str = f"{title} {description}"
        if is_beauty_product(check_str):
            err_msg = f"🛑 [YOUTUBE GÜVENLİK DUVARI] '{title}' bir kadın/kozmetik ürünüdür ve YouTube Shorts'a yüklenmesi KESİNLİKLE ENGELLENDİ!"
            print(err_msg)
            return {"success": False, "error": err_msg, "skipped": True}
        if not is_youtube_approved_product(check_str):
            err_msg = f"🛑 [YOUTUBE GÜVENLİK DUVARI] '{title}' onaylı bir F/P Teknoloji veya Sneaker ürünü olmadığı için YouTube Shorts'a yüklenmesi KESİNLİKLE ENGELLENDİ!"
            print(err_msg)
            return {"success": False, "error": err_msg, "skipped": True}
    except Exception as e_chk:
        print(f"[YouTube Publisher] ⚠️ Güvenlik filtresi denetim uyarısı: {e_chk}")

    if not os.path.exists(video_path):
        if video_path.startswith("http://") or video_path.startswith("https://"):
            temp_vid = os.path.join(DATA_DIR, "temp_yt_upload.mp4")
            cmd = get_curl_cmd(["-s", "-L", video_path, "-o", temp_vid])
            safe_run_subprocess(cmd)
            if os.path.exists(temp_vid) and os.path.getsize(temp_vid) > 1000:
                video_path = temp_vid
            else:
                return {"success": False, "error": f"Uzak video indirilemedi: {video_path}"}
        else:
            return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

    cred_info = check_youtube_credentials()
    if not cred_info.get("token_ready"):
        print(f"[YouTube Publisher] ⚠️ {cred_info.get('message', 'Yetkilendirme eksik')}")
        return {"success": False, "error": cred_info.get("message", "Yetkilendirme eksik")}

    try:
        access_token = get_valid_access_token()
    except Exception as e:
        return {"success": False, "error": f"Yetkilendirme anahtarı alınamadı: {e}"}

    # Başlığı Shorts standartlarına uyarla (Maks 100 karakter, #Shorts ekle, < > temizle)
    clean_title = sanitize_youtube_text(title)
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        clean_title = f"{clean_title[:88]} #Shorts"
    else:
        clean_title = clean_title[:100]

    # Açıklama metnini düzenle (#reklam, web vitrin linki, #Shorts zorunlu, < > temizle)
    clean_desc = sanitize_youtube_text(description)
    from config import SITE_URL
    web_link = f"{SITE_URL}?utm_source=youtube&utm_medium=shorts"
    if SITE_URL not in clean_desc:
        clean_desc = f"{clean_desc}\n\n⚡ Tüm Dip Fiyatlar & İndirim Radarı:\n🔗 {web_link}"

    default_tags = ["shorts", "indirim", "fırsat", "kampanya", "alışveriş", "sıcakfırsat", "teknoloji"]
    if tags:
        sanitized_tags = [sanitize_youtube_text(t) for t in tags if t]
        default_tags = list(set(default_tags + sanitized_tags))

    privacy = privacy_status or YOUTUBE_PRIVACY_STATUS or "public"

    metadata = {
        "snippet": {
            "title": clean_title,
            "description": clean_desc,
            "tags": default_tags[:15],
            "categoryId": "28"  # 28: Science & Technology
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    file_size = os.path.getsize(video_path)
    print(f"\n[YouTube Publisher] 🚀 YouTube Shorts yüklemesi başlatılıyor...")
    print(f"📌 Başlık:   {clean_title}")
    print(f"🔒 Gizlilik:  {privacy.upper()}")
    print(f"📦 Dosya:     {os.path.basename(video_path)} ({int(file_size / (1024*1024))} MB)")

    # 1. Resumable Upload Başlat (Start session - Güvenli UTF-8 JSON dosyası üzerinden)
    meta_temp = os.path.join(DATA_DIR, "yt_meta_temp.json")
    with open(meta_temp, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    init_cmd = get_curl_cmd([
        "-s", "-i", "-X", "POST",
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json; charset=UTF-8",
        "-H", "X-Upload-Content-Type: video/mp4",
        "-H", f"X-Upload-Content-Length: {file_size}",
        "--data-binary", f"@{meta_temp}"
    ])

    init_res = safe_run_subprocess(init_cmd, capture_output=True, text=True, encoding="utf-8")
    headers = init_res.stdout

    upload_url = None
    for line in headers.splitlines():
        if line.lower().startswith("location:"):
            upload_url = line.split(":", 1)[1].strip()
            break

    if not upload_url:
        print(f"[YouTube Publisher] ❌ Resumable oturum açılamadı:\n{headers}")
        err_detail = "Bilinmeyen hata"
        try:
            json_start = headers.find("{")
            if json_start != -1:
                err_obj = json.loads(headers[json_start:])
                err_detail = err_obj.get("error", {}).get("message", headers[:200])
            else:
                err_detail = headers[:200]
        except Exception:
            err_detail = headers[:200]
        return {"success": False, "error": f"Oturum açılamadı: {err_detail}"}

    # 2. Video Dosyasını Yükle (PUT binary video)
    print("[YouTube Publisher] ⏳ Video Google sunucularına aktarılıyor...")
    put_cmd = get_curl_cmd([
        "-s", "-X", "PUT",
        upload_url,
        "-H", "Content-Type: video/mp4",
        "-H", f"Content-Length: {file_size}",
        "--upload-file", video_path
    ])

    put_res = safe_run_subprocess(put_cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        resp_json = json.loads(put_res.stdout)
        video_id = resp_json.get("id")
        if video_id:
            shorts_url = f"https://www.youtube.com/shorts/{video_id}"
            print(f"🎉 [YouTube Publisher] Video başarıyla yüklendi!")
            print(f"🔗 Shorts Linki: {shorts_url}")

            comment_res = None
            if auto_comment:
                try:
                    time.sleep(2)
                    comment_text = generate_friendly_youtube_comment(
                        title=clean_title.replace("#Shorts", "").replace("#shorts", "").strip(),
                        new_price=new_price,
                        discount_pct=discount_pct,
                        deal_code=deal_code,
                        description=clean_desc,
                    )
                    comment_res = post_first_comment_to_youtube(
                        video_id=video_id,
                        comment_text=comment_text,
                        access_token=access_token,
                    )
                    if comment_res.get("success"):
                        print(f"💬 [YouTube İlk Yorum] Samimi topluluk yorumu paylaşıldı: {comment_text}")
                    elif comment_res.get("needs_reauth"):
                        print("⚠️ [YouTube İlk Yorum] Mevcut token'da yorum yazma izni yok (youtube.force-ssl için 'python youtube_auth.py' yenilemesi gerekir).")
                    else:
                        print(f"⚠️ [YouTube İlk Yorum] Yorum eklenemedi (video yayını etkilenmedi): {comment_res.get('error')}")
                except Exception as e_cmt:
                    print(f"⚠️ [YouTube İlk Yorum] İstisna (video yayını etkilenmedi): {e_cmt}")

            return {
                "success": True,
                "video_id": video_id,
                "url": shorts_url,
                "privacy": privacy,
                "comment": comment_res
            }
        else:
            print(f"[YouTube Publisher] ❌ Yükleme yanıt hatası: {put_res.stdout}")
            return {"success": False, "error": put_res.stdout}
    except Exception as e:
        print(f"[YouTube Publisher] ❌ Ayrıştırma hatası: {e} | Çıktı: {put_res.stdout}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("--- YOUTUBE SHORTS PUBLISHER DURUMU ---")
    st = check_youtube_credentials()
    print(json.dumps(st, ensure_ascii=False, indent=2))
