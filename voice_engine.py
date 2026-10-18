import os
import json
import base64
import subprocess
from config import BASE_DIR, TEMP_DIR, GEMINI_API_KEY, safe_run_subprocess

def generate_gemini_voice(text: str, output_filename: str = "gemini_voice.wav", style: str = "calm, deep, natural fluent pacing, conversational, stoic male voice") -> tuple:
    """
    Google Gemini 3.8 Flash TTS kullanarak doğal, akıcı ve karizmatik bir ses üretir.
    FFmpeg atempo filtresi ile konuşmayı hızlandırır, tane tane duraksamaları ortadan kaldırır.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    raw_wav_path = os.path.join(TEMP_DIR, "raw_" + output_filename)
    out_wav_path = os.path.join(TEMP_DIR, output_filename)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/interactions?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "model": "gemini-3.8-flash-tts",
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}]
            }]
        }],
        "response_format": {"type": "audio", "mime_type": "audio/wav"},
        "generation_config": {"speech_config": [{"voice": "Puck"}]}
    })

    cmd = ["curl.exe", "-4", "--ssl-no-revoke", "-s", "-H", "Content-Type: application/json", "-X", "POST", "-d", payload, url]
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    data = json.loads(res.stdout)

    audio_bytes = None
    for step in data.get("steps", []):
        for c in step.get("content", []):
            if c.get("type") == "audio":
                audio_bytes = base64.b64decode(c["data"])
                break

    if not audio_bytes:
        raise RuntimeError(f"Gemini TTS ses üretemedi: {data}")

    with open(raw_wav_path, "wb") as f:
        f.write(audio_bytes)

    # %20 daha hızlı, akıcı ve ritmik hale getir (ses tonunu/kalınlığını bozmadan)
    speed_factor = 1.20
    safe_run_subprocess([
        "ffmpeg", "-y", "-i", raw_wav_path,
        "-filter:a", f"atempo={speed_factor}",
        out_wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Sesin süresini Python wave modülü ile hesapla
    import wave
    with wave.open(out_wav_path, "rb") as wf:
        total_duration = wf.getnframes() / float(wf.getframerate())

    # Cümleleri ve kelime öbeklerini zamanla
    words = text.split()
    # 2-3 kelimelik öbekler
    chunk_size = 2
    chunks = [words[k:k+chunk_size] for k in range(0, len(words), chunk_size)]
    
    phrases = []
    chunk_dur = total_duration / max(len(chunks), 1)
    for idx, c in enumerate(chunks):
        phrases.append({
            "text": " ".join(c),
            "start": round(idx * chunk_dur, 2),
            "end": round((idx + 1) * chunk_dur, 2)
        })

    return out_wav_path, phrases, round(total_duration, 2)

if __name__ == "__main__":
    t = "Vazgeçmek en kolay seçenektir. Başarılı olmak ise herkesi susturur."
    p, ph, d = generate_gemini_voice(t)
    print("Voice path:", p)
    print("Duration:", d)
    print("Phrases:", ph)
