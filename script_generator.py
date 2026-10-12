import os
import json
import subprocess
from config import GEMINI_API_KEY

def generate_script(topic: str = None) -> dict:
    """
    Gemini 3.8 Flash kullanarak referans videodaki gibi kısa, derin,
    felsefi ve vurucu bir motivasyon sözü üretir (yaklaşık 15-20 kelime).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_prompt = """Sen kısa, derin, felsefi ve sinematik motivasyon videoları için sözler yazan bir bilgesin.
Referans tarz: 
'Vazgeçmek en kolay seçenektir. Tüm bu sesleri susturmanın tek yolu ise başarılı olmaktır.'

Kurallar:
- Cümle asla uzun olmamalı (maksimum 15-20 kelime).
- Edebi, sakin, vakur ve derin olmalı.
- Son cümle vurucu ve akılda kalıcı olmalı (çünkü siyah bitiş kartında tek başına görünecek).
- JSON formatında yanıt ver:
{
  "title": "Kısa başlık",
  "text": "Tek parça, akıcı metin",
  "search_query": "İngilizce 2-3 kelimelik Pexels dikey video arama terimi, örn: sunset ocean silhouette"
}
Sadece JSON döndür."""

    user_query = f"Konu: {topic if topic else 'Sessizce çalışmak, vazgeçmemek ve başarılı olmak'}"
    
    payload = json.dumps({
        "contents": [{"parts": [{"text": user_query}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"response_mime_type": "application/json"}
    })

    cmd = ["curl.exe", "-4", "--ssl-no-revoke", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", payload, url]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    try:
        data = json.loads(res.stdout)
        content_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(content_text)
    except Exception as e:
        print("[Script] API parse hatası:", e)
        return {
            "title": "Sessiz Zafer",
            "text": "Vazgeçmek en kolay seçenektir. Bütün bu sesleri susturmanın bilinen en etkili yolu ise, başarılı olmaktır.",
            "search_query": "sunset calm sea silhouette"
        }

if __name__ == "__main__":
    s = generate_script()
    print("Script output:", s)
