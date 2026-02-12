import os
import telebot
import yt_dlp
import subprocess
import uuid
import signal
import sys
import json
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Kirim /yt + link\nSaya akan:\n- Cari momen viral\n- Potong 60 detik\n- Tambah subtitle\n- Kirim clip")


@bot.message_handler(commands=['yt'])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Contoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "⬇️ Downloading video & transcript...")

    unique_id = str(uuid.uuid4())
    raw_file = f"{unique_id}.mp4"
    clip_file = f"clip_{unique_id}.mp4"
    final_file = f"final_{unique_id}.mp4"

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": raw_file,
        "noplaylist": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["id", "en"],
        "skip_download": False
    }

    try:
        # DOWNLOAD VIDEO + SUBTITLE
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        duration = info.get("duration", 0)

        # CARI FILE SRT
        transcript_text = ""
        for file in os.listdir():
            if file.endswith(".vtt"):
                with open(file, "r", encoding="utf-8") as f:
                    transcript_text = f.read()
                break

        if not transcript_text:
            bot.reply_to(message, "❌ Subtitle tidak tersedia di YouTube.")
            return

        bot.reply_to(message, "🧠 AI mencari momen paling viral...")

        prompt = f"""
Berikut transcript video YouTube.

Tugas:
1. Tentukan timestamp paling viral dan emosional.
2. Berikan jawaban dalam format JSON:
{{ "start": detik_mulai }}

Transcript:
{transcript_text[:8000]}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.choices[0].message.content.strip()

        # Ambil angka dari JSON
        start_time = json.loads(result)["start"]

        # Pastikan tidak lebih dari durasi
        if start_time + 60 > duration:
            start_time = max(0, duration - 60)

        bot.reply_to(message, f"✂️ Memotong 60 detik dari detik {start_time}...")

        # POTONG VIDEO
        subprocess.run([
            "ffmpeg",
            "-ss", str(start_time),
            "-i", raw_file,
            "-t", "60",
            "-vf", "scale=1280:-2",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "aac",
            clip_file
        ])

        bot.reply_to(message, "📝 Generate subtitle...")

        # GENERATE SRT DENGAN WHISPER
        subprocess.run([
            "whisper",
            clip_file,
            "--model", "tiny",
            "--language", "Indonesian",
            "--output_format", "srt"
        ])

        srt_file = clip_file.replace(".mp4", ".srt")

        bot.reply_to(message, "🎬 Menempelkan subtitle...")

        subprocess.run([
            "ffmpeg",
            "-i", clip_file,
            "-vf", f"subtitles={srt_file}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "copy",
            final_file
        ])

        bot.reply_to(message, "📤 Mengirim clip...")

        with open(final_file, "rb") as video:
            bot.send_video(message.chat.id, video)

        # CLEAN UP
        for file in os.listdir():
            if unique_id in file:
                os.remove(file)

    except Exception as e:
        bot.reply_to(message, f"❌ ERROR: {e}")


def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
