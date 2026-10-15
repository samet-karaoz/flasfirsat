import os
import time
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from config import BASE_DIR, DATA_DIR, SITE_URL

load_dotenv()

REPLIED_COMMENTS_FILE = os.path.join(DATA_DIR, "replied_comments.json")
DM_KEYWORDS = [
    "link", "linki", "fiyat", "fiyati", "nerede", "nerden", "nereden", "al",
    "fiyatı", "fiyatı ne", "istiyorum", "gönder", "gonder", "dm", "satın al", "satin al"
]

def normalize_turkish(text: str) -> str:
    """Türkçe karakterleri güvenli küçük harfe çevirir."""
    if not text:
        return ""
    # Türkçe İ -> i, I -> ı -> i
    t = text.replace("İ", "i").replace("I", "i").replace("ı", "i")
    t = t.lower()
    t = t.replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    return t

def load_replied_comments() -> set:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(REPLIED_COMMENTS_FILE):
        try:
            with open(REPLIED_COMMENTS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_replied_comments(replied: set):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        recent = list(replied)[-2000:]
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
    Açıklama metninden ve yerel geçmişten en doğru ürün linkini ve başlığını bulur.
    Döner: (product_name, target_url)
    """
    # 1. Caption içinde doğrudan URL var mı?
    cap_url = extract_link_from_caption(caption)

    # İlk satırdan ürün başlığı
    lines = [l.strip() for l in (caption or "").split("\n") if l.strip()]
    product_name = lines[0].replace("🔥", "").replace("🚨", "").strip() if lines else "Fırsat Ürünü"

    # 2. autopilot_history.json veya deals.json'dan gerçek affiliate_url ara
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
                        # Başlık caption içinde geçiyor mu?
                        words = [w.lower() for w in title.split() if len(w) > 3]
                        if words and any(w in caption.lower() for w in words):
                            return (title or product_name, aff_url)
                        if not cap_url:
                            cap_url = aff_url
                            if title:
                                product_name = title
                            break
        except Exception:
            pass

    if cap_url:
        return (product_name, cap_url)

    # 3. Fallback: Web Vitrini
    return (product_name, f"{SITE_URL}?utm_source=instagram&utm_medium=auto_dm")

def check_and_reply_comments(max_medias: int = 5, limit_per_run: int = 10) -> int:
    """
    Son paylaşılan Instagram Reels/Gönderilerdeki yorumları ve alt yanıtları denetler.
    'LİNK', 'FİYAT' vb. yazan kullanıcılara DM ile doğrudan ürün linkini gönderir,
    kullanıcının yorumunu beğenir ve altına bilgilendirme yanıtı bırakır.
    """
    from instagram_publisher import check_instagram_credentials, get_instagrapi_client

    creds = check_instagram_credentials()
    if not creds.get("configured") or creds.get("mode") != "instagrapi":
        print("[Auto DM] ⚠️ Instagram oturumu yapılandırılmamış. Atlanıyor.")
        return 0

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

            try:
                root_comments = cl.media_comments(media_pk, amount=40)
            except Exception as ec:
                print(f"[Auto DM] Yorum çekme hatası (Medya {media_pk}): {ec}")
                continue

            all_comments = []
            for rc in root_comments:
                all_comments.append(rc)
                # Eğer yorumun alt yanıtı varsa veya bizim sabitlenen yorumumuzsa yanıtları da çek
                child_cnt = getattr(rc, "child_comment_count", 0) or 0
                if child_cnt > 0 or rc.user.pk == user_id:
                    try:
                        replies = cl.media_comment_replies(media_pk, rc.pk)
                        if replies:
                            for rep in replies:
                                all_comments.append(rep)
                    except Exception:
                        pass

            for comment in all_comments:
                if processed_count >= limit_per_run:
                    break

                c_id = str(comment.pk)
                if c_id in replied_set:
                    continue

                # Kendi hesabımızın yorumlarını atla
                if comment.user.pk == user_id:
                    replied_set.add(c_id)
                    continue

                raw_text = comment.text or ""
                text_clean = normalize_turkish(raw_text)

                # Anahtar kelime eşleşmesi
                is_match = False
                for kw in DM_KEYWORDS:
                    kw_clean = normalize_turkish(kw)
                    # Kelime sınırıyla veya doğrudan içeren
                    if re.search(rf"\b{re.escape(kw_clean)}\b", text_clean) or kw_clean in text_clean.split():
                        is_match = True
                        break

                if is_match:
                    user_pk = comment.user.pk
                    user_handle = comment.user.username
                    print(f"[Auto DM] 🎯 Eşleşen Yorum: @{user_handle} -> \"{raw_text}\" (Medya: {media.code})")

                    dm_message = (
                        f"Selam @{user_handle}! 👋\n\n"
                        f"Videomuzda sorduğun fırsatın indirimli satın alma linki:\n"
                        f"🛒 {product_name}\n"
                        f"👉 Link: {target_link}\n\n"
                        f"⚡ Tüm anlık indirimler & kupon radarı için web vitrinimiz:\n"
                        f"🌐 {SITE_URL}?utm_source=instagram&utm_medium=auto_dm\n\n"
                        f"Keyifli alışverişler! 🎉"
                    )

                    dm_sent = False
                    # 1. Kullanıcıya DM Gönder
                    try:
                        cl.direct_send(dm_message, user_ids=[user_pk])
                        print(f"✅ [Auto DM] DM Gönderildi -> @{user_handle}")
                        dm_sent = True
                    except Exception as edm:
                        print(f"⚠️ [Auto DM] DM doğrudan iletilemedi (@{user_handle}): {edm}")

                    # 2. Yorumu Beğen
                    try:
                        cl.comment_like(comment.pk)
                    except Exception:
                        pass

                    # 3. Yorumun Altına Yanıt Bırak (Kullanıcıya bildirim gider ve istek kutusuna yönlendirir)
                    try:
                        reply_text = f"@{user_handle} Linki DM kutuna ilettik! 📩 (Gelen kutundaki İstekler / Gizli İstekler sekmesine bakmayı unutma)"
                        cl.media_comment(media_pk, reply_text, replied_to_comment_id=comment.pk)
                        print(f"💬 [Auto DM] Yoruma yanıt yazıldı -> @{user_handle}")
                    except Exception as erp:
                        print(f"⚠️ [Auto DM] Yoruma yanıt verilemedi: {erp}")

                    replied_set.add(c_id)
                    processed_count += 1
                    time.sleep(3)  # Instagram spam koruması

        save_replied_comments(replied_set)
        if processed_count > 0:
            print(f"🎉 [Auto DM] Bu döngüde toplam {processed_count} kişiye indirim linki iletildi!\n")
        else:
            print("[Auto DM] 💤 Yeni link talep eden yorum bulunamadı.\n")

        return processed_count

    except Exception as e:
        print(f"[Auto DM] Genel hata: {e}")
        return 0

if __name__ == "__main__":
    check_and_reply_comments()
