import os
import re
import uuid
import shutil
import subprocess
from pathlib import Path

import telebot
from telebot import types

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN belum di-set di Railway Variables")

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================
# UTIL
# =========================
def run_cmd(cmd):
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600
        )
        return p.returncode, p.stdout
    except Exception as e:
        return 1, str(e)


def extract_url(text):
    urls = re.findall(r'https?://\S+', text)
    return urls[0] if urls else None


def sanitize_filename(name):
    name = re.sub(r"[^\w\s\-\.\(\)]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:80] if name else "file"


def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} TB"


def clean_folder(folder):
    try:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
    except:
        pass


# =========================
# DOWNLOAD FUNCTION
# =========================
def download_media(url, mode="mp4"):

    job_id = str(uuid.uuid4())[:8]
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(job_dir / "%(title)s.%(ext)s")

    if mode == "mp3":
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--no-playlist",
            "-o", output_template,
            url
        ]
    else:
        cmd = [
            "yt-dlp",
            "-f", "bv*+ba/best",
            "--merge-output-format", "mp4",
            "--no-playlist",
            "-o", output_template,
            url
        ]

    code, out = run_cmd(cmd)

    if code != 0:
        clean_folder(job_dir)
        raise RuntimeError(out[-2000:])

    files = list(job_dir.glob("*"))
    if not files:
        clean_folder(job_dir)
        raise RuntimeError("File tidak ditemukan.")

    return max(files, key=lambda p: p.stat().st_size)


# =========================
# HANDLERS
# =========================
@bot.message_handler(commands=["start", "help"])
def start(msg):
    bot.reply_to(
        msg,
        "🔥 <b>ClipperBot</b>\n\n"
        "Kirim link langsung atau pakai:\n"
        "<code>/yt https://link</code>\n\n"
        "Support:\n"
        "YouTube, TikTok, Instagram (public)"
    )


@bot.message_handler(commands=["yt"])
def handle_yt(msg):
    url = extract_url(msg.text)

    if not url:
        bot.reply_to(msg, "❌ Kirim link valid ya.")
        return

    show_format_buttons(msg, url)


@bot.message_handler(func=lambda m: True)
def handle_link(msg):
    url = extract_url(msg.text)

    if not url:
        bot.reply_to(msg, "❌ Kirim link yang valid (http/https).")
        return

    show_format_buttons(msg, url)


def show_format_buttons(msg, url):
    kb = types.InlineKeyboardMarkup(row_width=2)

    btn_mp4 = types.InlineKeyboardButton(
        "🎬 Download MP4",
        callback_data=f"dl|mp4|{url}"
    )
    btn_mp3 = types.InlineKeyboardButton(
        "🎧 Download MP3",
        callback_data=f"dl|mp3|{url}"
    )

    kb.add(btn_mp4, btn_mp3)

    bot.reply_to(msg, "Pilih format download:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("dl|"))
def callback_download(call):
    _, mode, url = call.data.split("|", 2)

    bot.answer_callback_query(call.id, "⏳ Diproses...")
    chat_id = call.message.chat.id

    status = bot.send_message(chat_id, "⏳ Download dimulai...")

    try:
        file_path = download_media(url, mode)
        size = file_path.stat().st_size
        file_name = sanitize_filename(file_path.stem) + file_path.suffix

        bot.edit_message_text(
            f"📦 Size: {human_size(size)}\n⏳ Upload...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        with open(file_path, "rb") as f:
            if mode == "mp3":
                bot.send_audio(chat_id, f, caption=f"🎧 {file_name}")
            else:
                bot.send_video(chat_id, f, caption=f"🎬 {file_name}")

        bot.edit_message_text(
            "✅ Selesai! Kirim link lagi kalau mau.",
            chat_id=chat_id,
            message_id=status.message_id
        )

        clean_folder(file_path.parent)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Gagal:\n{str(e)[:1500]}",
            chat_id=chat_id,
            message_id=status.message_id
        )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("🚀 Bot running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
