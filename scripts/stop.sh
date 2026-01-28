#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Stopping Money Drop services (if running)"

if [ -f /tmp/md_server.pid ]; then
  pid=$(cat /tmp/md_server.pid)
  if kill -0 "$pid" 2>/dev/null; then
    echo "Killing server pid $pid"
    kill "$pid" || true
    sleep 0.2
  fi
  rm -f /tmp/md_server.pid
fi

if [ -f /tmp/md_web.pid ]; then
  pid=$(cat /tmp/md_web.pid)
  if kill -0 "$pid" 2>/dev/null; then
    echo "Killing web pid $pid"
    kill "$pid" || true
    sleep 0.2
  fi
  rm -f /tmp/md_web.pid
fi

echo "Stopped. Logs: /tmp/md_server.log /tmp/md_web.log"

exit 0
