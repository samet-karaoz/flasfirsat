"""
Sinematik motivasyon videosu montajı.

Referans tarz: siyah 9:16 çerçeve içinde yuvarlak köşeli video kartı, sıcak renk,
ince serif font, kelime kelime beliren asimetrik altyazı, siyah bitiş kartı.
"""
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw

from config import (
    ASSETS_DIR,
    BASE_DIR,
    FPS,
    OUTPUT_DIR,
    TEMP_DIR,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    WATERMARK_TEXT,
    safe_run_subprocess,
)

CARD_W, CARD_H = 960, 1080
CARD_X = (VIDEO_WIDTH - CARD_W) // 2
CARD_Y = (VIDEO_HEIGHT - CARD_H) // 2
CARD_RADIUS = 56
END_CARD_SECONDS = 2.4
FONT_NAME = "DM Serif Display"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")


def tr_lower(text: str) -> str:
    """Türkçe'ye uygun küçük harf (I -> ı, İ -> i)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def _ass_time(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(phrases: list, card_end: float, total: float, path: str) -> str:
    """
    phrases: [{"text": "vazgeçmek en", "start": 0.4, "end": 1.6}, ...]
    Her kelime kendi boyutu ve kaydırılmış konumuyla sırayla belirir.
    Son cümle siyah bitiş kartında büyük ve ortalı gösterilir.
    """
    rng = random.Random(7)
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {VIDEO_WIDTH}\nPlayResY: {VIDEO_HEIGHT}\nWrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Main,{FONT_NAME},80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,0,4,5,0,0,0,1\n"
        f"Style: Mark,{FONT_NAME},26,&HB0FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,12,0,1,0,0,5,0,0,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    last_index = len(phrases) - 1
    for idx, ph in enumerate(phrases):
        words = tr_lower(ph["text"]).split()
        if not words:
            continue
        start, end = ph["start"], ph["end"]
        is_end_card = (idx == last_index)
        if is_end_card:
            # Siyah bitiş kartı: kart kapandıktan sonra ortalı büyük yazı.
            show_start = card_end - 0.2
            text = r"\N".join(
                [" ".join(words[i:i + 2]) for i in range(0, len(words), 2)]
            )
            lines.append(
                f"Dialogue: 1,{_ass_time(show_start)},{_ass_time(total)},Main,,0,0,0,,"
                f"{{\\an5\\pos({VIDEO_WIDTH // 2},{VIDEO_HEIGHT // 2 - 40})\\fs104\\fad(350,0)}}{text}"
            )
            continue
        span = max(end - start, 0.3)
        step = span / len(words)
        base_y = CARD_Y + CARD_H * 0.42 + rng.randint(-60, 60)
        for w_i, word in enumerate(words):
            big = w_i % 2 == 0
            size = 92 if big else 62
            x = VIDEO_WIDTH // 2 + rng.randint(-170, 170)
            y = int(base_y + w_i * 112)
            w_start = start + w_i * step
            lines.append(
                f"Dialogue: 1,{_ass_time(w_start)},{_ass_time(end + 0.15)},Main,,0,0,0,,"
                f"{{\\an5\\pos({x},{y})\\fs{size}\\fad(160,120)}}{word}"
            )
    # Küçük filigran (kartın altında)
    lines.append(
        f"Dialogue: 0,{_ass_time(0)},{_ass_time(card_end)},Mark,,0,0,0,,"
        f"{{\\an5\\pos({VIDEO_WIDTH // 2},{CARD_Y + CARD_H - 44})}}{WATERMARK_TEXT}"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
    return path


def _rounded_mask(path: str) -> str:
    mask = Image.new("L", (CARD_W, CARD_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, CARD_W - 1, CARD_H - 1), radius=CARD_RADIUS, fill=255
    )
    mask.save(path)
    return path


def _run(cmd: list, label: str) -> None:
    res = safe_run_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=BASE_DIR)
    if res.returncode != 0:
        raise RuntimeError(f"[{label}] ffmpeg hatası:\n{res.stderr[-1500:]}")


def make_warm_pad(path: str, seconds: int = 60) -> str:
    """Anahtarsız yedek: yumuşak, sıcak ambient pad üretir (gerçek müzik varsa onu kullan)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    freqs = [110.0, 164.81, 220.0, 277.18]
    inputs, labels = [], []
    for i, f in enumerate(freqs):
        inputs += ["-f", "lavfi", "-i", f"sine=f={f}:d={seconds}"]
        labels.append(f"[{i}:a]")
    graph = (
        "".join(labels)
        + f"amix=inputs={len(freqs)}:normalize=0,volume=0.22,"
        "tremolo=f=0.12:d=0.45,lowpass=f=900,aecho=0.8:0.88:900|1700:0.35|0.25,"
        f"afade=t=in:d=3,afade=t=out:st={seconds - 4}:d=4"
    )
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", graph, "-c:a", "libmp3lame", "-q:a", "4", path], "pad")
    return path


