FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

# Create input/output dirs (will be mounted at runtime, but ensure they exist)
RUN mkdir -p /app/input /app/output

ENTRYPOINT ["python", "main.py"] 