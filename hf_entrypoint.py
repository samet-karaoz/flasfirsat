import os
import sys
import time
import threading
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Flas Firsat 24/7 Cloud Bot")

START_TIME = datetime.now()
LAST_DM_TIME = "Henüz çalışmadı"
BOT_STATUS = "Başlatılıyor..."

@app.get("/", response_class=HTMLResponse)
def index():
    uptime = str(datetime.now() - START_TIME).split(".")[0]
    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>⚡ Flaş Fırsat - 7/24 Bulut Botu</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f172a;
                color: #f8fafc;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 32px;
                max-width: 480px;
                width: 90%;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                text-align: center;
            }}
            .badge {{
                display: inline-block;
                background: #10b981;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 9999px;
                font-size: 14px;
                margin-bottom: 16px;
            }}
            h1 {{ margin: 0 0 8px; font-size: 24px; color: #38bdf8; }}
            p {{ color: #94a3b8; font-size: 15px; margin: 6px 0; }}
            .stats {{
                background: #0f172a;
                border-radius: 10px;
                padding: 16px;
                margin: 20px 0;
                text-align: left;
                font-size: 14px;
            }}
            .stats-item {{
                display: flex;
                justify-content: space-between;
                padding: 6px 0;
                border-bottom: 1px solid #1e293b;
            }}
            .stats-item:last-child {{ border-bottom: none; }}
            .val {{ color: #38bdf8; font-weight: bold; }}
            .btn {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-top: 10px;
            }}
            .btn:hover {{ background: #1d4ed8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">● 7/24 KESİNTİSİZ AKTİF</div>
            <h1>⚡ Flaş Fırsat Bulut Botu</h1>
            <p>Hugging Face Spaces üzerinde 2 vCPU & 16GB RAM ile çalışıyor.</p>
            
            <div class="stats">
                <div class="stats-item">
                    <span>Durum:</span>
                    <span class="val">Çalışıyor (Online)</span>
                </div>
                <div class="stats-item">
                    <span>Çalışma Süresi:</span>
                    <span class="val">{uptime}</span>
                </div>
                <div class="stats-item">
                    <span>Auto-DM Radarı:</span>
                    <span class="val">Her 2 Dakikada Bir</span>
                </div>
                <div class="stats-item">
                    <span>Telegram Servisi:</span>
                    <span class="val">Aktif (@flasfirsat)</span>
                </div>
                <div class="stats-item">
                    <span>Otopilot Kuşakları:</span>
                    <span class="val">12:30 & 20:00</span>
                </div>
            </div>

            <p style="font-size: 12px; color: #64748b;">Bilgisayarınız kapalı olsa dahi sistem arka planda 7/24 çalışmaya devam eder.</p>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": (datetime.now() - START_TIME).total_seconds()}

def start_bot_service():
    """telegram_bot_service arka plan servisini başlatır."""
    try:
        from telegram_bot_service import run_telegram_service
        run_telegram_service()
    except Exception as e:
        print(f"[HF Entrypoint] Bot servisi hatası: {e}")

if __name__ == "__main__":
    # 1. Bot servisini arka plan iş parçacığında başlat
    bot_thread = threading.Thread(target=start_bot_service, daemon=True)
    bot_thread.start()

    # 2. Hugging Face Spaces portunu dinle (varsayılan 7860)
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF Entrypoint] Web dashboard başlatılıyor (Port {port})...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
