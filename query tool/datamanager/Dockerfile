FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DATAMANAGER_PORT=8001

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY datamanager.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

VOLUME ["/depersonalized"]
EXPOSE 8001

ENTRYPOINT ["./entrypoint.sh"]
