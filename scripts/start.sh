#!/usr/bin/env bash
# run chmod +x scripts/start.sh first
set -e
command -v memory-mesh &>/dev/null || pip install -e .
LOCAL_IP=$(python3 -c "import socket; s=socket.socket(); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()")
echo "Local:     http://${LOCAL_IP}:8765"
echo "mDNS:      http://memory-mesh.local:8765"
TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
[ -n "$TS_IP" ] && echo "Tailscale: http://${TS_IP}:8765"
if [[ "$1" == "--chatgpt" ]]; then
  memory-mesh chatgpt "${@:2}"
else
  memory-mesh serve
fi
