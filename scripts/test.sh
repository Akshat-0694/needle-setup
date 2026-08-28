#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:8000/health; echo
curl -fsS -X POST http://127.0.0.1:8000/message -H 'Content-Type: application/json' -d '{"text":"List my open tasks."}'; echo
