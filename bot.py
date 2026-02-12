import os
import telebot
import yt_dlp
import subprocess
from openai import OpenAI

# ==============================
# ENV
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None


# ==============================
# START / HELP
# ==============================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎬 Clipper Bot Aktif!\n\nKirim:\n/yt link_youtube")


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Gunakan:\n\n/yt https://youtube.com/xxxx")


# ==============================
# YOUTUBE DOWNLOAD
# ==============================

@bot.message_handler(commands=['yt'])
def download_video(message):

    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Masukkan link YouTube.\nContoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "📥 Downloading video...")

    try:
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": "video.%(ext)s",
            "noplaylist": True,
            "merge_output_format": "mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        filename = "video.mp4"

        # ==============================
        # CEK SIZE
        # ==============================

        file_size = os.path.getsize(filename) / (1024 * 1024)  # MB

        # Jika lebih dari 49MB → compress
        if file_size > 49:
            bot.reply_to(message, "🎛 Compressing video...")

            compressed = "compressed.mp4"

            subprocess.run([
                "ffmpeg",
                "-i", filename,
                "-vcodec", "libx264",
                "-crf", "28",
                "-preset", "veryfast",
                "-acodec", "aac",
                "-b:a", "128k",
                compressed
            ])

            filename = compressed
            file_size = os.path.getsize(filename) / (1024 * 1024)

        # ==============================
        # KIRIM
        # ==============================

        if file_size <= 49:
            with open(filename, "rb") as video:
                bot.send_video(message.chat.id, video)
        else:
            with open(filename, "rb") as video:
                bot.send_document(message.chat.id, video)

        bot.reply_to(message, "✅ Selesai!")

        # Hapus file
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")
        if os.path.exists("compressed.mp4"):
            os.remove("compressed.mp4")

    except Exception as e:
        bot.reply_to(message, f"❌ ERROR: {e}")


# ==============================
# RUN
# ==============================

bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
