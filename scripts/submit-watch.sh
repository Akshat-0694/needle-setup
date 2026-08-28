#!/usr/bin/env bash
set -euo pipefail

URL="${1:?Usage: ./scripts/submit-watch.sh https://example.com [previous_hash]}"
PREVIOUS="${2:-}"

python3 - "$URL" "$PREVIOUS" <<'PY'
import json, sys, urllib.request, uuid

url = sys.argv[1]
previous = sys.argv[2]
payload = {"needle":"watcher","action":"check","payload":{"url":url}}
if previous:
    payload["payload"]["previous_hash"] = previous

req = urllib.request.Request(
    "http://127.0.0.1:8000/tasks",
    data=json.dumps(payload).encode(),
    headers={"Content-Type":"application/json"},
)
with urllib.request.urlopen(req) as r:
    print(r.read().decode())
PY
