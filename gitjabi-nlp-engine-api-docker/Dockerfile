FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# RUN python -c "from sentence_transformers import SentenceTransformer; \
#     SentenceTransformer('snunlp/KR-SBERT-V4-entity-clustering')"

COPY . .

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]


##################################################33

# # FROM python:3.11-slim
# FROM python:3.12-slim-bookworm

# RUN apt-get update && apt-get install -y \
#     openjdk-17-jdk-headless \
#     build-essential \
#     gcc \
#     g++ \
#     python3-dev \
#     curl \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# WORKDIR /code

# COPY requirements.txt .

# RUN pip install --upgrade pip setuptools wheel
# RUN pip install --upgrade --no-cache-dir -r requirements.txt

# COPY . .

# # EXPOSE 80
# # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
# EXPOSE 80
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]