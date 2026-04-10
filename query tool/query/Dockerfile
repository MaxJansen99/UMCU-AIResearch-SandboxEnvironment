FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV QUERY_PORT=8000

# openssl is needed to create self-signed cert on startup if no cert is provided
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY query.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

VOLUME ["/certs"]
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
