#!/usr/bin/env bash
set -euo pipefail

# Start script for Money Drop (socket server + web app)
# Usage: ./scripts/start.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[moneydrop] Starting from $ROOT"

# create venv if missing
if [ ! -d .venv ]; then
  echo "Creating virtualenv .venv..."
  python3 -m venv .venv
fi

echo "Activating venv and installing requirements (if needed)..."
. .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
pip install -r requirements.txt >/dev/null 2>&1 || true

# Choose PID / LOG file names. Prefer global /tmp/md_*.pid/.log, but if they exist and are owned by another user
# fall back to per-user files to avoid requiring sudo or clobbering another user's files.
SERVER_PID_GLOBAL="/tmp/md_server.pid"
SERVER_LOG_GLOBAL="/tmp/md_server.log"
WEB_PID_GLOBAL="/tmp/md_web.pid"
WEB_LOG_GLOBAL="/tmp/md_web.log"

if [ -f "$SERVER_PID_GLOBAL" ] && [ "$(stat -c %u "$SERVER_PID_GLOBAL")" != "$(id -u)" ]; then
  SERVER_PID="/tmp/md_server_${USER}.pid"
  SERVER_LOG="/tmp/md_server_${USER}.log"
else
  SERVER_PID="$SERVER_PID_GLOBAL"
  SERVER_LOG="$SERVER_LOG_GLOBAL"
fi

if [ -f "$WEB_PID_GLOBAL" ] && [ "$(stat -c %u "$WEB_PID_GLOBAL")" != "$(id -u)" ]; then
  WEB_PID="/tmp/md_web_${USER}.pid"
  WEB_LOG="/tmp/md_web_${USER}.log"
else
  WEB_PID="$WEB_PID_GLOBAL"
  WEB_LOG="$WEB_LOG_GLOBAL"
fi

# stop previous instances if any (using chosen pid files)
if [ -f "$SERVER_PID" ]; then
  old=$(cat "$SERVER_PID")
  if kill -0 "$old" 2>/dev/null; then
    echo "Stopping old server pid $old"
    kill "$old" || true
    sleep 0.2
  fi
  rm -f "$SERVER_PID" || true
fi
if [ -f "$WEB_PID" ]; then
  old=$(cat "$WEB_PID")
  if kill -0 "$old" 2>/dev/null; then
    echo "Stopping old web pid $old"
    kill "$old" || true
    sleep 0.2
  fi
  rm -f "$WEB_PID" || true
fi

echo "Starting socket server (server.py) on 0.0.0.0:5050..."
nohup .venv/bin/python3 server.py --host 0.0.0.0 --port 5050 > "$SERVER_LOG" 2>&1 &
echo $! > "$SERVER_PID"

WEB_PORT=${MONEYDROP_PORT:-8001}
export MONEYDROP_PORT="$WEB_PORT"
export MONEYDROP_HOST="0.0.0.0"
echo "Starting web app (web_app.py) on http://0.0.0.0:$WEB_PORT ..."
nohup .venv/bin/python3 web_app.py > "$WEB_LOG" 2>&1 &
echo $! > "$WEB_PID"

echo "Started."
echo "Socket server log: $SERVER_LOG (pid $(cat $SERVER_PID))"
echo "Web log: $WEB_LOG (pid $(cat $WEB_PID))"
# Afficher l'IP locale pour que les autres puissent se connecter
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "🌐 Accédez au serveur via: http://$LOCAL_IP:$WEB_PORT"
echo "💡 Partagez cette adresse IP avec vos amis pour qu'ils se connectent à distance!"

exit 0
