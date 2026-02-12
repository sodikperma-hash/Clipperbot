import os
import telebot
import yt_dlp
import subprocess
import whisper
import uuid
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# DOWNLOAD YOUTUBE VIDEO
# =========================
def download_video(url, filename):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": filename,
        "noplaylist": True,
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# =========================
# POTONG 60 DETIK (AUTO)
# =========================
def cut_video(input_file, output_file, duration=60):
    command = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-t", str(duration),
        "-c", "copy",
        output_file
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# =========================
# TRANSKRIP WHISPER + SRT
# =========================
def transcribe_to_srt(video_path, srt_path):
    model = whisper.load_model("base")
    result = model.transcribe(video_path)

    segments = result["segments"]

    def format_time(t):
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        milliseconds = int((t - int(t)) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"].strip()

            f.write(f"{i+1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")


# =========================
# TAMBAH SUBTITLE KE VIDEO
# =========================
def burn_subtitle(input_video, subtitle_file, output_video):
    command = [
        "ffmpeg",
        "-y",
        "-i", input_video,
        "-vf", f"subtitles={subtitle_file}:force_style='Fontsize=28,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3,Outline=2,Shadow=1'",
        "-c:a", "copy",
        output_video
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# =========================
# COMMAND START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "🔥 Kirim:\n/yt link_youtube\n\nSaya akan:\n- Download\n- Potong 60 detik\n- Tambah subtitle\n- Kirim clip")


# =========================
# COMMAND YT
# =========================
@bot.message_handler(commands=["yt"])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Contoh:\n/yt https://youtube.com/xxxx")
        return

    unique_id = str(uuid.uuid4())
    original_video = f"{unique_id}_original.mp4"
    clipped_video = f"{unique_id}_clip.mp4"
    subtitle_file = f"{unique_id}.srt"
    final_video = f"{unique_id}_final.mp4"

    try:
        bot.reply_to(message, "⬇️ Downloading video...")
        download_video(url, original_video)

        bot.send_message(message.chat.id, "✂️ Memotong 60 detik...")
        cut_video(original_video, clipped_video)

        bot.send_message(message.chat.id, "🧠 Membuat subtitle...")
        transcribe_to_srt(clipped_video, subtitle_file)

        bot.send_message(message.chat.id, "🎬 Rendering subtitle...")
        burn_subtitle(clipped_video, subtitle_file, final_video)

        bot.send_message(message.chat.id, "📤 Mengirim clip...")
        with open(final_video, "rb") as vid:
            bot.send_video(message.chat.id, vid)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

    finally:
        for f in [original_video, clipped_video, subtitle_file, final_video]:
            if os.path.exists(f):
                os.remove(f)


# =========================
# RUN BOT
# =========================
bot.remove_webhook()
bot.infinity_polling(timeout=60, long_polling_timeout=60)
