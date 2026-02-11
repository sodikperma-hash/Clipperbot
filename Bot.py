import os
import shutil
import time
import telebot
from yt_dlp import YoutubeDL

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN NOT FOUND. Set it in Railway Variables.")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_VIDEO_MB = 45  # aman untuk Telegram (biar ga gagal)
MAX_VIDEO_BYTES = MAX_VIDEO_MB * 1024 * 1024


def check_ffmpeg():
    return shutil.which("ffmpeg") is not None


def safe_filename(name: str):
    # biar nama file ga error
    return "".join(c for c in name if c.isalnum() or c in " .-_()[]").strip()


def download_youtube(url: str):
    """
    Download video YouTube.
    Return: file_path (mp4)
    """

    # Nama file unik biar gak bentrok
    unique = str(int(time.time()))
    outtmpl = f"{DOWNLOAD_DIR}/{unique}_%(title)s.%(ext)s"

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*+ba/best",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4",
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        title = safe_filename(info.get("title", "video"))
        ext = info.get("ext", "mp4")

        # File awal
        file_path = ydl.prepare_filename(info)

        # Kadang hasil merge jadi mp4 tapi prepare_filename masih ext lama
        base = os.path.splitext(file_path)[0]
        mp4_path = base + ".mp4"

        if os.path.exists(mp4_path):
            return mp4_path

        # fallback kalau memang sudah mp4
        if os.path.exists(file_path):
            return file_path

        raise FileNotFoundError("Download selesai tapi file output tidak ditemukan.")


def get_file_size(path: str):
    return os.path.getsize(path)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Halo 😎\n\n"
        "Kirim perintah:\n"
        "/yt <link_youtube>\n\n"
        "Contoh:\n"
        "/yt https://youtu.be/xxxxx"
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

        # cek ffmpeg
        if not check_ffmpeg():
            bot.reply_to(
                message,
                "❌ ERROR: ffmpeg tidak ditemukan.\n\n"
                "Railway butuh Dockerfile untuk install ffmpeg.\n"
                "Pastikan project kamu sudah pakai Dockerfile."
            )
            return

        # download
        file_path = download_youtube(url)

        if not os.path.exists(file_path):
            bot.reply_to(message, "❌ File tidak ditemukan setelah download.")
            return

        size = get_file_size(file_path)

        # kirim sesuai ukuran
        with open(file_path, "rb") as f:
            if size <= MAX_VIDEO_BYTES:
                bot.send_video(message.chat.id, f, caption="✅ Done 😎")
            else:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"⚠️ Video besar ({round(size/1024/1024,1)}MB). Dikirim sebagai file."
                )

        # hapus file
        try:
            os.remove(file_path)
        except:
            pass

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("Bot running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
