# Factorio Ports (Only These)

For this workspace, use only the reserved Factorio ports below.

## TCP

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

## UDP

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

Do not use any other Factorio ports.

# World Profiles (Only These)

- `default_lab_scenario`
- `open_world`

Do not use any other world/scenario profile names.

# World Isolation

For the dedicated codex server on `41000`, use isolated mounts under `/tmp/factorio-agent-1-codex/*` for:

- `mods`
- `config`
- `scenarios`
- `saves`
- `script-output`

Do not bind these from `/tmp/factorio-verifier-cluster/*`.
