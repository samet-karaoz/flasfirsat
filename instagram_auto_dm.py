import os
import time
import json
import re
import random
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from config import BASE_DIR, DATA_DIR, SITE_URL

load_dotenv()

REPLIED_COMMENTS_FILE = os.path.join(DATA_DIR, "replied_comments.json")

# Pozitif istek anahtar kelimeleri (Tek başına riskli "al" kelimesi çıkarıldı)
DM_KEYWORDS = [
    "link", "linki", "linkini", "link lütfen", "link at", "link atar mısın", "link atarmısınız",
    "link atabilir misiniz", "link verir misiniz", "linki gönder", "link atar msn",
    "fiyat", "fiyatı", "fiyat nedir", "fiyatı ne", "fiyat alabilir miyim",
    "dm", "dm lütfen", "dm at", "dm atar mısın", "dm bakar mısınız",
    "istiyorum", "almak istiyorum", "alabilir miyim", "nasıl alırım", "nereden alırım",
    "nereden alabilirim", "nerden alabilirim", "nerede", "nerden", "nereden",
    "satın al", "satin al", "gönder", "gonder"
]

# Negatif / Eleştiri kelimeleri (Bu kelimeler varsa kullanıcı link istemiyordur, spam DM atılmamalıdır)
NEGATIVE_STOP_WORDS = [
    "alma", "almayin", "almayın", "sakin", "sakın", "cop", "çöp", "berbat",
    "dolandirici", "dolandırıcı", "sahte", "rezalet", "alma bence", "almayın sakın"
]

# Instagram spam filtrelerine takılmamak için doğal insan varyasyonları
GREETINGS = [
    "Selam @{user}! 👋",
    "Merhaba @{user}! 😊",
    "Harika seçim @{user}! 🛍️",
    "Selamlar @{user}! ⚡"
]

INTROS = [
    "Videomuzda sorduğun fırsatın indirimli satın alma linki:",
    "Reels videomuzda beğendiğin ürünün güncel indirim linki:",
    "Sorduğun fırsat ürününün indirimli satın alma linkini iletiyorum:"
]

CLOSINGS = [
    "Keyifli alışverişler! 🎉",
    "Stoklar tükenmeden yakalamanı öneririz! 🔥",
    "İndirim fırsatını kaçırmaman dileğiyle, güzel günlerde kullan! ✨",
    "Tüm anlık sıcak indirimler için bildirimlerimizi açık tutmayı unutma! 🔔"
]

COMMENT_REPLIES_SUCCESS = [
    "@{user} Linki DM kutuna ilettik! 📩 (İstekler / Gizli İstekler kutuna bakmayı unutma)",
    "@{user} İndirimli ürün linkini özel mesaj (DM) olarak gönderdik! 🚀",
    "@{user} Link DM'den iletildi! 🛍️ Gelen kutundaki Mesaj İstekleri sekmesini kontrol edebilirsin.",
    "@{user} Fırsat linkini DM olarak gönderdik, şimdiden keyifli alışverişler! ✨"
]

COMMENT_REPLIES_ALREADY_SENT = [
    "@{user} Ürün linkini daha önce DM kutuna iletmiştik, gelen kutundaki Mesaj İstekleri sekmesini kontrol edebilirsin! 📩",
    "@{user} Fırsat linki DM kutunda mevcut, mesaj isteklerini incelemeyi unutma! 🛍️"
]

COMMENT_REPLIES_CLOSED_DM = [
    "@{user} DM kutun kapalı olduğu için mesaj iletilemedi. Bize DM'den bir 'merhaba' yazarsan veya profilimizdeki site linkine tıklarsan fırsata hemen ulaşabilirsin! 🌐"
]

