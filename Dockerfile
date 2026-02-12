FROM python:3.10

RUN apt-get update && apt-get install -y ffmpeg

RUN pip install --upgrade pip
RUN pip install openai openai-whisper yt-dlp pyTelegramBotAPI

WORKDIR /app
COPY . .

CMD ["python", "bot.py"]
