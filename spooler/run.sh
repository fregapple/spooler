#!/bin/bash

# Move to the directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Decide which venv to use
if [ -n "$AGENT_VENV" ]; then
    VENV_PATH="$AGENT_VENV"
    echo "[SETUP] Using override venv at $VENV_PATH"
else
    VENV_PATH="$SCRIPT_DIR/venv"
    echo "[SETUP] Using server venv at $VENV_PATH"
fi

# Create venv if missing
if [ ! -d "$VENV_PATH" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate venv
echo "[SETUP] Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Install dependencies
echo "[SETUP] Installing dependencies..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Forwarder bind settings (for WebGUI connection)
if [ -n "${1:-}" ]; then
    export SPOOLER_FORWARDER_HOST="$1"
fi
if [ -n "${2:-}" ]; then
    export SPOOLER_FORWARDER_PORT="$2"
fi
export SPOOLER_FORWARDER_HOST="${SPOOLER_FORWARDER_HOST:-127.0.0.1}"
export SPOOLER_FORWARDER_PORT="${SPOOLER_FORWARDER_PORT:-8765}"
echo "[NET] Forwarder bind: ${SPOOLER_FORWARDER_HOST}:${SPOOLER_FORWARDER_PORT}"
if [ "${SPOOLER_FORWARDER_HOST}" = "127.0.0.1" ]; then
    echo "[NET] Mode: local daemon only (same machine)"
fi

# Run daemon

clear
cat << "EOF"
  _______  _______  _______  _______  ___      _______  ______
 |       ||       ||       ||       ||   |    |       ||    _ |
 |  _____||    _  ||   _   ||   _   ||   |    |    ___||   | ||
 | |_____ |   |_| ||  | |  ||  | |  ||   |    |   |___ |   |_||_
 |_____  ||    ___||  |_|  ||  |_|  ||   |___ |    ___||    __  |
  _____| ||   |    |       ||       ||       ||   |___ |   |  | |
 |_______||___|    |_______||_______||_______||_______||___|  |_|
 
          Spoolman - Centauri Carbon - Orcaslicer Bridge
================================================================
EOF
echo "[RUN] Starting SDCP --- Spoolman daemon..."
python3 "$SCRIPT_DIR/daemon.py"