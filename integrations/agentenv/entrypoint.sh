#!/bin/sh
set -eu

FACTORIO_LOG="${FACTORIO_LOG:-/tmp/factorio-current.log}"
ENVD_LOG="${ENVD_LOG:-/tmp/factorio-envd.log}"
RCON_PORT="${FACTORIO_RCON_PORT:-27015}"
ENVD_PORT="${FLE_GUEST_ENVD_PORT:-8172}"
LEASE_TTL="${FLE_GUEST_LEASE_TTL:-86400}"

# The training image intentionally runs the vanilla base game. The build
# references the official headless assets through the upstream image; it does
# not make Space Age capabilities part of this benchmark.
rm -rf \
  /opt/factorio/data/elevated-rails \
  /opt/factorio/data/quality \
  /opt/factorio/data/space-age

/opt/factorio/bin/x64/factorio \
  --start-server-load-scenario default_lab_scenario \
  --port 34197 \
  --rcon-port "${RCON_PORT}" \
  --rcon-password factorio \
  --server-settings /opt/factorio/config/server-settings.json \
  --map-gen-settings /opt/factorio/config/map-gen-settings.json \
  --map-settings /opt/factorio/config/map-settings.json \
  --server-adminlist /opt/factorio/config/server-adminlist.json \
  --server-banlist /opt/factorio/config/server-banlist.json \
  --server-whitelist /opt/factorio/config/server-whitelist.json \
  --use-server-whitelist \
  --mod-directory /opt/factorio/mods \
  >"${FACTORIO_LOG}" 2>&1 &
factorio_pid=$!

cleanup() {
  kill "${envd_pid:-}" "${factorio_pid}" 2>/dev/null || true
  wait "${envd_pid:-}" "${factorio_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python - "${RCON_PORT}" "${factorio_pid}" <<'PY'
import os
import socket
import sys
import time

port = int(sys.argv[1])
factorio_pid = int(sys.argv[2])
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    try:
        os.kill(factorio_pid, 0)
    except OSError as exc:
        raise SystemExit("Factorio exited before RCON became ready") from exc
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            break
    except OSError:
        time.sleep(0.25)
else:
    raise SystemExit("Timed out waiting for Factorio RCON")
PY

fle-envd \
  --runtime local \
  --host 0.0.0.0 \
  --port "${ENVD_PORT}" \
  --factorio-address 127.0.0.1 \
  --rcon-ports "${RCON_PORT}" \
  --lease-ttl "${LEASE_TTL}" \
  >"${ENVD_LOG}" 2>&1 &
envd_pid=$!

while kill -0 "${factorio_pid}" 2>/dev/null && kill -0 "${envd_pid}" 2>/dev/null; do
  sleep 1
done

echo "Factorio or factorio-envd exited unexpectedly" >&2
tail -n 100 "${FACTORIO_LOG}" >&2 || true
tail -n 100 "${ENVD_LOG}" >&2 || true
exit 1
