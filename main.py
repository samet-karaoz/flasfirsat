import os
import sys
import time
from config import BASE_DIR, OUTPUT_DIR, ASSETS_DIR, MUSIC_DIR
from script_generator import generate_script
from voice_engine import generate_gemini_voice
from media_manager import get_cinematic_clips
from video_composer import compose_video, make_warm_pad

def create_cinematic_video(custom_topic: str = None) -> str:
    print("\n" + "="*55)
    print("🎬 SİNEMATİK MOTİVASYON VİDEOSU ÜRETİLİYOR")
    print("="*55)

    # 1. Gemini ile Felsefi & Vurucu Senaryo
    print("\n[1/4] ✍️ Senaryo üretiliyor (Gemini 3.8 Flash)...")
    script = generate_script(custom_topic)
    title = script.get("title", "Motivasyon")
    text = script.get("text", "")
    query = script.get("search_query", "sunset ocean silhouette")
    print(f"📌 Başlık: {title}")
    print(f"📖 Metin: \"{text}\"")

    # 2. Gemini 3.8 Flash TTS ile Gerçekçi & Derin Seslendirme
    print("\n[2/4] 🎙️ Seslendirme üretiliyor (Gemini 3.8 Flash TTS)...")
    voice_path, phrases, duration = generate_gemini_voice(text, "cinematic_voice.wav")
    print(f"⏱️ Ses Süresi: {duration} saniye")
    print(f"💬 Cümle Öbekleri: {len(phrases)} adet")

    # 3. Pexels API ile Gerçek Sinematik Dikey Videolar (B-Roll)
    print("\n[3/4] 🎥 Sinematik dikey videolar indiriliyor (Pexels)...")
    clip_count = max(2, min(4, int(duration / 3)))
    clips = get_cinematic_clips(query, count=clip_count)
    print(f"✅ Toplam {len(clips)} adet yüksek kaliteli klip hazırlandı.")

    # 4. Arka Plan Müziği ve Sinematik Montaj (Rounded Card + Serif)
    print("\n[4/4] 🎞️ Sinematik kart montajı ve serif altyazılar işleniyor...")
    bg_music = os.path.join(MUSIC_DIR, "warm_pad.mp3")
    if not os.path.exists(bg_music):
        make_warm_pad(bg_music)

    timestamp_str = int(time.time())
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    output_filename = f"{safe_title}_{timestamp_str}.mp4"

    final_video = compose_video(
        clips=clips,
        voice_path=voice_path,
        phrases=phrases,
        voice_duration=duration,
        output_filename=output_filename,
        music_path=bg_music
    )

    print("\n" + "="*55)
    print("🎉 VİDEO BAŞARIYLA ÜRETİLDİ!")
    print(f"📁 Dosya: {final_video}")
    print("="*55 + "\n")
    return final_video

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    create_cinematic_video(topic)
