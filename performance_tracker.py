import os
import sqlite3
import re
from datetime import datetime
from config import BASE_DIR

DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "performance.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_performance_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS published_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                store TEXT NOT NULL,
                category TEXT,
                discount_pct INTEGER,
                meme_used TEXT,
                audio_used TEXT,
                video_file TEXT,
                views INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                sales INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perf_meme ON published_deals(meme_used)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perf_cat ON published_deals(category)")
    conn.close()

def log_published_deal(deal: dict, meme: str = "", audio: str = "", video_path: str = "") -> int:
    """Yayınlanan bir fırsat videosunu ve kullanılan meme/müziği veritabanına kaydeder."""
    init_performance_db()
    conn = get_connection()
    try:
        pct_m = re.search(r"(\d+)", str(deal.get("discount_pct", "")))
        pct_val = int(pct_m.group(1)) if pct_m else 0
        from deal_hunter import get_product_subtype
        cat = get_product_subtype(deal.get("title", ""))

        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO published_deals 
                (title, store, category, discount_pct, meme_used, audio_used, video_file, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal.get("title", "Bilinmeyen Fırsat"),
                deal.get("store_name", "Amazon TR"),
                cat,
                pct_val,
                meme or "",
                audio or "",
                os.path.basename(video_path) if video_path else "",
                datetime.now()
            ))
            return cur.lastrowid
    except Exception as e:
        print(f"[Performance] Kayıt uyarısı: {e}")
        return 0
    finally:
        conn.close()

def update_deal_metrics(deal_id_or_title, views: int = 0, clicks: int = 0, sales: int = 0):
    """Fırsatın görüntülenme, tıklama veya satış geri bildirimini günceller."""
    init_performance_db()
    conn = get_connection()
    try:
        with conn:
            if isinstance(deal_id_or_title, int):
                conn.execute("""
                    UPDATE published_deals 
                    SET views = views + ?, clicks = clicks + ?, sales = sales + ?
                    WHERE id = ?
                """, (views, clicks, sales, deal_id_or_title))
            else:
                conn.execute("""
                    UPDATE published_deals 
                    SET views = views + ?, clicks = clicks + ?, sales = sales + ?
                    WHERE title LIKE ?
                """, (views, clicks, sales, f"%{deal_id_or_title}%"))
    finally:
        conn.close()

def get_performance_insights() -> dict:
    """
    En çok izlenen ve tıklanan meme, kategori ve indirim oranlarını analiz eder.
    Puanlama motoruna geri bildirim sağlar.
    """
    init_performance_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        # En iyi meme'ler
        cur.execute("""
            SELECT meme_used, COUNT(*) as count, SUM(views) as total_views, SUM(clicks) as total_clicks
            FROM published_deals
            WHERE meme_used != ''
            GROUP BY meme_used
            ORDER BY (total_clicks * 3 + total_views) DESC
            LIMIT 5
        """)
        top_memes = [dict(r) for r in cur.fetchall()]

        # En çok satan kategoriler
        cur.execute("""
            SELECT category, COUNT(*) as count, SUM(clicks) as total_clicks, SUM(sales) as total_sales
            FROM published_deals
            GROUP BY category
            ORDER BY (total_sales * 5 + total_clicks) DESC
            LIMIT 5
        """)
        top_cats = [dict(r) for r in cur.fetchall()]

        return {
            "top_memes": top_memes,
            "top_categories": top_cats
        }
    finally:
        conn.close()

if __name__ == "__main__":
    init_performance_db()
    insights = get_performance_insights()
    print("--- PERFORMANS İÇGÖRÜLERİ ---")
    print(insights)
