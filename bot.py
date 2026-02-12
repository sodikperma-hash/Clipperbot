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
            timeout=900
        )
        return p.returncode, p.stdout
    except Exception as e:
        return 1, str(e)


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
        raise RuntimeError(f"Gagal download.\n\n{out[-1500:]}")

    files = list(job_dir.glob("*"))
    if not files:
        clean_folder(job_dir)
        raise RuntimeError("Download selesai tapi file tidak ditemukan.")

    final_file = max(files, key=lambda p: p.stat().st_size)

    return final_file


# =========================
# COMMANDS
# =========================
@bot.message_handler(commands=["start", "help"])
def start(msg):
    text = (
        "🔥 <b>ClipperBot</b>\n\n"
        "Gunakan:\n"
        "• /yt https://youtube.com/xxxx\n"
        "ATAU\n"
        "• Kirim link langsung\n\n"
        "Lalu pilih format download."
    )
    bot.reply_to(msg, text)


# =========================
# HANDLE /yt COMMAND
# =========================
@bot.message_handler(commands=["yt"])
def handle_yt(msg):
    parts = msg.text.split(maxsplit=1)

    if len(parts) < 2:
        bot.reply_to(msg, "❌ Format salah.\n\nContoh:\n/yt https://youtube.com/xxxx")
        return

    url = parts[1].strip()

    if not url.startswith("http"):
        bot.reply_to(msg, "❌ Link harus diawali http/https.")
        return

    show_download_options(msg, url)


# =========================
# HANDLE DIRECT LINK
# =========================
@bot.message_handler(func=lambda m: True)
def handle_plain_link(msg):
    text = msg.text.strip()

    if not text.startswith("http"):
        return  # abaikan selain link

    show_download_options(msg, text)


# =========================
# SHOW BUTTONS
# =========================
def show_download_options(msg, url):
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


# =========================
# CALLBACK DOWNLOAD
# =========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("dl|"))
def callback_download(call):
    try:
        _, mode, url = call.data.split("|", 2)
    except:
        bot.answer_callback_query(call.id, "Data error.")
        return

    bot.answer_callback_query(call.id, "⏳ Diproses...")

    chat_id = call.message.chat.id

    status = bot.send_message(chat_id, "⏳ Download dimulai...")

    try:
        file_path = download_media(url, mode=mode)

        size = file_path.stat().st_size
        file_name = sanitize_filename(file_path.stem) + file_path.suffix

        bot.edit_message_text(
            f"📦 Size: <b>{human_size(size)}</b>\n⏳ Upload ke Telegram...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        # Batasi agar tidak OOM Railway
        if size > 80 * 1024 * 1024:
            bot.edit_message_text(
                "❌ File terlalu besar untuk server Railway.\n"
                "Gunakan video lebih pendek.",
                chat_id=chat_id,
                message_id=status.message_id
            )
            clean_folder(file_path.parent)
            return

        with open(file_path, "rb") as f:
            if mode == "mp3":
                bot.send_audio(chat_id, f, caption=f"🎧 {file_name}")
            else:
                bot.send_video(chat_id, f, caption=f"🎬 {file_name}")

        bot.edit_message_text(
            "✅ Selesai! Kirim link lain kalau mau.",
            chat_id=chat_id,
            message_id=status.message_id
        )

        clean_folder(file_path.parent)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Gagal.\n\n{str(e)[:1000]}",
            chat_id=chat_id,
            message_id=status.message_id
        )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("🚀 Bot running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
