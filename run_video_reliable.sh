#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

PROFILE="${WORLD_PROFILE:-open_world}"
if [[ "${PROFILE}" != "open_world" && "${PROFILE}" != "default_lab_scenario" ]]; then
  echo "ERROR: WORLD_PROFILE must be one of: open_world, default_lab_scenario" >&2
  exit 1
fi

PORT="${1:-}"
if [[ -z "${PORT}" ]]; then
  if [[ "${PROFILE}" == "default_lab_scenario" ]]; then
    # Default-lab runs are pinned to our isolated dedicated server.
    PORT="41000"
  else
    PORT="$(python resolve_scenario_port.py --profile "${PROFILE}" --ports "41000-41009" --output port)"
  fi
else
  if ! [[ "${PORT}" =~ ^[0-9]+$ ]]; then
    echo "ERROR: port must be numeric (got '${PORT}')." >&2
    exit 1
  fi
  if (( PORT < 41000 || PORT > 41009 )); then
    echo "ERROR: port ${PORT} is outside reserved range 41000-41009." >&2
    exit 1
  fi
fi

if [[ "${ENSURE_ISOLATED_CODEX_SERVER:-1}" == "1" && "${PORT}" == "41000" && "${PROFILE}" == "default_lab_scenario" ]]; then
  UDP_PORT="${FACTORIO_SERVER_UDP_PORT:-$((46000 + PORT - 41000))}"
  "${ROOT_DIR}/ensure_codex_factorio_server.sh" "${PROFILE}" "${PORT}" "${UDP_PORT}"
fi

# Validate selected port matches requested scenario profile.
python resolve_scenario_port.py --profile "${PROFILE}" --ports "${PORT}" --output port >/dev/null

if ! docker ps --format '{{.Names}} {{.Ports}}' | grep -Eq "(^| )[^ ]*factorio[^ ]* .*(${PORT}->27015/tcp)"; then
  echo "ERROR: no running Factorio container is mapped on tcp port ${PORT}." >&2
  exit 1
fi

CONTAINER="$(docker ps --format '{{.Names}} {{.Ports}}' | grep -m1 -E "factorio.*${PORT}->27015/tcp" | awk '{print $1}')"
if [[ "${WORLD_RESET_BEFORE_RUN:-0}" == "1" ]]; then
  if [[ -z "${CONTAINER}" ]]; then
    echo "ERROR: cannot determine container for tcp/${PORT} to reset." >&2
    exit 1
  fi
  echo "Reset requested: restarting ${CONTAINER} before run..."
  docker restart "${CONTAINER}" >/dev/null
  sleep "${WORLD_RESET_WAIT_SECONDS:-8}"
fi

export FACTORIO_SERVER_ADDRESS="127.0.0.1"
export FACTORIO_SERVER_PORT="${PORT}"
export WORLD_PROFILE="${PROFILE}"
export SCREENSHOT_BACKEND="benchmark"
export LIVE_RENDER_PARALLEL="0"
export CATCHUP_RENDER_PARALLEL="1"
export CATCHUP_RENDER_TIMEOUT="900"
export CATCHUP_RENDER_RETRIES="1"
export CATCHUP_RENDER_TICKS="60"
export SKIP_WORLD_CHECK="0"

echo "Running video pipeline on ${FACTORIO_SERVER_ADDRESS}:${FACTORIO_SERVER_PORT} profile=${WORLD_PROFILE}"
echo "Backend=${SCREENSHOT_BACKEND} live_parallel=${LIVE_RENDER_PARALLEL} catchup_parallel=${CATCHUP_RENDER_PARALLEL} timeout=${CATCHUP_RENDER_TIMEOUT} retries=${CATCHUP_RENDER_RETRIES} ticks=${CATCHUP_RENDER_TICKS} reset=${WORLD_RESET_BEFORE_RUN:-0}"

exec python run_with_video.py
