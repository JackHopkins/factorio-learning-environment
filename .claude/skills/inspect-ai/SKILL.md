---
name: inspect-ai
description: Use this skill whenever asked to run Inspect AI evaluations, analyze .eval or .json log files, read trajectory data, or work with the Inspect AI Python API. Triggers include mentions of "inspect eval", ".eval files", "eval logs", "trajectory", "EvalLog", "samples", "scores", or references to the inspect_ai Python package. Also use when asked to analyze agent behavior from evaluation runs, extract scores/metrics, retry failed evals, or compare evaluation results programmatically.
---

# Inspect AI — Running Evaluations & Analyzing Log Files

This skill covers two core workflows with the [Inspect AI](https://inspect.aisi.org.uk/) framework:

1. **Running evaluations** using the Python API (`eval()`, `eval_set()`, `eval_retry()`)
2. **Reading and analyzing `.eval` / `.json` log files** using the Log File API

Reference documentation:
- Eval from Python: https://inspect.aisi.org.uk/index.html#eval-from-python
- Log File API: https://inspect.aisi.org.uk/eval-logs.html#sec-log-file-api
- Python API reference: https://inspect.aisi.org.uk/reference/inspect_ai.html
- Log module reference: https://inspect.aisi.org.uk/reference/inspect_ai.log.html

---

## Installation

```bash
pip install inspect-ai
```

Provider-specific packages are also needed (e.g. `pip install openai`, `pip install anthropic`). API keys must be set as environment variables or in a `.env` file:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
INSPECT_LOG_DIR=./logs
```

For OpenRouter, set:
```
OPENROUTER_API_KEY=...
```

---

## Part 1: Running Evaluations from Python

### Basic `eval()` Usage

```python
from inspect_ai import eval

# Run a task file against a model — returns list[EvalLog]
logs = eval("path/to/task.py", model="openai/gpt-4o")

# Run a specific @task function from a file
logs = eval("path/to/task.py@my_task_name", model="anthropic/claude-sonnet-4-0")

# Run with OpenRouter
logs = eval("agents/task.py@game_1830_multi_agent", model="openrouter/openai/gpt-5-mini")
```

### Running a Task Object Directly

```python
from inspect_ai import eval
from my_tasks import my_task

# Pass a Task instance directly
logs = eval(my_task(), model="openai/gpt-4o")

# Multiple tasks
logs = eval([task_a(), task_b()], model="openai/gpt-4o")
```

### Common `eval()` Parameters

```python
logs = eval(
    tasks="task.py",              # str, list[str], Task, or list[Task]
    model="openai/gpt-4o",       # Model string (provider/model-name)
    log_dir="./my-logs",         # Where to write logs (default: ./logs)
    log_format="eval",           # "eval" (binary, default) or "json"
    max_connections=10,           # Max concurrent API connections
    max_samples=None,             # Max concurrent samples (default: max_connections + 1)
    max_tasks=None,               # Max concurrent tasks
    fail_on_error=True,           # True/False/float(proportion)/int(count)
    log_level="warning",          # "debug","http","sandbox","info","warning","error","critical"
    tags=["experiment-1"],        # Tags for this eval run
    metadata={"version": "2.0"}, # Arbitrary metadata
)
```

### `eval()` Return Value

`eval()` returns a `list[EvalLog]` — one per task evaluated. Always check status:

```python
logs = eval("task.py", model="openai/gpt-4o")
for log in logs:
    if log.status == "success":
        print(f"Results: {log.results}")
        print(f"Samples: {len(log.samples)}")
    elif log.status == "error":
        print(f"Error: {log.error}")
```

### Running Eval Sets

```python
from inspect_ai import eval_set

success, logs = eval_set(
    tasks=["task_a.py", "task_b.py"],
    model=["openai/gpt-4o", "anthropic/claude-sonnet-4-0"],
    log_dir="logs-run-42",       # Required — dedicated dir for this set
)
```

### Retrying Failed Evals

```python
from inspect_ai import eval_retry

# Retry from a log file path
eval_retry("logs/2024-05-29T12-38-43_math_Gprr29Mv.eval")

# Retry from an EvalLog object
log = eval("task.py", model="openai/gpt-4o")[0]
if log.status != "success":
    eval_retry(log, max_connections=3)
```

### CLI Equivalents (for reference)

```bash
# Basic eval
inspect eval task.py --model openai/gpt-4o

# Specific task function
inspect eval agents/task.py@game_1830_multi_agent --model openrouter/openai/gpt-5-mini

# With options
inspect eval task.py --model openai/gpt-4o --log-dir ./my-logs --max-connections 20

# Retry
inspect eval-retry logs/2024-05-29T12-38-43_math_Gprr29Mv.eval

# Eval set
inspect eval-set task_a.py task_b.py --model openai/gpt-4o --log-dir logs-run-42
```

---

## Part 2: Analyzing Log Files (Log File API)

### Key Imports

```python
from inspect_ai.log import (
    # Reading
    read_eval_log,
    read_eval_log_sample,
    read_eval_log_samples,
    read_eval_log_sample_summaries,
    list_eval_logs,
    # Writing
    write_eval_log,
    # Editing
    edit_score,
    recompute_metrics,
    # Attachments
    resolve_sample_attachments,
    # Types
    EvalLog,
    EvalLogInfo,
    EvalSample,
    EvalSampleSummary,
)
```

### Log File Formats

| Type    | Description |
|---------|-------------|
| `.eval` | Binary format — compressed, fast, incremental sample access. Default since v0.3.46. |
| `.json` | Text JSON — larger, slower for big files, but human-readable. |

**Always use the Python Log File API** to read/write logs. Never parse the JSON directly — the API handles both formats transparently.

### Reading a Full Log

```python
log = read_eval_log("logs/2024-05-29T12-38-43_math_Gprr29Mv.eval")

# Check status first
assert log.status == "success"

# Access top-level fields
print(log.version)       # int — file format version (currently 2)
print(log.status)        # "started" | "success" | "cancelled" | "error"
print(log.eval)          # EvalSpec — task, model, creation time, etc.
print(log.plan)          # EvalPlan — solvers and generation config
print(log.results)       # EvalResults — aggregate scores and metrics
print(log.stats)         # EvalStats — token usage statistics
print(log.error)         # EvalError | None — traceback if status == "error"
print(log.samples)       # list[EvalSample] — all samples with inputs/outputs/scores
print(log.reductions)    # list[EvalSampleReduction] — for multi-epoch evals
print(log.location)      # URI where log was read from / written to
```

### EvalLog Fields Reference

| Field        | Type                       | Description |
|--------------|----------------------------|-------------|
| `version`    | `int`                      | File format version (currently 2) |
| `status`     | `str`                      | `"started"`, `"success"`, `"cancelled"`, or `"error"` |
| `eval`       | `EvalSpec`                 | Task name, model, creation time, dataset info, config |
| `plan`       | `EvalPlan`                 | Solver list and model generation config |
| `results`    | `EvalResults`              | Aggregate scores computed by scorer metrics |
| `stats`      | `EvalStats`                | Model usage (input/output tokens) |
| `error`      | `EvalError`                | Error info + traceback (if `status == "error"`) |
| `samples`    | `list[EvalSample]`         | Each sample: input, output, target, messages, events, score |
| `reductions` | `list[EvalSampleReduction]`| Reductions for multi-epoch evaluations |
| `location`   | `str`                      | URI the log was read from |

### Reading Header Only (Fast — No Samples)

For large logs (multi-GB), read only metadata + aggregate scores:

```python
log_header = read_eval_log("path/to/log.eval", header_only=True)
# log_header.samples will be empty, but .results, .eval, .plan, .stats are populated
```

### Reading Sample Summaries (Efficient Filtering)

```python
summaries = read_eval_log_sample_summaries("path/to/log.eval")
# Returns list[EvalSampleSummary] — lightweight: no full messages/events
# Includes: id, epoch, input (images removed), target, scores (value only), error, metadata

for s in summaries:
    print(f"Sample {s.id}: score={s.scores}, error={s.error}")
```

### Reading Individual Samples

```python
# Read a single sample by ID
sample = read_eval_log_sample("path/to/log.eval", id=42)

# Read a single sample by ID and epoch
sample = read_eval_log_sample("path/to/log.eval", id=42, epoch=1)
```

### Streaming All Samples (Memory-Efficient)

```python
# Generator — one sample in memory at a time
for sample in read_eval_log_samples("path/to/log.eval"):
    print(f"Sample {sample.id}: {sample.scores}")

# For logs with errors, pass all_samples_required=False
for sample in read_eval_log_samples("path/to/log.eval", all_samples_required=False):
    ...
```

### Listing All Logs in a Directory

```python
import os

# Uses INSPECT_LOG_DIR env var or defaults to ./logs
logs = list_eval_logs()

# Or specify a directory
logs = list_eval_logs(log_dir="./my-experiment-logs")

# Filter by status
logs = list_eval_logs(filter=lambda log: log.status == "success")

# Non-recursive
logs = list_eval_logs(recursive=False)

# Returns list[EvalLogInfo] with metadata about each log file
for info in logs:
    print(info)
```

### Analyzing Samples — Common Patterns

```python
log = read_eval_log("path/to/log.eval")

# 1. Extract all scores
for sample in log.samples:
    for scorer_name, score in sample.scores.items():
        print(f"Sample {sample.id} [{scorer_name}]: {score.value}")

# 2. Get the full message history for a sample
for sample in log.samples:
    for msg in sample.messages:
        print(f"  [{msg.role}]: {msg.content[:100]}...")

# 3. Inspect events/transcript for agent behavior
for sample in log.samples:
    for event in sample.events:
        print(f"  Event: {event}")

# 4. Filter samples by score
failed = [s for s in log.samples if s.scores.get("accuracy", None) and s.scores["accuracy"].value == 0]
passed = [s for s in log.samples if s.scores.get("accuracy", None) and s.scores["accuracy"].value == 1]

# 5. Token usage
print(f"Total input tokens: {log.stats.input_tokens}")
print(f"Total output tokens: {log.stats.output_tokens}")
```

### Resolving Attachments

Large content (images, etc.) is de-duplicated and stored as attachments. Resolve them when you need the actual content:

```python
from inspect_ai.log import resolve_sample_attachments

sample = read_eval_log_sample("path/to/log.eval", id=42, resolve_attachments=True)
# OR
sample = resolve_sample_attachments(sample)
```

You typically only need this if:
- You want base64 images from `input` or `messages`
- You are directly reading the `events` transcript

### Editing Scores

```python
from inspect_ai.log import read_eval_log, write_eval_log, edit_score
from inspect_ai.scorer import ScoreEdit, ProvenanceData

log = read_eval_log("my_eval.eval")

edit = ScoreEdit(
    value=0.95,
    explanation="Corrected model grader bug",
    provenance=ProvenanceData(
        author="jack",
        reason="Scoring bug in original grader",
    )
)

edit_score(
    log=log,
    sample_id=log.samples[0].id,
    score_name="accuracy",
    edit=edit,
)

# Don't forget to write back!
write_eval_log(log)
```

### Batch Editing (Defer Metric Recomputation)

```python
from inspect_ai.log import recompute_metrics

edit_score(log, sample_id_1, "accuracy", edit1, recompute_metrics=False)
edit_score(log, sample_id_2, "accuracy", edit2, recompute_metrics=False)
recompute_metrics(log)
write_eval_log(log)
```

### Writing / Copying Logs

```python
# Write back to original location
write_eval_log(log)

# Write to a new location
write_eval_log(log, location="./backup/my_log.eval")
```

---

## Part 3: Dataframes API (for Structured Analysis)

For pandas-style analysis, use the `inspect_ai.analysis` module:

```python
from inspect_ai.analysis import evals_df, samples_df, messages_df, events_df

# Get a DataFrame of all evals in a log directory
df_evals = evals_df(log_dir="./logs")

# Get a DataFrame of all samples from a specific log
df_samples = samples_df("path/to/log.eval")

# Get messages from samples
df_messages = messages_df("path/to/log.eval")

# Get events from samples
df_events = events_df("path/to/log.eval")
```

---

## Part 4: CLI Log Commands (Non-Python Interop)

```bash
# List all logs
inspect log list --json --log-dir ./logs

# List only successful logs
inspect log list --json --status success

# Dump a log as plain JSON (works for both .eval and .json formats)
inspect log dump path/to/log.eval

# Convert between formats
inspect log convert source.json --to eval --output-dir log-output
inspect log convert logs/ --to eval --output-dir logs-eval

# Get JSON schema
inspect log schema

# Launch the log viewer
inspect view
```

---

## Common Workflow: Run → Analyze

```python
from inspect_ai import eval
from inspect_ai.log import read_eval_log

# 1. Run the evaluation
logs = eval("agents/task.py@game_1830_multi_agent", model="openrouter/openai/gpt-5-mini")

# 2. Check results
log = logs[0]
if log.status == "success":
    print(f"Results: {log.results}")

    # 3. Iterate over samples
    for sample in log.samples:
        print(f"\nSample {sample.id}:")
        print(f"  Input: {str(sample.input)[:200]}")
        print(f"  Target: {sample.target}")
        print(f"  Scores: {sample.scores}")

        # 4. Inspect agent trajectory (messages)
        for msg in sample.messages:
            role = msg.role
            content = str(msg.content)[:300]
            print(f"  [{role}]: {content}")

# 5. Or re-read from disk later
log = read_eval_log(log.location)
```

---

## Environment Variables Reference

| Variable                          | Description |
|-----------------------------------|-------------|
| `INSPECT_LOG_DIR`                 | Default log directory (default: `./logs`) |
| `INSPECT_LOG_FORMAT`              | Default log format: `eval` or `json` |
| `INSPECT_LOG_LEVEL`               | Console log level |
| `INSPECT_LOG_LEVEL_TRANSCRIPT`    | Transcript log level |
| `INSPECT_EVAL_MODEL`              | Default model for evals |
| `INSPECT_EVAL_MAX_RETRIES`        | Default max retries |
| `INSPECT_EVAL_MAX_CONNECTIONS`    | Default max connections |
| `INSPECT_EVAL_LOG_IMAGES`         | Whether to log base64 images |
| `INSPECT_EVAL_LOG_FILE_PATTERN`   | Log filename pattern (e.g. `{task}_{model}_{id}`) |
| `OPENAI_API_KEY`                  | OpenAI API key |
| `ANTHROPIC_API_KEY`               | Anthropic API key |
| `OPENROUTER_API_KEY`              | OpenRouter API key |
| `GOOGLE_API_KEY`                  | Google API key |

---

## Tips

- **Always check `log.status == "success"`** before accessing samples or results.
- **Use `header_only=True`** when you only need aggregate metrics — avoids loading potentially gigabytes of sample data.
- **Use `read_eval_log_samples()` generator** for memory-efficient iteration over large logs.
- **Use `read_eval_log_sample_summaries()`** when you only need scores and metadata, not full message histories.
- **Resolve attachments only when needed** — most analysis doesn't require the raw image/content data.
- **The `.eval` format is strongly preferred** over `.json` — it's ~8x smaller and supports incremental sample access.
- **`eval()` returns `EvalLog` objects in memory** — you don't need to re-read from disk unless you want to analyze logs from a previous session.
- **Use `eval_retry()`** for transient failures (rate limits, network errors) — it preserves already-completed samples.