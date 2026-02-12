# Gunakan Python 3.10 slim
FROM python:3.10-slim

# Install ffmpeg + dependency penting
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements dulu (biar caching optimal)
COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip

# Install semua dependency Python
RUN pip install -r requirements.txt

# Copy semua file project
COPY . .

# Jalankan bot
CMD ["python", "bot.py"]
