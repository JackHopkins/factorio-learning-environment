#!/bin/bash
set -e

# Detect Factorio binary path (handle ARM64 emulation via box64)
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    export FACTORIO_BIN="/bin/box64 /opt/factorio/bin/x64/factorio"
else
    export FACTORIO_BIN="/opt/factorio/bin/x64/factorio"
fi

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/fle.conf
