#!/usr/bin/env bash
set -euo pipefail

echo "== Health =="
curl -fsS http://127.0.0.1:8000/health
echo
echo

echo "== Researcher smoke test =="
curl -fsS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"needle":"researcher","payload":{"question":"Explain what an event bus is in one paragraph."}}'
echo
echo

sleep 3
echo "== Recent events =="
curl -fsS http://127.0.0.1:8000/events?limit=10
echo
