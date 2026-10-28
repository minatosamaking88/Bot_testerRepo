#!/usr/bin/env bash
set -euo pipefail

customer_pid=""
order_pid=""

cleanup() {
  if [[ -n "$order_pid" ]]; then
    kill "$order_pid" 2>/dev/null || true
  fi
  if [[ -n "$customer_pid" ]]; then
    kill "$customer_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

export CUSTOMER_SERVICE_URL="${CUSTOMER_SERVICE_URL:-http://127.0.0.1:4174}"

.venv/bin/python -m uvicorn customer_service.main:app \
  --host 0.0.0.0 \
  --port 4174 &
customer_pid=$!

for attempt in {1..50}; do
  if .venv/bin/python -c \
    'import socket; socket.create_connection(("127.0.0.1", 4174), timeout=0.2).close()' \
    >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if ! .venv/bin/python -c \
  'import socket; socket.create_connection(("127.0.0.1", 4174), timeout=0.2).close()' \
  >/dev/null 2>&1; then
  printf '%s\n' "Customer service did not start on port 4174." >&2
  exit 1
fi

.venv/bin/python -m uvicorn order_service.main:app \
  --host 0.0.0.0 \
  --port 4173 &
order_pid=$!

wait -n "$customer_pid" "$order_pid"
