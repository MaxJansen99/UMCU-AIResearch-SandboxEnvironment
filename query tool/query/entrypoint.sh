#!/usr/bin/env sh
set -e

cert_dir="/certs"
cert_file="${QUERY_TLS_CERT:-${cert_dir}/server.crt}"
key_file="${QUERY_TLS_KEY:-${cert_dir}/server.key}"

if [ "${QUERY_TLS:-false}" = "1" ] || [ "$(echo "${QUERY_TLS:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ] || [ "$(echo "${QUERY_TLS:-false}" | tr '[:upper:]' '[:lower:]')" = "yes" ]; then
  if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
    echo "Creating self-signed certificate at $cert_file / $key_file"
    mkdir -p "$(dirname "$cert_file")"
    mkdir -p "$(dirname "$key_file")"
    openssl req -x509 -newkey rsa:2048 -days 365 -nodes \
      -subj "/CN=${QUERY_HOST:-0.0.0.0}" \
      -keyout "$key_file" \
      -out "$cert_file"
  fi
fi

args=""
if [ -n "${QUERY_HOST}" ]; then
  args="$args --host ${QUERY_HOST}"
fi
if [ -n "${QUERY_PORT}" ]; then
  args="$args --port ${QUERY_PORT}"
fi
if [ -n "${QUERY_TLS}" ] && ( [ "${QUERY_TLS}" = "1" ] || [ "$(echo "${QUERY_TLS}" | tr '[:upper:]' '[:lower:]')" = "true" ] || [ "$(echo "${QUERY_TLS}" | tr '[:upper:]' '[:lower:]')" = "yes" ] ); then
  args="$args --tls --tls-cert ${cert_file} --tls-key ${key_file}"
fi

if [ -n "${QUERY_TLS_CA}" ]; then
  args="$args --tls-ca ${QUERY_TLS_CA}"
fi

if [ -n "${DICOM_ROOT}" ]; then
  set -- "$DICOM_ROOT" $args
else
  set -- "idc-data/" $args
fi

exec python query.py "$@"
