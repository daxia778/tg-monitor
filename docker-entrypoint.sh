#!/bin/sh
# Docker entrypoint: auto-initialize config.yaml from example if not mounted
set -e

if [ ! -f /app/config.yaml ]; then
    echo "[entrypoint] config.yaml not found — copying from config.example.yaml"
    cp /app/config.example.yaml /app/config.yaml
fi

exec python -m src.cli "$@"
