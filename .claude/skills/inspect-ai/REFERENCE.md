# Inspect AI — Detailed API Reference

This file contains detailed reference material for the Inspect AI Log File API,
eval() function parameters, score editing, and advanced analysis patterns.

## eval() Full Signature

```python
from inspect_ai import eval

logs = eval(
    tasks,                    # str, list[str], Task, or list[Task]
    model="provider/model",   # Required unless INSPECT_EVAL_MODEL is set
    model_base_url=None,      # Optional base URL for model API
    model_roles=None,         # Dict of named roles: {"red_team": "openai/gpt-4o"}
    solver=None,              # Override task solver
    tags=None,                # Tags for this eval run
    metadata=None,            # Metadata dict for this eval run
    log_dir=None,             # Override log directory (default: ./logs)
    log_format="eval",        # "eval" (binary) or "json" (text)
    log_level="warning",      # Console log level
    log_images=True,          # Include base64 images in logs
    max_messages=None,        # Max messages per sample
    max_tokens=None,          # Max token usage per sample
    max_time=None,            # Max clock time (seconds) per sample
    max_working_time=None,    # Max working time (seconds) per sample
    max_samples=None,         # Max concurrent samples
    max_tasks=None,           # Max concurrent tasks
    max_subprocesses=None,    # Max concurrent subprocesses
    max_sandboxes=None,       # Max concurrent sandboxes
    max_connections=None,     # Max model API connections
    fail_on_error=True,       # True/False/float(proportion)/int(count)
    fail_on_error_end=False,  # Continue running, fail at end
    max_retries=0,            # Retry failed samples
    temperature=None,         # Model temperature
    top_p=None,               # Model top_p
    trace=False,              # Trace model interactions to terminal
    display="full",           # Display type
    approval=None,            # Tool approval policies
    sandbox_cleanup=True,     # Cleanup sandboxes after task
    log_samples=True,         # Log detailed sample info
)
```

## Log File API Functions

| Function | Description |
|----------|-------------|
| `list_eval_logs(log_dir, formats, filter, recursive, descending)` | List all eval logs at a location |
| `read_eval_log(path, header_only, resolve_attachments)` | Read an EvalLog from a file path |
| `read_eval_log_sample(path, id, epoch, resolve_attachments)` | Read a single sample |
| `read_eval_log_samples(path, all_samples_required)` | Generator yielding samples one at a time |
| `read_eval_log_sample_summaries(path)` | Read summary of all samples (fast) |
| `write_eval_log(log, location, format, if_match_etag)` | Write an EvalLog to a file |

## Score Editing

```python
from inspect_ai.log import read_eval_log, write_eval_log, edit_score, recompute_metrics
from inspect_ai.scorer import ScoreEdit, ProvenanceData

log = read_eval_log("my_eval.eval")

edit = ScoreEdit(
    value=0.95,
    explanation="Corrected scoring bug",
    provenance=ProvenanceData(
        author="username",
        reason="Model grader had a bug",
    )
)

edit_score(
    log=log,
    sample_id=log.samples[0].id,
    score_name="accuracy",
    edit=edit
)

write_eval_log(log)
```

### Batch edits with deferred metric recomputation

```python
edit_score(log, id1, "accuracy", edit1, recompute_metrics=False)
edit_score(log, id2, "accuracy", edit2, recompute_metrics=False)
recompute_metrics(log)
write_eval_log(log)
```

### Score history

```python
score = log.samples[0].scores["accuracy"]
print(f"Original: {score.history[0].value}")
print(f"Current: {score.value}")
print(f"Edits: {len(score.history)}")
```

## Filtering Samples via Summaries

```python
errors = []
for summary in read_eval_log_sample_summaries("path/to/log.eval"):
    if summary.error is not None:
        full = read_eval_log_sample("path/to/log.eval", summary.id, summary.epoch)
        errors.append(full)
```

## Extracting Tool Calls

```python
log = read_eval_log("path/to/log.eval")
for sample in log.samples:
    for msg in sample.messages:
        if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"Tool: {tc.function}, Args: {tc.arguments}")
```

## Analyzing Events/Transcript

```python
from inspect_ai.log import read_eval_log_sample, resolve_sample_attachments

sample = read_eval_log_sample("path/to/log.eval", id=1, resolve_attachments=True)

for event in sample.events:
    print(f"Event: {event.event}, Span: {event.span_id}")
    if event.event == "tool":
        print(f"  Tool: {event.function}, Result: {event.result[:200]}")
    elif event.event == "model":
        print(f"  Model output: {event.output.choices[0].message.content[:200]}")
```

## DataFrame API Details

```python
from inspect_ai.analysis import evals_df, samples_df, messages_df, events_df

# All accept: paths to log files, directories, or EvalLog objects
# Options: parallel=True (or int for worker count), quiet=True

df = samples_df("./logs", parallel=True, quiet=True)
```

## Summarize All Eval Results

```python
import os
from inspect_ai.log import list_eval_logs, read_eval_log

os.environ["INSPECT_LOG_DIR"] = "./logs"

for info in list_eval_logs():
    log = read_eval_log(info.name, header_only=True)
    if log.status == "success":
        print(f"Task: {log.eval.task}, Model: {log.eval.model}")
        for score in log.results.scores:
            print(f"  {score.name}: {score.metrics}")
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `INSPECT_LOG_DIR` | Override default log directory |
| `INSPECT_LOG_FORMAT` | Default log format (`eval` or `json`) |
| `INSPECT_LOG_LEVEL` | Console log level |
| `INSPECT_EVAL_MODEL` | Default model for evals |
| `INSPECT_EVAL_MAX_RETRIES` | Default max retries |
| `INSPECT_EVAL_MAX_CONNECTIONS` | Default max connections |
| `OPENROUTER_API_KEY` | API key for OpenRouter models |

## .env File Example

```
OPENROUTER_API_KEY=sk-or-v1-...
INSPECT_LOG_DIR=./logs
INSPECT_LOG_LEVEL=warning
INSPECT_EVAL_MAX_RETRIES=5
INSPECT_EVAL_MAX_CONNECTIONS=20
```

## Links

- Log File API docs: https://inspect.aisi.org.uk/eval-logs.html
- Python eval() API: https://inspect.aisi.org.uk/reference/inspect_ai.html
- DataFrame API: https://inspect.aisi.org.uk/dataframe.html
- Eval Sets: https://inspect.aisi.org.uk/eval-sets.html