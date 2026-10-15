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
    "link", "fiyat", "nerede", "nerden", "nereden", "al",
    "fiyatı", "fiyatı ne", "istiyorum", "gönder", "dm", "satın al"
]

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
        # Son 1000 yorumu sakla
        recent = list(replied)[-1000:]
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
    return f"{SITE_URL}?utm_source=instagram&utm_medium=dm"

def check_and_reply_comments(max_medias: int = 5, limit_per_run: int = 10) -> int:
    """
    Son paylaşılan Instagram gönderilerindeki/Reels'lerdeki yorumları denetler.
    'LİNK', 'FİYAT' vb. yazan kullanıcılara DM ile doğrudan ürün linkini gönderir
    ve yorumlarını beğenir.
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

        print(f"\n[Auto DM] 🔍 Son {max_medias} Reels/Gönderi yorumları taranıyor (@{creds.get('username')})...")
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
            target_link = extract_link_from_caption(caption)

            # İlk satırdan ürün başlığını tahmin et
            lines = [l.strip() for l in caption.split("\n") if l.strip()]
            product_name = lines[0].replace("🔥", "").replace("🚨", "").strip() if lines else "Fırsat Ürünü"

            try:
                comments = cl.media_comments(media_pk, amount=30)
            except Exception as ec:
                print(f"[Auto DM] Yorum çekme hatası (Medya {media_pk}): {ec}")
                continue

            for comment in comments:
                if processed_count >= limit_per_run:
                    break

                c_id = str(comment.pk)
                if c_id in replied_set:
                    continue

                # Kendi yorumumuzsa atla
                if comment.user.pk == user_id:
                    replied_set.add(c_id)
                    continue

                text_clean = (comment.text or "").strip().lower()
                # Kelime eşleşmesi kontrolü
                is_match = any(re.search(rf"\b{re.escape(kw)}\b", text_clean, re.IGNORECASE) for kw in DM_KEYWORDS)

                if is_match:
                    user_pk = comment.user.pk
                    user_handle = comment.user.username
                    print(f"[Auto DM] 🎯 Eşleşen Yorum: @{user_handle} -> \"{comment.text}\"")

                    dm_message = (
                        f"Selam @{user_handle}! 👋\n\n"
                        f"Videomuzda sorduğun fırsatın indirimli satın alma linki:\n"
                        f"🛒 {product_name}\n"
                        f"👉 Link: {target_link}\n\n"
                        f"⚡ Tüm anlık indirimler & kupon radarı için web vitrinimiz:\n"
                        f"🌐 {SITE_URL}?utm_source=instagram&utm_medium=auto_dm\n\n"
                        f"Keyifli alışverişler! 🎉"
                    )

                    try:
                        # 1. Kullanıcıya DM Gönder
                        cl.direct_send(dm_message, user_ids=[user_pk])
                        print(f"✅ [Auto DM] DM Gönderildi -> @{user_handle}")

                        # 2. Yorumu Beğen (Kullanıcıya bildirim gider)
                        try:
                            cl.comment_like(comment.pk)
                        except Exception:
                            pass

                        replied_set.add(c_id)
                        processed_count += 1
                        time.sleep(3)  # Instagram spam koruması için 3 saniye bekle

                    except Exception as edm:
                        print(f"❌ [Auto DM] DM gönderilemedi (@{user_handle}): {edm}")
                        # Tekrar denenmesin diye ekle
                        replied_set.add(c_id)

        save_replied_comments(replied_set)
        if processed_count > 0:
            print(f"🎉 [Auto DM] Bu döngüde toplam {processed_count} kişiye indirim linki DM ile gönderildi!\n")
        else:
            print("[Auto DM] 💤 Yeni link talep eden yorum bulunamadı.\n")

        return processed_count

    except Exception as e:
        print(f"[Auto DM] Genel hata: {e}")
        return 0

if __name__ == "__main__":
    check_and_reply_comments()
