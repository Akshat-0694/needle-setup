#!/bin/sh
set -eu
curl -fsS http://127.0.0.1:8000/health; echo
curl -fsS http://127.0.0.1:8000/tasks; echo
