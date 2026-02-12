import os
import telebot
import yt_dlp
import subprocess
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)


# ===============================
# UTIL FUNCTIONS
# ===============================

def download_video(url):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "video.mp4",
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def extract_audio():
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "video.mp4",
        "-vn",
        "-acodec", "mp3",
        "audio.mp3"
    ])


def transcribe_audio():
    with open("audio.mp3", "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text


def find_best_moment(transcript):
    prompt = f"""
Dari transcript berikut, pilih bagian paling menarik dan viral.
Berikan jawaban dalam format:
START:detik
END:detik

Transcript:
{transcript}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.choices[0].message.content

    try:
        start = int(text.split("START:")[1].split("\n")[0])
        end = int(text.split("END:")[1].split("\n")[0])
    except:
        start = 0
        end = 60

    if end - start > 60:
        end = start + 60

    return start, end


def cut_video(start, end):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "video.mp4",
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy",
        "clip.mp4"
    ])


def generate_srt(transcript):
    lines = transcript.split(".")
    srt_content = ""
    index = 1
    time_cursor = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        start_time = time_cursor
        end_time = time_cursor + 4

        srt_content += f"{index}\n"
        srt_content += f"00:00:{start_time:02d},000 --> 00:00:{end_time:02d},000\n"
        srt_content += f"{line}\n\n"

        index += 1
        time_cursor += 4

    with open("subtitle.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)


def burn_subtitle():
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "clip.mp4",
        "-vf", "subtitles=subtitle.srt:force_style='Fontsize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3'",
        "-c:a", "copy",
        "final.mp4"
    ])


# ===============================
# TELEGRAM COMMAND
# ===============================

@bot.message_handler(commands=["yt"])
def handle_yt(message):
    url = message.text.replace("/yt", "").strip()

    if not url:
        bot.reply_to(message, "Kirim link YouTube setelah command.\nContoh:\n/yt https://youtube.com/xxxx")
        return

    bot.reply_to(message, "⬇️ Download video...")
    download_video(url)

    bot.reply_to(message, "🎧 Extract audio...")
    extract_audio()

    bot.reply_to(message, "🧠 Transcribe...")
    transcript = transcribe_audio()

    bot.reply_to(message, "🔥 Cari moment terbaik...")
    start, end = find_best_moment(transcript)

    bot.reply_to(message, f"✂️ Potong dari {start}s sampai {end}s...")
    cut_video(start, end)

    bot.reply_to(message, "📝 Generate subtitle...")
    generate_srt(transcript)

    bot.reply_to(message, "🎬 Render subtitle...")
    burn_subtitle()

    bot.reply_to(message, "📤 Kirim clip...")

    with open("final.mp4", "rb") as video:
        bot.send_video(message.chat.id, video)

    bot.reply_to(message, "✅ Selesai!")


print("Bot is running...")
bot.infinity_polling()
