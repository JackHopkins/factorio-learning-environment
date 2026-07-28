# DeepSeek microbenchmark runs

The inference evaluator uses DeepSeek's OpenAI-compatible chat-completions and
tool-calling API directly. The model receives only:

- the public task goal, objective, constraints, and compact FLE action reference;
- `factorio_observe_factory`;
- `factorio_execute_program`;
- the ordinary outputs and errors from those tools.

The privileged diagnostic packet is written after finalization for analysis and
is never placed in the model context.

## Preflight

Start the Factorio fleet and `factorio-envd`, then set the API key without
putting it on the command line:

```powershell
$env:DEEPSEEK_API_KEY = '...'
Invoke-RestMethod http://127.0.0.1:8172/v1/health
```

The default script model IDs follow the current DeepSeek API quick start. They
can be overridden with `-Models`.

## Recommended sequence

First run one attempt on the 11-task development split:

```powershell
.\integrations\deepseek\Invoke-DeepSeekBenchmark.ps1 `
  -Split development `
  -Attempts 1 `
  -ToolErrorRetries 0 `
  -OutputDirectory runtime/deepseek-calibration
```

Inspect costs, invalid-call rate, and trajectories. Then run the complete
21-task ready suite with three attempts:

```powershell
.\integrations\deepseek\Invoke-DeepSeekBenchmark.ps1 `
  -Attempts 3 `
  -ToolErrorRetries 0
```

## Retry policy

`-ToolErrorRetries N` grants up to `N` additional model turns after programs
that the engine reports as errors. Retry events:

- remain in the trajectory;
- retain their invalid-action penalty;
- do not consume the ordinary intervention budget;
- are included in invalid and retry rates;
- are not automatically replayed.

Factorio programs are not transactional. Statements executed before an error
may have changed the world, so a retry is an opportunity for the model to
inspect and repair—not a rollback.

Publish strict (`N=0`) and retry-assisted (`N>0`) runs separately. The summary
includes `retry_assisted_success_rate`, so assisted recoveries cannot be
mistaken for first-pass tool competence.

Do not enable `--cache-prompt` for the hosted API. That option is only for the
local llama.cpp server.
