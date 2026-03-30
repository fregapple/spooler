#!/bin/bash

if [ ! -d "/app/spooler" ]; then
    echo "[BOOTSTRAP] First run: Cloning repo ..."
    git clone https://github.com/fregapple/spooler.git /app/repo
    
    echo "[BOOTSTRAP] Copying code into /app/spooler ..."   
    cp -r /app/repo/spooler /app/spooler
    cp /app/repo/config/config_example.yaml /app/config/config_example.yaml

else
    echo "[BOOTSRAP] Code already present, skipping clone and copy."
fi

cd /app/spooler
./run.sh