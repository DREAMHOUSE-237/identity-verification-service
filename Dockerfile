FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKER_ID=0

WORKDIR /app

# Tesseract OCR + langue française + dépendances MySQL
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    libtesseract-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media/cni/recto /app/media/cni/verso

EXPOSE 8087

CMD ["gunicorn", "identity_project.wsgi:application", \
     "--bind", "0.0.0.0:8087", \
     "--workers", "1", \
     "--timeout", "120", \
     "--preload"]
