#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -n "$AGENT_VENV" ]; then
    VENV_PATH="$AGENT_VENV"
    echo "[SETUP] Using override venv at $VENV_PATH"
else
    VENV_PATH="$SCRIPT_DIR/venv"
    echo "[SETUP] Using server venv at $VENV_PATH"
fi

if [ ! -d "$VENV_PATH" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

echo "[SETUP] Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "[SETUP] Installing dependencies..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Forwarder target settings (daemon stream endpoint)
if [ -n "${1:-}" ]; then
    DAEMON_HOST="$1"
    DAEMON_PORT="${2:-8765}"
    export SPOOLER_FORWARDER_URL="ws://${DAEMON_HOST}:${DAEMON_PORT}"
fi
export SPOOLER_FORWARDER_URL="${SPOOLER_FORWARDER_URL:-ws://127.0.0.1:8765}"
echo "[NET] Forwarder target: ${SPOOLER_FORWARDER_URL}"
if [ "${SPOOLER_FORWARDER_URL}" = "ws://127.0.0.1:8765" ]; then
    echo "[NET] Mode: local daemon (same machine)"
fi

echo "[RUN] Starting Spooler Web GUI on http://0.0.0.0:8949"
python3 "$SCRIPT_DIR/webgui.py"
