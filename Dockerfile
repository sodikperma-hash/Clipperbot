FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy project
COPY . .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start bot
CMD ["python", "bot.py"]
