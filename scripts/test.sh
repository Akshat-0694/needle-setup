#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://127.0.0.1:8000/health
echo
echo

curl -fsS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"agent":"system","prompt":"Give me a short system status report."}'
echo
