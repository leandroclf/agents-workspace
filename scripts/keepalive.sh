#!/usr/bin/env bash
# Run keepalive in background, logging to /tmp/lf-keepalive.log
cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null || true
nohup python scripts/keepalive.py >> /tmp/lf-keepalive.log 2>&1 &
echo "Keep-alive iniciado. PID: $! | Log: /tmp/lf-keepalive.log"
