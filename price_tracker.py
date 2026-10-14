import os
import sqlite3
from datetime import datetime, timedelta
from config import BASE_DIR

DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "price_history.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                store TEXT NOT NULL,
                title TEXT,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prod_store ON price_records(product_id, store)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON price_records(created_at)
        """)
    conn.close()

def record_price(product_id: str, store: str, title: str, price: float):
    """Her taramada tespit edilen ürün fiyatını zaman damgasıyla kaydeder."""
    if not product_id or price <= 0:
        return
    init_db()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO price_records (product_id, store, title, price, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(product_id).strip().upper(), store, title, float(price), datetime.now())
            )
    finally:
        conn.close()

def check_if_lowest_30d(product_id: str, current_price: float, store: str = "Amazon TR") -> dict:
    """
    Ürünün veritabanımızdaki son 30 günlük fiyat geçmişini kontrol eder.
    Mevzuata uygunluk: Sadece GERÇEKTEN son 30 günde kaydedilmiş veri varsa
    ve mevcut fiyat en düşükse 'is_lowest': True döner.
    """
    if not product_id or current_price <= 0:
        return {"is_lowest": False, "history_count": 0, "lowest_seen": current_price}
        
    init_db()
    conn = get_connection()
    try:
        since_date = datetime.now() - timedelta(days=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT price, created_at 
            FROM price_records 
            WHERE product_id = ? AND store = ? AND created_at >= ?
            ORDER BY price ASC
            """,
            (str(product_id).strip().upper(), store, since_date)
        )
        rows = cursor.fetchall()
        if not rows:
            return {"is_lowest": False, "history_count": 0, "lowest_seen": current_price}

        prices = [r["price"] for r in rows]
        min_price = min(prices)
        
        # Eğer mevcut fiyat geçmişteki en düşük fiyata eşit veya daha ucuzsa
        is_lowest = (current_price <= min_price) and len(prices) >= 2
        return {
            "is_lowest": is_lowest,
            "history_count": len(prices),
            "lowest_seen": min_price,
            "highest_seen": max(prices)
        }
    finally:
        conn.close()

def get_real_previous_price(product_id: str, store: str = "Amazon TR") -> float:
    """
    Ürünün indirimden önceki gerçek fiyatını (varsa) veritabanından döndürür.
    Böylece tahmini liste fiyatı yerine gerçek önceki fiyat kullanılabilir.
    """
    if not product_id:
        return 0.0
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT price 
            FROM price_records 
            WHERE product_id = ? AND store = ?
            ORDER BY created_at DESC 
            LIMIT 5
            """,
            (str(product_id).strip().upper(), store)
        )
        rows = cursor.fetchall()
        if rows and len(rows) > 1:
            prices = [r["price"] for r in rows]
            return max(prices)
        return 0.0
    finally:
        conn.close()

init_db()