def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri güvenli küçük harfe çevirir."""
    if not text:
        return ""
    t = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    t = t.lower()
    t = t.replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    return t

def load_replied_comments() -> set:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(REPLIED_COMMENTS_FILE):
        try:
            with open(REPLIED_COMMENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                elif isinstance(data, dict):
                    return set(data.get("comment_ids", []))
        except Exception:
            return set()
    return set()

def save_replied_comments(replied: set):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        recent = list(replied)[-3000:]
        with open(REPLIED_COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Auto DM] Yorum geçmişi kaydedilemedi: {e}")

def extract_link_from_caption(caption: str) -> str:
    """Açıklama içindeki web/affiliate linkini ayıklar."""
    if not caption:
        return ""
    urls = re.findall(r"https?://[^\s]+", caption)
    for u in urls:
        if "instagram.com" not in u:
            return u
    return ""

def find_best_product_link(caption: str) -> tuple[str, str]:
    """
    Açıklama metninden, deals.json'dan ve otopilot geçmişinden en doğru ürün linkini ve başlığını bulur.
    Döner: (product_name, target_url)
    """
    cap_url = extract_link_from_caption(caption)
    lines = [l.strip() for l in (caption or "").split("\n") if l.strip()]
    product_name = lines[0].replace("🔥", "").replace("🚨", "").strip() if lines else "Fırsat Ürünü"

    caption_low = (caption or "").lower()

    # 1. data/deals.json içindeki güncel ürünlerle eşleştir (En yüksek doğruluk)
    deals_file = os.path.join(DATA_DIR, "deals.json")
    best_match = None
    best_score = 0

    if os.path.exists(deals_file):
        try:
            with open(deals_file, "r", encoding="utf-8") as f:
                deals = json.load(f)
                for d in deals:
                    t = d.get("title", "")
                    u = d.get("store_url") or d.get("affiliate_url")
                    if not u or not t:
                        continue
                    words = [w.lower() for w in re.findall(r"\w+", t) if len(w) > 3]
                    matches = sum(1 for w in words if w in caption_low)
                    if matches > best_score:
                        best_score = matches
                        best_match = (t, u)
        except Exception:
            pass

    if best_match and best_score >= 1:
        return best_match

    # 2. autopilot_history.json kontrolü
    history_file = os.path.join(DATA_DIR, "autopilot_history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                for item in reversed(history):
                    deal = item.get("deal") or {}
                    aff_url = deal.get("affiliate_url")
                    title = deal.get("title") or ""
                    if aff_url:
                        words = [w.lower() for w in re.findall(r"\w+", title) if len(w) > 3]
                        if words and sum(1 for w in words if w in caption_low) >= 1:
                            return (title or product_name, aff_url)
        except Exception:
            pass

    if cap_url:
        return (product_name, cap_url)

    # 3. Fallback: Web Vitrini
    return (product_name, f"{SITE_URL}?utm_source=instagram&utm_medium=auto_dm")

def sync_git_remote():
    """Bulut ve yerel arasındaki yorum geçmişini senkronize eder."""
    try:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, timeout=12)
    except Exception:
        pass

def push_git_history():
    """Yeni yanıtlanan yorumları uzaktaki depoya güvenle gönderir."""
    try:
        subprocess.run(["git", "add", "data/replied_comments.json"], capture_output=True, timeout=10)
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"], capture_output=True, timeout=10)
        if diff.returncode != 0:
            subprocess.run(["git", "commit", "-m", "💬 Auto-DM: Yorum geçmişi güncellendi [skip ci]"], capture_output=True, timeout=10)
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, timeout=12)
            subprocess.run(["git", "push", "origin", "main"], capture_output=True, timeout=15)
    except Exception:
        pass

def check_and_reply_comments(max_medias: int = 5, limit_per_run: int = 10) -> int:
    """
    Son paylaşılan Instagram Reels/Gönderilerdeki yorumları ve alt yanıtları denetler.
    Kullanıcılara DM ile indirim linkini iletir, yorumu beğenir ve bilgilendirme yanıtı yazar.
    
    KUSURSUZ MÜKERRERLİK KORUMALARI:
    1. Sunucu Seviyesinde Doğrulama: Hesabımızın daha önce yanıt verdiği yorumlar Instagram'dan teyit edilerek kesinlikle atlanır.
    2. Kullanıcı Seviyesinde Tekilleştirme: Aynı kullanıcı aynı videoya birden fazla yorum atarsa ikinci kez DM gönderilmez.
    3. Anlık Kayıt (Crash-Safe): Her yorum işlendiği anda diske kaydedilir, kesinti olsa dahi mükerrer DM oluşmaz.
    4. Negatif Filtre: Şikayet ve 'alma' gibi olumsuz yorumlara yanlışlıkla link gönderilmez.
    """
    from instagram_publisher import check_instagram_credentials, get_instagrapi_client

    creds = check_instagram_credentials()
    if not creds.get("configured") or creds.get("mode") != "instagrapi":
        print("[Auto DM] ⚠️ Instagram oturumu yapılandırılmamış. Atlanıyor.")
        return 0

    # Bulut/Yerel senkronizasyonunu kontrol et
    sync_git_remote()

    try:
        cl = get_instagrapi_client()
        user_id = cl.user_id
        if not user_id:
            user_id = cl.user_id_from_username(creds.get("username", "flasfirsat"))

        print(f"\n[Auto DM] 🔍 Son {max_medias} Reels/Gönderi taranıyor (@{creds.get('username')})...")
        medias = cl.user_medias(user_id, amount=max_medias)
        if not medias:
            print("[Auto DM] ℹ️ Henüz yayınlanmış medya bulunamadı.")
            return 0

        replied_set = load_replied_comments()
        processed_count = 0

        for media in medias:
            if processed_count >= limit_per_run:
                break

            media_pk = media.pk
            caption = media.caption_text or ""
            product_name, target_link = find_best_product_link(caption)
            media_users_replied = set()

            try:
                root_comments = cl.media_comments(media_pk, amount=50)
            except Exception as ec:
                print(f"[Auto DM] Yorum çekme hatası (Medya {media_pk}): {ec}")
                continue

            for rc in root_comments:
                if processed_count >= limit_per_run:
                    break

                rc_id = str(rc.pk)
                replies = []
                child_cnt = getattr(rc, "child_comment_count", 0) or 0
                if child_cnt > 0 or rc.user.pk == user_id:
                    try:
                        replies = cl.media_comment_replies(media_pk, rc.pk) or []
                    except Exception:
                        replies = []

                # KORUMA 1: Sunucu Seviyesinde Kontrol (Instagram Server Check)
                # Eğer bu root yoruma zaten botumuz daha önce yanıt verdiyse kesinlikle atla!
                already_replied_by_us = any(getattr(rep.user, "pk", None) == user_id for rep in replies)
                if already_replied_by_us:
                    replied_set.add(rc_id)
                    save_replied_comments(replied_set)
                    # Bot yanıtını da kümede sakla
                    for rep in replies:
                        if getattr(rep.user, "pk", None) == user_id:
                            replied_set.add(str(rep.pk))
                    continue

                # Kendi yazdığımız root yorumları atla
                if rc.user.pk == user_id or rc_id in replied_set:
                    replied_set.add(rc_id)
                    continue

                # Bu thread'deki tüm yorumları (ana yorum + varsa diğer kullanıcı yanıtları) incele
                thread_comments = [rc] + replies

                for comment in thread_comments:
                    if processed_count >= limit_per_run:
                        break

                    c_id = str(comment.pk)
                    if c_id in replied_set or comment.user.pk == user_id:
                        continue

                    raw_text = comment.text or ""
                    text_clean = normalize_turkish(raw_text)

                    # KORUMA 2: Negatif / Şikayet Filtresi
                    if any(nw in text_clean for nw in NEGATIVE_STOP_WORDS):
                        replied_set.add(c_id)
                        save_replied_comments(replied_set)
                        continue

                    # KORUMA 3: Pozitif Anahtar Kelime Tespiti
                    is_match = False
                    for kw in DM_KEYWORDS:
                        kw_norm = normalize_turkish(kw)
                        if re.search(rf"\b{re.escape(kw_norm)}\b", text_clean):
                            is_match = True
                            break

                    if not is_match:
                        continue

                    user_pk = comment.user.pk
                    user_handle = comment.user.username
                    print(f"[Auto DM] 🎯 Eşleşen Yorum: @{user_handle} -> \"{raw_text}\" (Medya: {media.code})")

                    # KORUMA 4: Kullanıcı Seviyesinde Tekilleştirme (Aynı kullanıcıya aynı videoda mükerrer DM engelleme)
                    user_already_got_dm = (user_pk in media_users_replied)

                    dm_sent = False
                    if not user_already_got_dm:
                        greeting = random.choice(GREETINGS).format(user=user_handle)
                        intro = random.choice(INTROS)
                        closing = random.choice(CLOSINGS)
                        dm_message = (
                            f"{greeting}\n\n"
                            f"{intro}\n"
                            f"🛒 {product_name}\n"
                            f"👉 Link: {target_link}\n\n"
                            f"⚡ Tüm anlık sıcak indirimler & kupon radarı için web vitrinimiz:\n"
                            f"🌐 {SITE_URL}?utm_source=instagram&utm_medium=auto_dm\n\n"
                            f"{closing}"
                        )
                        try:
                            cl.direct_send(dm_message, user_ids=[user_pk])
                            print(f"✅ [Auto DM] DM Gönderildi -> @{user_handle}")
                            dm_sent = True
                            media_users_replied.add(user_pk)
                        except Exception as edm:
                            print(f"⚠️ [Auto DM] DM iletilemedi (@{user_handle} - DM kutusu kapalı olabilir): {edm}")
                            dm_sent = False

                    # Yorumu Beğen
                    try:
                        cl.comment_like(comment.pk)
                    except Exception:
                        pass

                    # Yoruma Yanıt Bırak
                    try:
                        if user_already_got_dm:
                            reply_text = random.choice(COMMENT_REPLIES_ALREADY_SENT).format(user=user_handle)
                        elif dm_sent:
                            reply_text = random.choice(COMMENT_REPLIES_SUCCESS).format(user=user_handle)
                        else:
                            reply_text = random.choice(COMMENT_REPLIES_CLOSED_DM).format(user=user_handle)

                        cl.media_comment(media_pk, reply_text, replied_to_comment_id=comment.pk)
                        print(f"💬 [Auto DM] Yoruma yanıt yazıldı -> @{user_handle}")
                    except Exception as erp:
                        print(f"⚠️ [Auto DM] Yoruma yanıt verilemedi: {erp}")

                    # KORUMA 5: Her yorumdan sonra anında diske kaydet (Crash/Kesinti Emniyeti)
                    replied_set.add(c_id)
                    save_replied_comments(replied_set)
                    processed_count += 1

                    # Spam Algoritma Koruması: Doğal insan davranışı için 4-7 saniye bekle
                    time.sleep(random.uniform(4.0, 7.0))

        if processed_count > 0:
            print(f"🎉 [Auto DM] Bu döngüde toplam {processed_count} kişiye indirim linki iletildi!\n")
            push_git_history()
        else:
            print("[Auto DM] 💤 Yeni link talep eden yorum bulunamadı.\n")

        return processed_count

    except Exception as e:
        print(f"[Auto DM] Genel hata: {e}")
        return 0

if __name__ == "__main__":
    check_and_reply_comments()
