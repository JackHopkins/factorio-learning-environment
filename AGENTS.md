# Factorio Port Reservation (Required)

These are the only Factorio ports reserved for this workspace/user. Do not use any other Factorio ports.

## Allowed TCP ports (RCON/game host mappings)

- `41000`
- `41001`
- `41002`
- `41003`
- `41004`
- `41005`
- `41006`
- `41007`
- `41008`
- `41009`

## Allowed UDP ports

- `46000`
- `46001`
- `46002`
- `46003`
- `46004`
- `46005`
- `46006`
- `46007`
- `46008`
- `46009`

## Rules

- Use only the ports above for Factorio-related runs, containers, and tooling.
- Do not use shared/default cluster ports (for example `27000-27005`, `28000`, `40100`, `40200`).
- If one of the reserved ports is occupied, stop and coordinate rather than switching to an unreserved port.
- Port isolation is not enough by itself: for `41000`, use only the isolated codex container mounts under `/tmp/factorio-agent-1-codex/*` for `mods/config/scenarios/saves/script-output`.

## Allowed World Profiles (Only These)

- `default_lab_scenario`
- `open_world`

Do not introduce or use any other world/scenario profile names in run tooling.

## Reliable Runbook: Real Screenshots + Video (Required)

Use this exact workflow for every run.

### 1) Run command (copy/paste)

Preferred (one command):

```bash
./run_video_reliable.sh 41000
```

Use one reserved TCP port from `41000-41009`.

Profile selection:

```bash
WORLD_PROFILE=open_world ./run_video_reliable.sh
WORLD_PROFILE=default_lab_scenario ./run_video_reliable.sh
```

If no port is passed, the wrapper auto-resolves a running server that matches `WORLD_PROFILE`.
For `WORLD_PROFILE=default_lab_scenario` on `41000`, the wrapper auto-runs `./ensure_codex_factorio_server.sh` to enforce isolated mounts and recreate the container if needed.

Fallback (explicit env form):

```bash
set -euo pipefail

FACTORIO_SERVER_ADDRESS=127.0.0.1 \
FACTORIO_SERVER_PORT=41000 \
SCREENSHOT_BACKEND=benchmark \
LIVE_RENDER_PARALLEL=0 \
CATCHUP_RENDER_PARALLEL=1 \
CATCHUP_RENDER_TIMEOUT=900 \
CATCHUP_RENDER_RETRIES=1 \
CATCHUP_RENDER_TICKS=60 \
python run_with_video.py
```

Note: `python run_with_video.py` now defaults to the reliable profile (`benchmark`, timeout `900`, retries `1`, ticks `60`, default port `41000`), but the wrapper script is preferred because it enforces reserved-port checks and overrides conflicting env vars.

### 2) Mandatory constraints

- Do not set `SKIP_WORLD_CHECK=1` (world preflight must stay enabled).
- Required model for this workflow is `claude-sonnet-4-6` (do not run with other models).
- Do not use `SCREENSHOT_BACKEND=render_simple` for production runs.
- Do not set `CATCHUP_RENDER_TICKS` or `RENDER_TICKS` below `60`.
- Keep renderer parallelism at `1` unless a soak test proves higher values are stable.

### 3) Verify artifacts after run

```bash
LATEST="$(ls -1 .fle/run_screenshots | sed 's/^v//' | sort -n | tail -1)"
echo "latest version: v${LATEST}"

ls -1 ".fle/run_screenshots/v${LATEST}"/step_*.png | wc -l
file ".fle/run_screenshots/v${LATEST}/step_000.png"
stat -c '%n %s bytes' ".fle/run_screenshots/v${LATEST}/run.mp4"
```

Expected:

- `31` PNG files (`step_000.png` through `step_030.png`) for the default 30-step run.
- PNG resolution is `1920 x 1080`.
- `run.mp4` exists and size is non-zero.

### 4) Recovery if screenshots/video are missing

Re-render directly from saved zips for that version:

```bash
RENDER_MAX_PARALLEL=1 \
RENDER_TIMEOUT=900 \
RENDER_RETRIES=1 \
RENDER_TICKS=60 \
python render_saves.py /tmp/fle-run-saves/v<version> .fle/run_screenshots/v<version>
```

Then re-run the verification commands in step 3.
