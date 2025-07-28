FROM --platform=linux/amd64 python:3.9-slim

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1 
ENV TOKENIZERS_PARALLELISM=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY ./models/ /app/models/
COPY ./src/    /app/src/

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "src/main.py"]