def compose_video(
    clips: list,
    voice_path: str,
    phrases: list,
    voice_duration: float,
    output_filename: str = "reel.mp4",
    music_path: str = None,
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    if not clips:
        raise ValueError("Klip listesi boş: gerçek B-Roll olmadan video üretilmez.")

    card_end = voice_duration + 0.6
    total = card_end + END_CARD_SECONDS
    seg = card_end / len(clips)

    # 1) Klipleri kart boyutuna kırp, sıcak renk ver, kes ve birleştir.
    grade = "eq=saturation=1.12:contrast=1.06:brightness=-0.02,colorbalance=rs=0.04:bs=-0.04"
    prepared = []
    for i, clip in enumerate(clips):
        out = os.path.join(TEMP_DIR, f"card_{i}.mp4")
        _run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", clip, "-t", f"{seg + 0.05:.3f}",
            "-vf", f"scale={CARD_W}:{CARD_H}:force_original_aspect_ratio=increase,crop={CARD_W}:{CARD_H},{grade},fps={FPS}",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out,
        ], f"clip{i}")
        prepared.append(out)
    list_file = os.path.join(TEMP_DIR, "cards.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in prepared:
            f.write(f"file '{p.replace(chr(92), '/')}'\n")
    card_video = os.path.join(TEMP_DIR, "card_all.mp4")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", card_video], "concat")

    # 2) Altyazı ve maske
    ass_rel = os.path.join("temp", "subs.ass")
    build_ass(phrases, card_end, total, os.path.join(BASE_DIR, ass_rel))
    mask_rel = os.path.join("temp", "mask.png")
    _rounded_mask(os.path.join(BASE_DIR, mask_rel))

    # 3) Final render
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={FPS}:d={total:.3f}",
        "-i", card_video,
        "-loop", "1", "-framerate", str(FPS), "-i", mask_rel,
        "-i", voice_path,
    ]
    if music_path:
        cmd += ["-stream_loop", "-1", "-i", music_path]
        audio = (
            f"[3:a]apad=whole_dur={total:.3f}[vo];"
            f"[4:a]volume=0.16,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5[m];"
            "[vo][m]amix=inputs=2:duration=first:normalize=0[a]"
        )
    else:
        audio = f"[3:a]apad=whole_dur={total:.3f}[a]"
    video = (
        "[1:v]format=yuva420p[c0];[2:v]format=gray[m0];[c0][m0]alphamerge[card];"
        f"[0:v][card]overlay={CARD_X}:{CARD_Y}:enable='between(t,0,{card_end:.2f})':eof_action=pass[bg];"
        f"[bg]ass=temp/subs.ass:fontsdir=assets/fonts,format=yuv420p[v]"
    )
    cmd += [
        "-filter_complex", f"{video};{audio}",
        "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    _run(cmd, "render")
    return output_path
