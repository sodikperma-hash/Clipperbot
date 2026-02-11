import os
import telebot
from openai import OpenAI
import yt_dlp
import subprocess
import signal
import sys
import json
import math

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ===========================
# BASIC COMMANDS
# ===========================

@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "🎬 Kirim:\n/yt LINK_YOUTUBE\nSaya akan buat short otomatis dengan subtitle 🔥")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Gunakan:\n/yt https://youtube.com/xxxxx")

# ===========================
# MAIN AI SHORTS FUNCTION
# ===========================

@bot.message_handler(commands=['yt'])
def handle_yt(message):
    chat_id = message.chat.id
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Masukkan link YouTube.\nContoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "📥 Downloading video...")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "video.mp4",
        "noplaylist": True
    }

    try:
        # DOWNLOAD VIDEO
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # EXTRACT AUDIO
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "video.mp4",
            "-vn",
            "-acodec", "mp3",
            "audio.mp3"
        ])

        bot.reply_to(message, "🧠 Menganalisa audio dengan AI...")

        # TRANSCRIBE WITH WHISPER
        audio_file = open("audio.mp3", "rb")
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json"
        )

        full_text = transcript.text

        # AI PILIH BAGIAN TERBAIK
        prompt = f"""
Dari transcript berikut, pilih 1 bagian paling viral untuk konten short.

Kriteria:
- Emosional
- Bisa jadi hook kuat
- Maksimal 45 detik

Jawab format JSON:
{{
"start": detik,
"end": detik,
"hook": "judul pendek"
}}

Transcript:
{full_text}
"""

        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        result = json.loads(ai_response.choices[0].message.content)

        start_time = str(result["start"])
        end_time = str(result["end"])
        hook_text = result["hook"]

        bot.reply_to(message, f"✂ Memotong bagian terbaik...\nHOOK: {hook_text}")

        # CUT VIDEO
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "video.mp4",
            "-ss", start_time,
            "-to", end_time,
            "-c", "copy",
            "clip.mp4"
        ])

        # FORMAT 9:16
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "clip.mp4",
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "short.mp4"
        ])

        # BUAT SUBTITLE FILE
        with open("subtitle.srt", "w", encoding="utf-8") as f:
            f.write("1\n")
            f.write("00:00:00,000 --> 00:00:03,000\n")
            f.write(hook_text + "\n")

        # BURN SUBTITLE
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "short.mp4",
            "-vf", "subtitles=subtitle.srt",
            "final.mp4"
        ])

        bot.reply_to(message, "📤 Mengirim hasil...")

        with open("final.mp4", "rb") as vid:
            bot.send_document(chat_id, vid)

        bot.reply_to(message, "✅ Selesai!")

        # CLEAN UP
        for file in ["video.mp4", "audio.mp3", "clip.mp4", "short.mp4", "subtitle.srt", "final.mp4"]:
            if os.path.exists(file):
                os.remove(file)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ===========================
# SAFE SHUTDOWN
# ===========================

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
