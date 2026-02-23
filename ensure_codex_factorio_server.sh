#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROFILE="${1:-default_lab_scenario}"
TCP_PORT="${2:-41000}"
UDP_PORT="${3:-$((46000 + TCP_PORT - 41000))}"

if [[ "${PROFILE}" != "default_lab_scenario" && "${PROFILE}" != "open_world" ]]; then
  echo "ERROR: profile must be 'default_lab_scenario' or 'open_world'." >&2
  exit 1
fi
if ! [[ "${TCP_PORT}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: tcp port must be numeric (got '${TCP_PORT}')." >&2
  exit 1
fi
if ! [[ "${UDP_PORT}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: udp port must be numeric (got '${UDP_PORT}')." >&2
  exit 1
fi

CONTAINER_NAME="${FACTORIO_CONTAINER_NAME:-factorio-agent-1-codex-server}"
BASE_DIR="${FACTORIO_BASE_DIR:-/tmp/factorio-agent-1-codex}"
IMAGE="${FACTORIO_IMAGE:-factoriotools/factorio:1.1.110}"
START_WAIT_SECONDS="${FACTORIO_START_WAIT_SECONDS:-6}"

mkdir -p \
  "${BASE_DIR}/config" \
  "${BASE_DIR}/mods" \
  "${BASE_DIR}/scenarios" \
  "${BASE_DIR}/saves" \
  "${BASE_DIR}/.fle/data/_screenshots"
BASE_DIR="$(cd "${BASE_DIR}" && pwd)"

seed_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ -d "${src}" ]]; then
    rsync -rlt --ignore-existing "${src}/" "${dst}/"
  fi
}

# Seed baseline config/mods from cluster assets if local copies are missing.
if [[ ! -f "${BASE_DIR}/config/server-settings.json" ]]; then
  seed_if_missing "/tmp/factorio-verifier-cluster/config" "${BASE_DIR}/config"
fi
if [[ ! -d "${BASE_DIR}/mods/verifier" ]]; then
  seed_if_missing "/tmp/factorio-verifier-cluster/mods" "${BASE_DIR}/mods"
fi

# Ensure both scenario profiles exist in the isolated tree.
if [[ -d "${ROOT_DIR}/fle/cluster/scenarios/default_lab_scenario" ]]; then
  mkdir -p "${BASE_DIR}/scenarios/default_lab_scenario"
  rsync -rlt "${ROOT_DIR}/fle/cluster/scenarios/default_lab_scenario/" "${BASE_DIR}/scenarios/default_lab_scenario/"
fi
if [[ -d "${ROOT_DIR}/fle/cluster/scenarios/open_world" ]]; then
  mkdir -p "${BASE_DIR}/scenarios/open_world"
  rsync -rlt "${ROOT_DIR}/fle/cluster/scenarios/open_world/" "${BASE_DIR}/scenarios/open_world/"
fi
if [[ ! -d "${BASE_DIR}/scenarios/default_lab_scenario" ]]; then
  seed_if_missing "/tmp/factorio-verifier-cluster/scenarios" "${BASE_DIR}/scenarios"
fi

choose_save_file() {
  local profile="$1"
  local tcp_port="$2"
  local base_dir="$3"
  local candidate
  local -a candidates

  if [[ "${profile}" == "default_lab_scenario" ]]; then
    candidates=(
      "${CODEX_DEFAULT_LAB_SAVE:-codex_seed_${tcp_port}.zip}"
      "codex_seed_41000.zip"
      "default_lab_scenario.zip"
      "seed_from_cluster.zip"
    )
  else
    candidates=(
      "${CODEX_OPEN_WORLD_SAVE:-open_world_seed_${tcp_port}.zip}"
      "open_world_seed_41000.zip"
      "open_world.zip"
    )
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -f "${base_dir}/saves/${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  # Pull a baseline scenario save if available.
  if [[ "${profile}" == "default_lab_scenario" && -f "/tmp/factorio-verifier-cluster/saves/default_lab_scenario.zip" ]]; then
    cp -n "/tmp/factorio-verifier-cluster/saves/default_lab_scenario.zip" "${base_dir}/saves/default_lab_scenario.zip" || true
    echo "default_lab_scenario.zip"
    return 0
  fi
  if [[ "${profile}" == "open_world" && -f "/tmp/factorio-verifier-cluster/saves/open_world.zip" ]]; then
    cp -n "/tmp/factorio-verifier-cluster/saves/open_world.zip" "${base_dir}/saves/open_world.zip" || true
    echo "open_world.zip"
    return 0
  fi

  return 1
}

if ! SAVE_FILE="$(choose_save_file "${PROFILE}" "${TCP_PORT}" "${BASE_DIR}")"; then
  echo "ERROR: no save file found for profile=${PROFILE} in ${BASE_DIR}/saves." >&2
  echo "       Add a seed save (for example codex_seed_${TCP_PORT}.zip or default_lab_scenario.zip)." >&2
  exit 1
fi

mount_source() {
  local container_name="$1"
  local dst="$2"
  docker inspect "${container_name}" --format '{{json .Mounts}}' \
    | jq -r --arg dst "${dst}" '.[] | select(.Destination==$dst) | .Source' \
    | head -n1
}

needs_recreate=1
if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  ports_json="$(docker inspect "${CONTAINER_NAME}" --format '{{json .NetworkSettings.Ports}}')"
  host_tcp="$(echo "${ports_json}" | jq -r '."27015/tcp"[0].HostPort // empty')"
  host_udp="$(echo "${ports_json}" | jq -r '."34197/udp"[0].HostPort // empty')"

  isolated=1
  for dst in \
    /opt/factorio/mods \
    /opt/factorio/config \
    /opt/factorio/scenarios \
    /opt/factorio/saves \
    /opt/factorio/script-output; do
    src="$(mount_source "${CONTAINER_NAME}" "${dst}")"
    if [[ -z "${src}" || "${src}" != "${BASE_DIR}"* ]]; then
      isolated=0
      break
    fi
  done

  if [[ "${isolated}" == "1" && "${host_tcp}" == "${TCP_PORT}" && "${host_udp}" == "${UDP_PORT}" ]]; then
    needs_recreate=0
    running="$(docker inspect "${CONTAINER_NAME}" --format '{{.State.Running}}')"
    if [[ "${running}" != "true" ]]; then
      docker start "${CONTAINER_NAME}" >/dev/null
      sleep "${START_WAIT_SECONDS}"
    fi
  fi
fi

if (( needs_recreate == 1 )); then
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker run -d \
    --name "${CONTAINER_NAME}" \
    --entrypoint /opt/factorio/bin/x64/factorio \
    -p "${TCP_PORT}:27015/tcp" \
    -p "${UDP_PORT}:34197/udp" \
    -v "${BASE_DIR}/scenarios:/opt/factorio/scenarios" \
    -v "${BASE_DIR}/.fle/data/_screenshots:/opt/factorio/script-output" \
    -v "${BASE_DIR}/saves:/opt/factorio/saves" \
    -v "${BASE_DIR}/mods:/opt/factorio/mods" \
    -v "${BASE_DIR}/config:/opt/factorio/config" \
    "${IMAGE}" \
    --start-server "/opt/factorio/saves/${SAVE_FILE}" \
    --port 34197 \
    --rcon-port 27015 \
    --rcon-password factorio \
    --server-settings /opt/factorio/config/server-settings.json \
    --map-gen-settings /opt/factorio/config/map-gen-settings.json \
    --map-settings /opt/factorio/config/map-settings.json \
    --server-adminlist /opt/factorio/config/server-adminlist.json \
    --server-banlist /opt/factorio/config/server-banlist.json \
    --server-whitelist /opt/factorio/config/server-whitelist.json \
    --use-server-whitelist \
    --mod-directory /opt/factorio/mods \
    >/dev/null
  sleep "${START_WAIT_SECONDS}"
fi

echo "Ensured isolated container ${CONTAINER_NAME} profile=${PROFILE} tcp=${TCP_PORT} udp=${UDP_PORT} save=${SAVE_FILE}"
