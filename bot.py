import os
import telebot
import yt_dlp
import whisper
import subprocess
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

model = whisper.load_model("base")


# =============================
# DOWNLOAD YOUTUBE
# =============================
def download_video(url):
    ydl_opts = {
        "format": "best",
        "outtmpl": "video.%(ext)s",
        "noplaylist": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video.mp4"


# =============================
# TRANSCRIBE
# =============================
def transcribe_video(path):
    result = model.transcribe(path)
    return result


# =============================
# FIND VIRAL MOMENT (AI)
# =============================
def find_best_segment(transcript_text):
    prompt = f"""
Pilih bagian paling emosional dan viral dari transcript ini.
Berikan waktu mulai dalam detik saja (angka).
Durasi maksimal 60 detik.

Transcript:
{transcript_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    start_time = int(''.join(filter(str.isdigit, response.choices[0].message.content)))
    return start_time


# =============================
# CUT 60 DETIK
# =============================
def cut_video(start):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", "video.mp4",
        "-t", "60",
        "-vf", "scale=1080:1920",
        "clip.mp4"
    ]
    subprocess.run(cmd)


# =============================
# GENERATE SRT DENGAN WARNA
# =============================
def generate_srt(result, start):
    segments = result["segments"]
    with open("sub.srt", "w", encoding="utf-8") as f:
        index = 1
        for seg in segments:
            if seg["start"] >= start and seg["start"] <= start + 60:
                text = seg["text"].strip()

                # highlight kata kuat
                words = text.split()
                if len(words) > 3:
                    words[0] = f"<font color='#00FF00'>{words[0]}</font>"
                text = " ".join(words)

                start_time = seg["start"] - start
                end_time = seg["end"] - start

                f.write(f"{index}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(text + "\n\n")
                index += 1


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# =============================
# RENDER FINAL VIDEO
# =============================
def render_final():
    hook_text = "INI MOMEN PALING GILA"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", "clip.mp4",
        "-vf",
        f"subtitles=sub.srt:force_style='Fontsize=48,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=120',"
        f"drawtext=text='{hook_text}':fontcolor=black:fontsize=60:box=1:boxcolor=white@0.9:x=(w-text_w)/2:y=100",
        "-c:a", "copy",
        "final.mp4"
    ]
    subprocess.run(cmd)


# =============================
# TELEGRAM COMMAND
# =============================
@bot.message_handler(commands=['yt'])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Kirim link setelah /yt")
        return

    bot.reply_to(message, "⬇️ Download video...")
    download_video(url)

    bot.reply_to(message, "🧠 Transcribe...")
    result = transcribe_video("video.mp4")

    transcript_text = " ".join([seg["text"] for seg in result["segments"]])

    bot.reply_to(message, "🔥 Mencari momen viral...")
    start = find_best_segment(transcript_text)

    bot.reply_to(message, "✂️ Memotong 60 detik...")
    cut_video(start)

    bot.reply_to(message, "📝 Menambahkan subtitle...")
    generate_srt(result, start)

    bot.reply_to(message, "🎬 Rendering final...")
    render_final()

    with open("final.mp4", "rb") as video:
        bot.send_video(message.chat.id, video)

    bot.reply_to(message, "✅ Selesai! Siap upload Shorts 🔥")


bot.infinity_polling()
