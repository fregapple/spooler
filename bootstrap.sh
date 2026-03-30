#!/bin/bash

set -euo pipefail

DAEMON_PID=""
WEBGUI_PID=""

shutdown() {
    echo "[BOOTSTRAP] Stopping services..."

    if [ -n "${WEBGUI_PID}" ] && kill -0 "${WEBGUI_PID}" 2>/dev/null; then
        kill "${WEBGUI_PID}" 2>/dev/null || true
    fi

    if [ -n "${DAEMON_PID}" ] && kill -0 "${DAEMON_PID}" 2>/dev/null; then
        kill "${DAEMON_PID}" 2>/dev/null || true
    fi

    wait 2>/dev/null || true
}

trap shutdown EXIT SIGINT SIGTERM

if [ ! -d "/app/spooler" ]; then
    echo "[BOOTSTRAP] First run: cloning repo..."
    git clone https://github.com/fregapple/spooler.git /app/repo

    echo "[BOOTSTRAP] Copying code into /app/spooler..."
    cp -r /app/repo/spooler /app/spooler
    cp /app/repo/config/config_example.yaml /app/config/config_example.yaml
else
    echo "[BOOTSTRAP] Code already present, skipping clone and copy."
fi

cd /app/spooler

echo "[BOOTSTRAP] Starting daemon (run.sh)..."
./run.sh &
DAEMON_PID=$!

FORWARDER_PORT="${SPOOLER_FORWARDER_PORT:-8765}"
echo "[BOOTSTRAP] Waiting for daemon on 127.0.0.1:${FORWARDER_PORT}..."
for _ in $(seq 1 120); do
    if ! kill -0 "${DAEMON_PID}" 2>/dev/null; then
        echo "[BOOTSTRAP] Daemon exited before becoming ready."
        wait "${DAEMON_PID}"
        exit 1
    fi

    if bash -c "echo > /dev/tcp/127.0.0.1/${FORWARDER_PORT}" 2>/dev/null; then
        echo "[BOOTSTRAP] Daemon is ready."
        break
    fi

    sleep 1
done

echo "[BOOTSTRAP] Starting web GUI (run_webgui.sh)..."
./run_webgui.sh &
WEBGUI_PID=$!

set +e
wait -n "${DAEMON_PID}" "${WEBGUI_PID}"
EXIT_CODE=$?
set -e

if ! kill -0 "${DAEMON_PID}" 2>/dev/null; then
    echo "[BOOTSTRAP] Daemon exited."
fi
if ! kill -0 "${WEBGUI_PID}" 2>/dev/null; then
    echo "[BOOTSTRAP] Web GUI exited."
fi

exit "${EXIT_CODE}"