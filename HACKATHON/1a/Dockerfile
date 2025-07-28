FROM python:3.9-slim-bookworm

ARG TARGETPLATFORM=linux/amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY HACKATHON/1a/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY HACKATHON/1a/main.py main.py

RUN mkdir -p /app/input /app/output

CMD ["python", "main.py"]
