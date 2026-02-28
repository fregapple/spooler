#!/bin/bash
git clone https://github.com/fregapple/spooler.git /app/repo
cp /app/repo/spooler /app/spooler
cp /app/repo/config/config_example.json /app/config/config_example.json
cd /app/spooler
./run.sh