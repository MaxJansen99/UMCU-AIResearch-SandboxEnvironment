#!/usr/bin/env sh
set -e

if [ -n "${DATAMANAGER_PACS_URL}" ]; then
  set -- "${DATAMANAGER_PACS_URL}" $args
else
  echo "DATAMANAGER_PACS_URL is required"
  exit 1
fi

exec python /app/datamanager.py "$@"
