FROM python:3.11-slim

# Sistem bağımlılıkları (FFmpeg, git, fontlar)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python bağımlılıklarını kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn fastapi

# Proje dosyalarını kopyala
COPY . .

# Hugging Face Spaces varsayılan portu 7860
EXPOSE 7860

# Servisi ve web dashboard'unu başlat
CMD ["python", "hf_entrypoint.py"]
