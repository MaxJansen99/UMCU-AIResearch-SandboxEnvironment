#!/usr/bin/env sh
set -e

exec uvicorn app.main:app --host "${QUERY_HOST:-0.0.0.0}" --port "${QUERY_PORT:-8000}"
