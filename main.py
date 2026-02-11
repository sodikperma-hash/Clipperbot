import os
import telebot
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DEBUG BOT_TOKEN:", BOT_TOKEN)
print("DEBUG OPENAI_API_KEY:", OPENAI_API_KEY)

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN NOT FOUND")

if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY NOT FOUND")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    transcript = message.text

    prompt = f"""
    Analisa transcript berikut:
    1. Cari 5 momen viral.
    2. Buat 5 hook kuat.
    3. Buat 3 caption TikTok.
    4. Buat 3 judul SEO.

    Transcript:
    {transcript}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    bot.reply_to(message, response.choices[0].message.content)

bot.polling()
