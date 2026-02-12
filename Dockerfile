FROM python:3.10

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
