import os
import telebot
from openai import OpenAI
import yt_dlp
import subprocess
import signal
import sys

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DEBUG BOT_TOKEN:", BOT_TOKEN)
print("DEBUG OPENAI_API_KEY:", OPENAI_API_KEY)

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN NOT FOUND")

if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
@bot.message_handler(commands=['start'])
def send_start(message):
    bot.reply_to(message, "Halo! Kirim transcript video dan saya akan ubah jadi konten viral 🔥")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Kirim teks transcript.\nSaya akan buat:\n- 5 momen viral\n- 5 hook kuat\n- 3 caption\n- 3 judul SEO")

@bot.message_handler(commands=['clip'])
def handle_clip(message):
    transcript = message.text.replace("/clip", "").strip()

    if not transcript:
        bot.reply_to(message, "Kirim transcript setelah command.\n\nContoh:\n/clip Di video ini saya membahas...")
        return

    prompt = f"""
Analisa transcript berikut:
1. Cari 5 momen viral.
2. Buat 5 hook kuat.
3. Buat 3 caption TikTok.
4. Buat 3 judul SEO.

Transcript:
{transcript}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    bot.reply_to(message, response.choices[0].message.content)
    
@bot.message_handler(commands=['yt'])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Kirim link YouTube setelah command.\nContoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "Sedang download video...")

ydl_opts = {
    "format": "worst[height<=144]",
    "outtmpl": "video.mp4",
    "noplaylist": True
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open("video.mp4", "rb") as video:
            bot.send_video(message.chat.id, video)

        bot.reply_to(message, "Video berhasil dikirim.")

    except Exception as e:
        bot.reply_to(message, f"Gagal download video: {e}")

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
