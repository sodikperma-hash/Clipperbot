import os
import telebot
import subprocess
import whisper
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

MODEL = whisper.load_model("base")  # jangan pakai medium/besar (RAM jebol)

# ===============================
# DOWNLOAD YOUTUBE
# ===============================
def download_video(url):
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': 'video.mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ===============================
# TRANSCRIBE AUDIO
# ===============================
def transcribe():
    result = MODEL.transcribe("video.mp4")
    return result["segments"]

# ===============================
# CARI MOMENT PALING PANJANG (anggap viral)
# ===============================
def find_best_segment(segments):
    longest = max(segments, key=lambda x: x["end"] - x["start"])
    return int(longest["start"])

# ===============================
# BUAT SUBTITLE FILE
# ===============================
def generate_srt(segments, start_time):
    with open("subtitle.srt", "w", encoding="utf-8") as f:
        index = 1
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]

            if start_time <= seg_start <= start_time + 60:
                s = seg_start - start_time
                e = seg_end - start_time

                f.write(f"{index}\n")
                f.write(f"{format_time(s)} --> {format_time(e)}\n")
                f.write(f"{seg['text'].strip()}\n\n")
                index += 1

def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

# ===============================
# POTONG + RESIZE + SUBTITLE
# ===============================
def create_clip(start_time):
    subprocess.run([
        "ffmpeg",
        "-ss", str(start_time),
        "-i", "video.mp4",
        "-t", "60",
        "-vf", "scale=720:1280,subtitles=subtitle.srt",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-threads", "1",
        "-c:a", "aac",
        "-b:a", "96k",
        "clip.mp4"
    ], check=True)

# ===============================
# COMMAND /yt
# ===============================
@bot.message_handler(commands=["yt"])
def handle_yt(message):
    try:
        url = message.text.split(" ")[1]

        bot.reply_to(message, "⬇️ Downloading video...")
        download_video(url)

        bot.reply_to(message, "🧠 Transcribing audio...")
        segments = transcribe()

        bot.reply_to(message, "🔥 Mencari moment terbaik...")
        start_time = find_best_segment(segments)

        generate_srt(segments, start_time)

        bot.reply_to(message, f"✂️ Memotong dari detik {start_time}...")
        create_clip(start_time)

        bot.reply_to(message, "📤 Mengirim clip...")
        with open("clip.mp4", "rb") as vid:
            bot.send_video(message.chat.id, vid)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

bot.polling()
