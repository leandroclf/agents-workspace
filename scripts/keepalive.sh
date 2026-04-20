#!/usr/bin/env bash
# Run keepalive in background, logging to /tmp/agents-workspace-keepalive.log
#
# Para instalar como serviço systemd:
#   sudo cp scripts/keepalive.service /etc/systemd/system/agents-workspace-keepalive.service
#   sudo systemctl daemon-reload
#   sudo systemctl enable agents-workspace-keepalive
#   sudo systemctl start agents-workspace-keepalive
cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null || true
nohup python scripts/keepalive.py >> /tmp/agents-workspace-keepalive.log 2>&1 &
echo "Keep-alive iniciado. PID: $! | Log: /tmp/agents-workspace-keepalive.log"
