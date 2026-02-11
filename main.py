import os
import shutil
import telebot
from yt_dlp import YoutubeDL

BOT_TOKEN = os.getenv("BOT_TOKEN")

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def check_ffmpeg():
    """Cek apakah ffmpeg tersedia di server"""
    return shutil.which("ffmpeg") is not None


def download_youtube(url: str):
    """Download video YouTube dan return path file"""
    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": "mp4/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4",
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

        # Kalau hasilnya bukan mp4 (kadang webm), cari mp4 versi merge
        if not file_path.endswith(".mp4"):
            base = os.path.splitext(file_path)[0]
            mp4_path = base + ".mp4"
            if os.path.exists(mp4_path):
                file_path = mp4_path

        return file_path


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Halo 😎\n\nKirim perintah:\n/yt <link_youtube>\n\nContoh:\n/yt https://youtu.be/xxxxx"
    )


@bot.message_handler(commands=["yt"])
def yt_handler(message):
    try:
        text = message.text.strip()

        if len(text.split()) < 2:
            bot.reply_to(message, "Format salah.\n\nContoh:\n/yt https://youtu.be/xxxxx")
            return

        url = text.split(maxsplit=1)[1].strip()

        bot.reply_to(message, "📥 Downloading video...")

        # Cek ffmpeg dulu
        if not check_ffmpeg():
            bot.reply_to(
                message,
                "❌ ERROR: ffmpeg tidak ditemukan.\n\n"
                "Solusi:\n"
                "Ubuntu/Debian:\n"
                "sudo apt update && sudo apt install -y ffmpeg\n\n"
                "Setelah itu jalankan ulang bot."
            )
            return

        # Download
        file_path = download_youtube(url)

        if not os.path.exists(file_path):
            bot.reply_to(message, "❌ Gagal download video (file tidak ditemukan).")
            return

        # Kirim ke Telegram
        with open(file_path, "rb") as video:
            bot.send_video(message.chat.id, video)

        # Hapus file setelah terkirim
        os.remove(file_path)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("Bot running...")
    bot.infinity_polling()
