#!/bin/bash

set -euo pipefail

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

SERVICE="${SPOOLER_SERVICE:-webgui}"

echo "[BOOTSTRAP] Service mode: ${SERVICE}"
case "${SERVICE}" in
    webgui)
        exec ./run_webgui.sh
        ;;
    daemon)
        exec ./run.sh
        ;;
    *)
        echo "[BOOTSTRAP] Invalid SPOOLER_SERVICE: ${SERVICE}"
        echo "[BOOTSTRAP] Valid values: webgui, daemon"
        exit 1
        ;;
esac
