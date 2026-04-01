FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --default-timeout=1000 --no-cache-dir idc-index

COPY fetch_idc.py .

ENTRYPOINT ["python", "/app/fetch_idc.py"]
