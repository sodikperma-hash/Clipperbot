import os
import telebot
import yt_dlp
import subprocess
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)


# ==========================
# START
# ==========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Kirim link YouTube pakai:\n\n/yt https://youtube.com/xxxxx\n\nBot akan:\n- Download\n- Cari moment viral\n- Potong 60 detik\n- Tambah subtitle\n- Kirim clip")


# ==========================
# YOUTUBE PROCESS
# ==========================

@bot.message_handler(commands=['yt'])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Masukkan link YouTube.")
        return

    bot.reply_to(message, "📥 Download video...")

    try:
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": "video.mp4",
            "noplaylist": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.reply_to(message, "🎧 Extract audio...")

        subprocess.run([
            "ffmpeg", "-i", "video.mp4",
            "-q:a", "0",
            "-map", "a",
            "audio.mp3"
        ], check=True)

        bot.reply_to(message, "🧠 Transcribe audio...")

        with open("audio.mp3", "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file
            )

        text = transcript.text

        bot.reply_to(message, "🔥 Mencari moment paling menarik...")

        highlight_prompt = f"""
Dari transcript berikut, pilih bagian paling menarik dan viral.
Tentukan waktu mulai dalam detik (angka saja).

Jawaban format:
START: angka_detik

Transcript:
{text}
"""

        highlight = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": highlight_prompt}]
        )

        result = highlight.choices[0].message.content

        start_time = 0
        for line in result.splitlines():
            if "START" in line:
                start_time = int(line.split(":")[1].strip())

        bot.reply_to(message, f"✂ Memotong dari detik {start_time}...")

        subprocess.run([
            "ffmpeg",
            "-i", "video.mp4",
            "-ss", str(start_time),
            "-t", "60",
            "-vf", "scale=1080:1920",
            "-c:a", "aac",
            "clip.mp4"
        ], check=True)

        bot.reply_to(message, "📝 Membuat subtitle...")

        with open("audio.mp3", "rb") as audio_file:
            srt = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                response_format="srt"
            )

        with open("subtitle.srt", "w") as f:
            f.write(srt)

        subprocess.run([
            "ffmpeg",
            "-i", "clip.mp4",
            "-vf", "subtitles=subtitle.srt:force_style='Fontsize=24,PrimaryColour=&Hffffff&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'",
            "final.mp4"
        ], check=True)

        bot.reply_to(message, "📤 Mengirim clip...")

        with open("final.mp4", "rb") as video:
            bot.send_video(message.chat.id, video)

        bot.reply_to(message, "✅ Selesai! Clip siap upload 🔥")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


# ==========================
# RUN
# ==========================

bot.remove_webhook()
bot.infinity_polling()
