import os
import telebot
from openai import OpenAI
import yt_dlp
import subprocess
import signal
import sys
import uuid

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Kirim /yt + link YouTube\nSaya akan potong 60 detik dan kirim ulang.")


# =========================
# YOUTUBE CLIP COMMAND
# =========================
@bot.message_handler(commands=['yt'])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Contoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "⬇️ Downloading video...")

    unique_id = str(uuid.uuid4())
    raw_file = f"{unique_id}.mp4"
    clip_file = f"clip_{unique_id}.mp4"

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": raw_file,
        "noplaylist": True
    }

    try:
        # DOWNLOAD VIDEO
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.reply_to(message, "✂️ Memotong 60 detik...")

        # POTONG 60 DETIK + COMPRESS
        subprocess.run([
            "ffmpeg",
            "-i", raw_file,
            "-t", "60",
            "-vf", "scale=1280:-2",
            "-vcodec", "libx264",
            "-preset", "veryfast",
            "-crf", "30",
            "-acodec", "aac",
            "-b:a", "96k",
            clip_file
        ])

        bot.reply_to(message, "📤 Mengirim clip...")

        with open(clip_file, "rb") as video:
            bot.send_video(message.chat.id, video)

        # HAPUS FILE
        os.remove(raw_file)
        os.remove(clip_file)

    except Exception as e:
        bot.reply_to(message, f"❌ ERROR: {e}")


# =========================
# GRACEFUL SHUTDOWN
# =========================
def signal_handler(sig, frame):
    print("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
