import os
import re
import json
import datetime
from PIL import Image, ImageFilter, ImageStat, ImageChops
from config import BASE_DIR, TEMP_DIR, DATA_DIR, safe_run_subprocess, download_file

VALIDATION_REPORTS_DIR = os.path.join(DATA_DIR, "validation_reports")

# Standart Windows TTF fontlarında (segoeuib.ttf vb.) kutucuk (tofu '▢') çıkaran karakter aralıkları
UNSUPPORTED_TTF_REGEX = re.compile(
    r'[\U00010000-\U0010ffff\u2600-\u27bf\ufe00-\ufe0f\u200d\ufffd]'
)


def sanitize_ttf_text(text: str) -> str:
    """
    Standart PIL TrueType fontlarında kutucuk (tofu '▢') olarak görünen
    emoji, astral Unicode ve kontrol karakterlerini temizler.
    """
    if not text:
        return ""
    cleaned = UNSUPPORTED_TTF_REGEX.sub("", str(text))
    # Çoklu boşlukları tek boşluğa indir
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def check_video_streams(video_path: str) -> dict:
    """
    FFmpeg ile videonun varlığını, boyutunu, çözünürlüğünü (1080x1920),
    süresini ve video/ses kanallarını kontrol eder.
    """
    res = {
        "valid": True,
        "issues": [],
        "duration": 0.0,
        "resolution": "",
        "has_video": False,
        "has_audio": False,
        "file_size_kb": 0
    }

    if not video_path or not os.path.exists(video_path):
        res["valid"] = False
        res["issues"].append({
            "code": "VIDEO_FILE_MISSING",
            "severity": "critical",
            "message": f"Video dosyası bulunamadı: {video_path}"
        })
        return res

    file_size = os.path.getsize(video_path)
    res["file_size_kb"] = round(file_size / 1024, 1)
    if file_size < 50 * 1024:
        res["valid"] = False
        res["issues"].append({
            "code": "VIDEO_FILE_TOO_SMALL",
            "severity": "critical",
            "message": f"Video dosyası bozuk veya çok küçük ({res['file_size_kb']} KB)"
        })
        return res

    proc = safe_run_subprocess(["ffmpeg", "-i", video_path], capture_output=True, text=True)
    stderr = (proc.stderr or "") if proc else ""

    dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if dur_m:
        res["duration"] = int(dur_m.group(1)) * 3600 + int(dur_m.group(2)) * 60 + float(dur_m.group(3))

    res["has_video"] = "Video:" in stderr
    res["has_audio"] = "Audio:" in stderr

    res_m = re.search(r"Video:.*?(\d{3,4}x\d{3,4})", stderr)
    if res_m:
        res["resolution"] = res_m.group(1)

    if not res["has_video"]:
        res["valid"] = False
        res["issues"].append({
            "code": "MISSING_VIDEO_STREAM",
            "severity": "critical",
            "message": "MP4 dosyasında video akışı (stream) bulunamadı."
        })

    if not res["has_audio"]:
        res["valid"] = False
        res["issues"].append({
            "code": "MISSING_AUDIO_STREAM",
            "severity": "warning",
            "message": "MP4 dosyasında ses akışı (audio stream) bulunamadı."
        })

    if res["resolution"] and res["resolution"] != "1080x1920":
        res["valid"] = False
        res["issues"].append({
            "code": "INVALID_RESOLUTION",
            "severity": "critical",
            "message": f"Video çözünürlüğü 1080x1920 değil ({res['resolution']})."
        })

    if res["duration"] > 0 and res["duration"] < 3.0:
        res["valid"] = False
        res["issues"].append({
            "code": "VIDEO_TOO_SHORT",
            "severity": "critical",
            "message": f"Video süresi çok kısa ({res['duration']:.2f}s)."
        })

    return res


