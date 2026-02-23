#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

PORT="${1:-${FACTORIO_SERVER_PORT:-41000}}"

if ! [[ "${PORT}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: port must be numeric (got '${PORT}')." >&2
  exit 1
fi

if (( PORT < 41000 || PORT > 41009 )); then
  echo "ERROR: port ${PORT} is outside reserved range 41000-41009." >&2
  exit 1
fi

if ! docker ps --format '{{.Names}} {{.Ports}}' | grep -Eq "(^| )[^ ]*factorio[^ ]* .*(${PORT}->27015/tcp)"; then
  echo "ERROR: no running Factorio container is mapped on reserved tcp port ${PORT}." >&2
  echo "Start/map a Factorio server on this port, or choose another reserved port." >&2
  exit 1
fi

export FACTORIO_SERVER_ADDRESS="127.0.0.1"
export FACTORIO_SERVER_PORT="${PORT}"
export SCREENSHOT_BACKEND="benchmark"
export LIVE_RENDER_PARALLEL="0"
export CATCHUP_RENDER_PARALLEL="1"
export CATCHUP_RENDER_TIMEOUT="900"
export CATCHUP_RENDER_RETRIES="1"
export CATCHUP_RENDER_TICKS="60"
export SKIP_WORLD_CHECK="0"

echo "Running video pipeline on ${FACTORIO_SERVER_ADDRESS}:${FACTORIO_SERVER_PORT}"
echo "Backend=${SCREENSHOT_BACKEND} live_parallel=${LIVE_RENDER_PARALLEL} catchup_parallel=${CATCHUP_RENDER_PARALLEL} timeout=${CATCHUP_RENDER_TIMEOUT} retries=${CATCHUP_RENDER_RETRIES} ticks=${CATCHUP_RENDER_TICKS}"

exec python run_with_video.py
