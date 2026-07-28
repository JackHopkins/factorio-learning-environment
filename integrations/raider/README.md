# Raider local-model evaluation

The first inference-only Factorio agent evaluation uses the existing
Tailscale/SSH route rather than exposing either service:

```text
ZeroRequiem
  Factorio Docker + factorio-envd (loopback)
  evaluation controller
        |
        | SSH local forward over Tailscale
        v
Raider
  llama.cpp :8080 (loopback)
  Qwen 35B MoE
```

The SSH alias `raider-codex` is supplied by the user's local SSH configuration.
No hostnames, keys, tokens, or Tailscale addresses are stored in this
repository.

## Preflight

With Factorio Docker running on ZeroRequiem and llama.cpp running on Raider:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\integrations\raider\Invoke-FactorioRaiderEval.ps1 `
  -Preflight
```

This starts a loopback-only SSH forward, starts `factorio-envd` if necessary,
checks both capability endpoints, resolves the live model ID, and exits without
generating tokens or leasing a Factorio environment.

## First rollout

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\integrations\raider\Invoke-FactorioRaiderEval.ps1 `
  -TaskId milestone_research_automation_v1 `
  -MaxTurns 8
```

Results and process logs are written under `runtime/raider-eval/` and ignored
by Git. Services created by the script are stopped in `finally`; pass
`-KeepServices` only for interactive debugging.

Raider's current 8K model context is handled by retaining complete recent
assistant/tool exchanges and a deterministic compact notebook of earlier
engine observations and action outcomes. Full result JSON is atomically
written as UTF-8 before any console summary is printed.

The Python loop in `fle.eval.remote_agent` is intentionally an inference
preflight. It exercises the same versioned `factorio-envd` lease, observation,
program, finalization, reward, and cleanup contract as Verifiers v1, but it is
not a substitute for Prime-RL's rollout and training machinery.