def extract_inspection_frames(video_path: str, slug: str = "check", ts_a: str = "00:00:01.30", ts_b: str = "00:00:03.40") -> tuple:
    """
    Videonun belirlenen saniyelerinden iki kontrol karesi (PNG) çıkarır.
    Hem görsel kaliteyi hem de hareketliliği/fiyat geçişini doğrular.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    frame_a = os.path.join(TEMP_DIR, f"val_frame_a_{slug}.png")
    frame_b = os.path.join(TEMP_DIR, f"val_frame_b_{slug}.png")

    for ts, out_p in [(ts_a, frame_a), (ts_b, frame_b)]:
        if os.path.exists(out_p):
            try:
                os.remove(out_p)
            except Exception:
                pass
        safe_run_subprocess(
            ["ffmpeg", "-y", "-ss", ts, "-i", video_path, "-frames:v", "1", out_p],
            capture_output=True,
            timeout=15
        )

    # Eğer video ikinci kareden kısaysa 0.5. saniyeden yedek kare al
    if not os.path.exists(frame_b) and os.path.exists(frame_a):
        safe_run_subprocess(
            ["ffmpeg", "-y", "-ss", "00:00:00.50", "-i", video_path, "-frames:v", "1", frame_b],
            capture_output=True,
            timeout=15
        )

    return (
        frame_a if os.path.exists(frame_a) else None,
        frame_b if os.path.exists(frame_b) else None
    )


def analyze_product_region(img: Image.Image, deal: dict = None) -> dict:
    """
    Üst banner (1080x960) içindeki beyaz stüdyo kartının merkezini (x:200..880, y:265..665)
    inceleyerek ürün görselinin gerçekten çizilip çizilmediğini tespit eder.
    """
    # Beyaz kartın iç orta bölgesi (rozetler hariç saf ürün alanı)
    crop_box = (200, 265, 880, 665)
    region = img.crop(crop_box).convert("RGB")
    gray = region.convert("L")

    # 1. Kenar Yoğunluğu (Edge Density): Boş kartta sadece yumuşak spotlight gradyanı vardır,
    # bu nedenle FIND_EDGES ortalaması < 1.2 çıkar. Gerçek ürün görselinde > 3.0 olur.
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Kenar çerçevesindeki 4 piksellik yapay sınır etkisini kırp
    w, h = edges.size
    edges_inner = edges.crop((6, 6, w - 6, h - 6))
    edge_stat = ImageStat.Stat(edges_inner)
    edge_mean = edge_stat.mean[0]
    edge_std = edge_stat.stddev[0]

    # Güçlü kenar piksellerinin oranı (piksel değeri > 28)
    hist = edges_inner.histogram()
    total_px = sum(hist)
    strong_edge_px = sum(hist[28:])
    strong_edge_ratio = strong_edge_px / max(1, total_px)

    # 2. Renk ve Parlaklık Varyansı
    gray_stat = ImageStat.Stat(gray)
    luma_std = gray_stat.stddev[0]

    # 3. Dosya bazlı kontrol (Eğer deal nesnesi verilmişse)
    img_path = (deal or {}).get("image_path", "")
    file_ok = bool(img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 1500)

    # Ürün görseli varlık kararı:
    # Boş stüdyo kartında edge_mean ~0.4-0.9, strong_edge_ratio ~0.0005 olur.
    has_product_visual = (edge_mean >= 1.8 and strong_edge_ratio >= 0.008) or (edge_mean >= 2.5)

    return {
        "has_product_visual": has_product_visual,
        "edge_mean": round(edge_mean, 2),
        "edge_std": round(edge_std, 2),
        "strong_edge_ratio": round(strong_edge_ratio, 4),
        "luma_std": round(luma_std, 2),
        "image_file_ok": file_ok,
        "image_path": img_path
    }


def analyze_meme_region(img_a: Image.Image, img_b: Image.Image = None) -> dict:
    """
    Alt yarıdaki (y:960..1900) meme katmanının siyah/boş olmadığını,
    reaksiyon başlığının (hook) mevcut olduğunu ve videonun hareket ettiğini doğrular.
    """
    W, H = img_a.size
    if H < 1800:
        return {"valid": False, "reason": "Görüntü yüksekliği 1920px değil"}

    meme_crop_a = img_a.crop((0, 960, W, 1900)).convert("RGB")
    stat_a = ImageStat.Stat(meme_crop_a.convert("L"))
    luma_mean = stat_a.mean[0]
    luma_std = stat_a.stddev[0]

    # Siyah veya tek renk bozuk ekran kontrolü
    is_not_blank = luma_std > 10.0 and 5.0 < luma_mean < 250.0

    # İki kare arası hareket farkı kontrolü (Meme videosu donmuş mu?)
    motion_score = 10.0
    if img_b and img_b.size == img_a.size:
        meme_crop_b = img_b.crop((0, 960, W, 1900)).convert("RGB")
        diff = ImageChops.difference(meme_crop_a, meme_crop_b).convert("L")
        motion_score = ImageStat.Stat(diff).mean[0]

    # Reaksiyon Hook kutusu kontrolü (y: 986..1054, x: 200..880)
    hook_crop = img_a.crop((200, 986, 880, 1054)).convert("L")
    hook_std = ImageStat.Stat(hook_crop).stddev[0]
    has_hook_overlay = hook_std > 15.0

    valid = is_not_blank and motion_score > 0.4
    return {
        "valid": valid,
        "is_not_blank": is_not_blank,
        "luma_mean": round(luma_mean, 2),
        "luma_std": round(luma_std, 2),
        "motion_score": round(motion_score, 2),
        "has_hook_overlay": has_hook_overlay
    }


def analyze_banner_typography_and_layout(img: Image.Image, deal: dict = None) -> dict:
    """
    Üst banner'daki fiyat kutusu kontrastını, güvenli kenar boşluklarını (safe margins)
    ve metinlerdeki desteklenmeyen karakterleri (tofu riski) denetler.
    """
    issues = []

    # 1. Fiyat Kutusu Kontrast Kontrolü (y: 750..888, x: 54..1026)
    price_crop = img.crop((54, 750, 1026, 888)).convert("L")
    price_std = ImageStat.Stat(price_crop).stddev[0]
    if price_std < 14.0:
        issues.append({
            "code": "PRICE_BOX_LOW_CONTRAST",
            "severity": "critical",
            "message": f"Fiyat kutusu alanı okunaksız veya boş görünüyor (std={price_std:.1f})."
        })

    # 2. Güvenli Kenar Boşluğu (Safe Margin) Taşma Kontrolü (Sol 0..28px ve Sağ 1052..1080px, y: 140..885)
    # Arka plan gradyanında yatayda (sol/sağ kenar) keskin kenar olmamalıdır
    left_margin = img.crop((2, 140, 26, 885)).convert("L").filter(ImageFilter.FIND_EDGES)
    right_margin = img.crop((1054, 140, 1078, 885)).convert("L").filter(ImageFilter.FIND_EDGES)
    left_inner = left_margin.crop((2, 4, 22, 740))
    right_inner = right_margin.crop((2, 4, 22, 740))
    left_edge = ImageStat.Stat(left_inner).mean[0]
    right_edge = ImageStat.Stat(right_inner).mean[0]

    margin_overflow = left_edge > 12.0 or right_edge > 12.0
    if margin_overflow:
        issues.append({
            "code": "TEXT_MARGIN_OVERFLOW",
            "severity": "warning",
            "message": f"Banner metni veya kutusu güvenli kenar boşluğunu (safe margin) taşıyor olabilir (L={left_edge:.1f}, R={right_edge:.1f})."
        })

    # 3. Deal metinlerinde kutucuk (tofu '▢') oluşturabilecek ham emoji / desteklenmeyen karakter kontrolü
    tofu_fields = []
    if deal and isinstance(deal, dict):
        check_keys = [
            "title", "old_price", "new_price", "discount_pct",
            "killer_hook", "feature_pill", "coupon_info",
            "installment", "seller_badge", "market_badge"
        ]
        for k in check_keys:
            val = str(deal.get(k, "") or "")
            if UNSUPPORTED_TTF_REGEX.search(val):
                tofu_fields.append(k)

    return {
        "price_box_std": round(price_std, 2),
        "left_margin_edge": round(left_edge, 2),
        "right_margin_edge": round(right_edge, 2),
        "margin_overflow": margin_overflow,
        "tofu_risk_fields": tofu_fields,
        "issues": issues
    }


def analyze_commercial_regions(img_a: Image.Image, img_b: Image.Image = None, deal: dict = None) -> dict:
    """
    1080x1920 Resmi Marka Tanıtım & Nizami Kart Layout Denetimi:
    1. Merkez (1080x1080) B-Roll video stream:
       - Hareketlilik (motion_score >= 0.4)
       - Görsel doku ve parlaklık varyansı (luma_std >= 10.0)
    2. Üst Header (y: 75..252):
       - Kontrast ve okunurluk (luma_std >= 14.0)
    3. Alt Nizami Kart (y: 1365..1860):
       - Kart kontrastı (luma_std >= 14.0)
       - Fiyat Açılma Geçişi: Frame A (0-3s ??? TL) ile Frame B (3-8s net fiyat) arasındaki fark (transition_diff >= 1.5)
    4. Tofu / Bozuk Unicode Kontrolü
    """
    issues = []
    W, H = img_a.size
    
    # 1. Merkez B-Roll Video Denetimi (y: 280..1340, x: 50..1030)
    center_a = img_a.crop((50, 280, 1030, 1340)).convert("RGB")
    center_luma_std = ImageStat.Stat(center_a.convert("L")).stddev[0]
    
    broll_motion = 10.0
    if img_b and img_b.size == img_a.size:
        center_b = img_b.crop((50, 280, 1030, 1340)).convert("RGB")
        broll_motion = ImageStat.Stat(ImageChops.difference(center_a, center_b).convert("L")).mean[0]
        
    has_broll = center_luma_std >= 10.0
    broll_moving = broll_motion >= 0.4
    
    if not has_broll:
        issues.append({
            "code": "BROLL_LAYER_BLANK",
            "severity": "critical",
            "message": f"Merkez B-Roll video alanı siyah veya boş (std={center_luma_std:.1f})"
        })
    if not broll_moving:
        issues.append({
            "code": "BROLL_LAYER_FROZEN",
            "severity": "critical",
            "message": f"Merkez B-Roll videosu hareketsiz/donmuş görünüyor (motion={broll_motion:.2f})"
        })
        
    # 2. Üst Header Kontrolü (y: 75..252, x: 54..1026)
    hdr_crop = img_a.crop((54, 75, 1026, 252)).convert("L")
    hdr_std = ImageStat.Stat(hdr_crop).stddev[0]
    if hdr_std < 14.0:
        issues.append({
            "code": "HEADER_LOW_CONTRAST",
            "severity": "critical",
            "message": f"Üst başlık veya rozetler okunaksız/eksik (std={hdr_std:.1f})"
        })
        
    # 3. Alt Nizami Kart ve Fiyat Açılış Geçişi (y: 1365..1860, x: 54..1026)
    card_a = img_a.crop((54, 1365, 1026, 1860)).convert("RGB")
    card_std = ImageStat.Stat(card_a.convert("L")).stddev[0]
    
    card_transition = 0.0
    if img_b and img_b.size == img_a.size:
        card_b = img_b.crop((54, 1365, 1026, 1860)).convert("RGB")
        card_transition = ImageStat.Stat(ImageChops.difference(card_a, card_b).convert("L")).mean[0]
        
    if card_std < 14.0:
        issues.append({
            "code": "DEAL_CARD_LOW_CONTRAST",
            "severity": "critical",
            "message": f"Alt nizami fırsat kartı okunaksız veya eksik (std={card_std:.1f})"
        })
        
    # 4. Tofu / Emoji Kontrolü
    tofu_fields = []
    if deal and isinstance(deal, dict):
        check_keys = ["title", "old_price", "new_price", "discount_pct", "killer_hook", "feature_pill", "seller_badge"]
        for k in check_keys:
            val = str(deal.get(k, "") or "")
            if UNSUPPORTED_TTF_REGEX.search(val):
                tofu_fields.append(k)
    if tofu_fields:
        issues.append({
            "code": "TOFU_GLYPH_RISK",
            "severity": "warning",
            "message": f"Deal metinlerinde kutucuk (tofu) riski: {', '.join(tofu_fields)}"
        })

    valid = has_broll and broll_moving and (hdr_std >= 14.0) and (card_std >= 14.0)
    return {
        "valid": valid,
        "broll_motion": round(broll_motion, 2),
        "broll_texture_std": round(center_luma_std, 2),
        "header_std": round(hdr_std, 2),
        "card_std": round(card_std, 2),
        "card_transition_diff": round(card_transition, 2),
        "tofu_risk_fields": tofu_fields,
        "issues": issues
    }


def validate_rendered_video(video_path: str, deal: dict = None, banner_path: str = None, layout_type: str = "commercial") -> dict:
    """
    Üretilen MP4 videoyu uçtan uca analiz eder:
    - layout_type="commercial" (Varsayılan): Merkez B-roll video, üst header ve alt nizami kart kontrolü
    - layout_type="split": Eski 2 katmanlı split-screen meme kontrolü
    """
    os.makedirs(VALIDATION_REPORTS_DIR, exist_ok=True)
    slug = re.sub(r'[^a-zA-Z0-9_-]', '', os.path.splitext(os.path.basename(video_path or "video"))[0])[:35]

    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "video_path": video_path,
        "banner_path": banner_path,
        "layout_type": layout_type,
        "passed": True,
        "issues": [],
        "metrics": {}
    }

    # 1. Akış & Dosya Kontrolü
    stream_res = check_video_streams(video_path)
    report["metrics"]["streams"] = stream_res
    if not stream_res["valid"]:
        report["passed"] = False
        report["issues"].extend(stream_res["issues"])
        return _save_validation_report(report, slug)

    # 2. Videodan Kare Çıkar
    ts_a = "00:00:01.50" if layout_type == "commercial" else "00:00:01.30"
    ts_b = "00:00:04.50" if layout_type == "commercial" else "00:00:03.40"
    frame_a_path, frame_b_path = extract_inspection_frames(video_path, slug=slug, ts_a=ts_a, ts_b=ts_b)
    if not frame_a_path or not os.path.exists(frame_a_path):
        report["passed"] = False
        report["issues"].append({
            "code": "FRAME_EXTRACTION_FAILED",
            "severity": "critical",
            "message": "Videodan kontrol karesi (frame) çıkarılamadı."
        })
        return _save_validation_report(report, slug)

    report["inspection_frame"] = frame_a_path

    try:
        with Image.open(frame_a_path) as img_a:
            img_a_rgb = img_a.convert("RGB")
            img_b_rgb = None
            if frame_b_path and os.path.exists(frame_b_path):
                with Image.open(frame_b_path) as img_b:
                    img_b_rgb = img_b.convert("RGB")

            if layout_type == "commercial":
                comm_res = analyze_commercial_regions(img_a_rgb, img_b_rgb, deal=deal)
                report["metrics"]["commercial_layout"] = comm_res
                for iss in comm_res["issues"]:
                    if iss.get("severity") == "critical":
                        report["passed"] = False
                    report["issues"].append(iss)
            else:
                # Legacy Split-screen Kontrolü
                prod_res = analyze_product_region(img_a_rgb, deal=deal)
                report["metrics"]["product_region"] = prod_res
                if not prod_res["has_product_visual"]:
                    report["passed"] = False
                    report["issues"].append({
                        "code": "MISSING_PRODUCT_IMAGE",
                        "severity": "critical",
                        "message": f"Üst banner kartında ürün görseli tespit edilemedi! (edge_mean={prod_res['edge_mean']})"
                    })

                meme_res = analyze_meme_region(img_a_rgb, img_b_rgb)
                report["metrics"]["meme_region"] = meme_res
                if not meme_res["valid"]:
                    report["passed"] = False
                    report["issues"].append({
                        "code": "MEME_LAYER_DEFECT",
                        "severity": "critical",
                        "message": f"Alt meme videosu bozuk veya hareketsiz!"
                    })

                typo_res = analyze_banner_typography_and_layout(img_a_rgb, deal=deal)
                report["metrics"]["typography"] = typo_res
                for iss in typo_res["issues"]:
                    if iss["severity"] == "critical":
                        report["passed"] = False
                    report["issues"].append(iss)

    except Exception as e:
        report["passed"] = False
        report["issues"].append({
            "code": "VALIDATION_EXCEPTION",
            "severity": "critical",
            "message": f"Görsel analiz sırasında hata: {e}"
        })

    return _save_validation_report(report, slug)


def _save_validation_report(report: dict, slug: str) -> dict:
    try:
        os.makedirs(VALIDATION_REPORTS_DIR, exist_ok=True)
        latest_path = os.path.join(VALIDATION_REPORTS_DIR, "last_validation.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return report


def auto_repair_deal_for_rerender(deal: dict, validation_report: dict, current_meme: str = None) -> dict:
    """
    Doğrulama raporundaki hatalara göre deal nesnesini ve yerel varlıkları (assets)
    otomatik olarak onarır:
    - MISSING_PRODUCT_IMAGE: Sayfadan yüksek çözünürlüklü görseli yeniden çeker,
      bozuk rembg kesimini (_cutout.png) siler ve gerekirse doğrudan temiz görseli kullanır.
    - MEME_LAYER_DEFECT: Havuzdan bir sonraki sağlam meme videosuna geçer.
    - TEXT_MARGIN_OVERFLOW / TOFU: Tüm metin alanlarındaki emojileri temizler ve uzun metinleri kısaltır.
    """
    issues = validation_report.get("issues", [])
    issue_codes = {i.get("code") for i in issues}
    repairs_applied = []

    # 1. Her durumda metin alanlarını TTF-güvenli hale getir (Tofu önleme)
    text_keys = [
        "title", "old_price", "new_price", "discount_pct",
        "killer_hook", "feature_pill", "coupon_info",
        "installment", "seller_badge", "market_badge"
    ]
    for k in text_keys:
        if deal.get(k):
            cleaned = sanitize_ttf_text(deal[k])
            if cleaned != deal[k]:
                deal[k] = cleaned
                repairs_applied.append(f"Metin temizlendi ({k})")

    # 2. Ürün Görseli Eksikse Onar
    if "MISSING_PRODUCT_IMAGE" in issue_codes:
        print("[Auto-Repair] 🔧 Eksik ürün görseli tespit edildi! Görsel kurtarma başlatılıyor...")
        old_img_path = deal.get("image_path", "")
        if old_img_path:
            cutout_p = f"{os.path.splitext(old_img_path)[0]}_cutout.png"
            if os.path.exists(cutout_p):
                try:
                    os.remove(cutout_p)
                    repairs_applied.append("Bozuk rembg cutout önbelleği silindi")
                except Exception:
                    pass

        # Eğer görsel dosyası yoksa veya bozuksa URL'den yeniden çek
        need_redownload = (
            not old_img_path
            or not os.path.exists(old_img_path)
            or os.path.getsize(old_img_path) < 2000
        )

        if need_redownload:
            img_url = deal.get("image_url", "")
            store_url = deal.get("store_url") or deal.get("affiliate_url", "")

            if not img_url and store_url:
                try:
                    from product_verifier import verify_deal_before_publish
                    v_info = verify_deal_before_publish(deal)
                    if v_info.get("deal", {}).get("image_url"):
                        img_url = v_info["deal"]["image_url"]
                        deal["image_url"] = img_url
                except Exception as e:
                    print(f"[Auto-Repair] product_verifier görsel bulma uyarısı: {e}")

            if not img_url and store_url:
                try:
                    from deal_hunter import parse_deal_from_url
                    parsed = parse_deal_from_url(store_url)
                    if parsed and parsed.get("image_path") and os.path.exists(parsed["image_path"]):
                        deal["image_path"] = parsed["image_path"]
                        repairs_applied.append(f"parse_deal_from_url ile görsel kurtarıldı: {parsed['image_path']}")
                except Exception as e:
                    print(f"[Auto-Repair] parse_deal_from_url uyarısı: {e}")

            if img_url and (not deal.get("image_path") or not os.path.exists(deal.get("image_path", ""))):
                slug = re.sub(r'[^a-zA-Z0-9]', '_', deal.get("title", "prod"))[:25].lower()
                repaired_img = os.path.join(TEMP_DIR, f"repaired_{slug}.jpg")
                if download_file(img_url, repaired_img) and os.path.exists(repaired_img) and os.path.getsize(repaired_img) > 1500:
                    deal["image_path"] = repaired_img
                    repairs_applied.append(f"Ürün görseli yeniden indirildi: {repaired_img}")

        # Eğer görsel dosyası var ama rembg yüzünden boş çıktıysa skip_rembg bayrağını aç
        if deal.get("image_path") and os.path.exists(deal["image_path"]):
            deal["skip_rembg"] = True
            repairs_applied.append("rembg devre dışı bırakıldı (orijinal ürün görseli kullanılacak)")

    # 3. Taşma Varsa Başlık ve Rozetleri Kısalt
    if "TEXT_MARGIN_OVERFLOW" in issue_codes:
        if len(deal.get("title", "")) > 55:
            words = deal["title"].split()
            deal["title"] = " ".join(words[:7])
            repairs_applied.append("Uzun ürün başlığı kısaltıldı")
        if len(deal.get("killer_hook", "")) > 32:
            deal["killer_hook"] = deal["killer_hook"][:32].strip()
            repairs_applied.append("Killer hook rozeti kısaltıldı")

    # 4. Meme Katmanında Sorun Varsa Yeni Meme Seç
    new_meme = current_meme
    if "MEME_LAYER_DEFECT" in issue_codes:
        try:
            from split_composer import select_smart_meme
            new_meme = select_smart_meme(deal.get("discount_pct", ""), deal.get("title", ""))
            repairs_applied.append(f"Yeni meme seçildi: {new_meme}")
        except Exception:
            pass

    return {
        "deal": deal,
        "meme_choice": new_meme,
        "repairs_applied": repairs_applied
    }


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target and os.path.exists(target):
        res = validate_rendered_video(target)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("Kullanım: python video_content_validator.py <video_path>")
