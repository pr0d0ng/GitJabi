FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && sed -i 's/torch==\([0-9\.]*\)+cu[0-9]*/torch==\1/' /app/requirements.txt \
    && sed -i 's/torchaudio==\([0-9\.]*\)+cu[0-9]*/torchaudio==\1/' /app/requirements.txt \
    && sed -i 's/torchvision==\([0-9\.]*\)+cu[0-9]*/torchvision==\1/' /app/requirements.txt \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "service.api:app", "--host", "0.0.0.0", "--port", "8080"]
