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

# Folder kerja
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================
# UTIL
# =========================
def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """
    Jalankan command dan ambil output (untuk debug).
    """
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


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s\-\.\(\)]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:80] if name else "file"


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} TB"


def safe_remove(path: Path):
    try:
        if path.exists():
            path.unlink()
    except:
        pass


def clean_folder(folder: Path):
    try:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
    except:
        pass


# =========================
# YT-DLP Download
# =========================
def download_media(url: str, mode: str = "mp4") -> Path:
    """
    mode:
      - mp4 -> video mp4
      - mp3 -> audio mp3
    """
    job_id = str(uuid.uuid4())[:8]
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(job_dir / "%(title)s.%(ext)s")

    if mode == "mp3":
        # Download best audio + convert mp3
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
        # Download best mp4 (video+audio)
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
        raise RuntimeError(f"Gagal download.\n\nLog:\n{out[-2000:]}")

    # Cari file hasil
    files = list(job_dir.glob("*"))
    if not files:
        clean_folder(job_dir)
        raise RuntimeError("Download selesai tapi file tidak ditemukan.")

    # Ambil file terbesar
    final_file = max(files, key=lambda p: p.stat().st_size)

    return final_file


# =========================
# TELEGRAM HANDLERS
# =========================
@bot.message_handler(commands=["start", "help"])
def start(msg):
    text = (
        "🔥 <b>ClipperBot</b>\n\n"
        "Kirim link:\n"
        "✅ YouTube\n"
        "✅ TikTok\n"
        "✅ Instagram (public)\n\n"
        "Lalu pilih:\n"
        "🎬 MP4 (Video)\n"
        "🎧 MP3 (Audio)\n\n"
        "Perintah:\n"
        "/start\n"
        "/help\n"
    )
    bot.reply_to(msg, text)


@bot.message_handler(func=lambda m: True)
def handle_link(msg):
    url = msg.text.strip()

    # Validasi kasar
    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(msg, "❌ Kirim link yang valid ya (harus diawali http/https).")
        return

    # Simpan url sementara via message reply markup
    kb = types.InlineKeyboardMarkup(row_width=2)

    btn_mp4 = types.InlineKeyboardButton("🎬 Download MP4", callback_data=f"dl|mp4|{url}")
    btn_mp3 = types.InlineKeyboardButton("🎧 Download MP3", callback_data=f"dl|mp3|{url}")

    kb.add(btn_mp4, btn_mp3)

    bot.reply_to(msg, "Pilih format download:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("dl|"))
def callback_download(call):
    try:
        _, mode, url = call.data.split("|", 2)
    except:
        bot.answer_callback_query(call.id, "Data error.")
        return

    bot.answer_callback_query(call.id, "⏳ Diproses...")

    chat_id = call.message.chat.id

    status = bot.send_message(chat_id, f"⏳ Download dimulai...\nMode: <b>{mode.upper()}</b>")

    try:
        file_path = download_media(url, mode=mode)

        size = file_path.stat().st_size
        file_name = sanitize_filename(file_path.stem) + file_path.suffix

        bot.edit_message_text(
            f"✅ Download selesai!\n📦 Size: <b>{human_size(size)}</b>\n⏳ Upload ke Telegram...",
            chat_id=chat_id,
            message_id=status.message_id
        )

        # Telegram limit:
        # - Bot biasanya aman sampai 50MB (kadang bisa 2000MB tergantung server)
        # Tapi untuk aman, kasih warning jika besar
        if size > 49 * 1024 * 1024:
            bot.send_message(
                chat_id,
                "⚠️ File cukup besar. Kalau gagal upload, berarti limit Telegram bot kena."
            )

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

        # Bersihin folder job
        clean_folder(file_path.parent)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Gagal.\n\n<b>Error:</b>\n{str(e)[:1500]}",
            chat_id=chat_id,
            message_id=status.message_id
        )


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("🚀 Bot running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
