# Weights & Biases Analysis — Detailed API Reference

This file contains detailed reference material for the W&B Python API, including complete function signatures, filter operators, object properties, and advanced patterns.

---

## wandb.Api() Full Signature

```python
import wandb

api = wandb.Api(
    api_key=None,        # API key (default: from env or ~/.netrc)
    timeout=None,        # Request timeout in seconds (default: 60)
    overrides=None,      # Dict of config overrides
)
```

**Returns:** `wandb.Api` object for querying runs, artifacts, and sweeps.

**Authentication Priority:**
1. `api_key` parameter
2. `WANDB_API_KEY` environment variable
3. `~/.netrc` file (from `wandb login`)

---

## api.runs() Complete Reference

```python
runs = api.runs(
    path,                # Project path (str): "entity/project" or "project"
    filters=None,        # MongoDB-style filter dict
    order="-created_at", # Sort order: "+field" (asc) or "-field" (desc)
    per_page=50,         # Results per page (max 1000)
    include_sweeps=True, # Include sweep runs
    include_tags=True,   # Include run tags
)
```

**Returns:** `wandb.apis.public.Runs` object (iterable list of Run objects)

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | Project path: "entity/project" or just "project" |
| `filters` | dict | None | MongoDB-style query filters |
| `order` | str | "-created_at" | Sort field with +/- prefix |
| `per_page` | int | 50 | Pagination size (1-1000) |
| `include_sweeps` | bool | True | Include runs from sweeps |
| `include_tags` | bool | True | Load run tags |

**Examples:**

```python
# Basic usage
runs = api.runs("factorio/takka-qwen3-8b")

# With filters
runs = api.runs("factorio/takka-qwen3-8b", filters={
    "state": "finished",
    "config.learning_rate": {"$gte": 1e-5}
})

# Custom sort order
runs = api.runs("factorio/takka-qwen3-8b", order="+summary_metrics.eval/loss")
```

---

## Filter Syntax Reference

W&B uses MongoDB-style query operators for filtering runs.

### Equality Operators

```python
# Exact match (implicit $eq)
filters = {"state": "finished"}
filters = {"config.model": "qwen3-4b"}

# Explicit equality
filters = {"state": {"$eq": "finished"}}

# Not equal
filters = {"state": {"$ne": "crashed"}}
```

### Comparison Operators

```python
# Greater than
filters = {"config.learning_rate": {"$gt": 1e-5}}

# Greater than or equal
filters = {"config.learning_rate": {"$gte": 1e-5}}

# Less than
filters = {"summary_metrics.eval/loss": {"$lt": 2.0}}

# Less than or equal
filters = {"summary_metrics.eval/loss": {"$lte": 2.0}}
```

### Array Operators

```python
# Value in list
filters = {"state": {"$in": ["finished", "running"]}}

# Value not in list
filters = {"state": {"$nin": ["crashed", "failed"]}}
```

### String Operators

```python
# Regex match (case-sensitive)
filters = {"config.model": {"$regex": "qwen3.*"}}

# Case-insensitive regex
filters = {"display_name": {"$regex": "(?i)experiment"}}
```

### Existence Operators

```python
# Field exists (not None)
filters = {"summary_metrics.eval/loss": {"$exists": True}}

# Field does not exist or is None
filters = {"summary_metrics.eval/loss": {"$exists": False}}
```

### Date Filtering

```python
# Created after date
filters = {"created_at": {"$gt": "2026-01-01"}}

# Created in date range
filters = {
    "created_at": {
        "$gte": "2026-01-01",
        "$lt": "2026-02-01"
    }
}

# Updated recently (last 24 hours)
from datetime import datetime, timedelta
yesterday = (datetime.now() - timedelta(days=1)).isoformat()
filters = {"updated_at": {"$gt": yesterday}}
```

### Complex Queries (AND/OR)

```python
# Multiple conditions (implicit AND)
filters = {
    "state": "finished",
    "config.learning_rate": {"$gte": 1e-5},
    "summary_metrics.eval/loss": {"$lt": 2.0}
}

# OR conditions (use $or)
filters = {
    "$or": [
        {"state": "finished"},
        {"state": "running"}
    ]
}

# Complex nested query
filters = {
    "state": "finished",
    "$or": [
        {"config.learning_rate": {"$gte": 5e-5}},
        {"config.batch_size": {"$gte": 16}}
    ],
    "summary_metrics.eval/loss": {"$exists": True}
}
```

### Filter on Nested Config

```python
# Nested config values
filters = {"config.model_config.hidden_size": 768}

# Nested summary metrics
filters = {"summary_metrics.eval/bleu": {"$gt": 0.5}}
```

---

## Run Object Properties

A `Run` object represents a single W&B run with the following properties:

### Basic Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | str | Unique run ID (e.g., "abc123") |
| `name` | str | Run display name |
| `display_name` | str | Alias for name |
| `entity` | str | W&B entity (username or team) |
| `project` | str | Project name |
| `state` | str | Run state: "running", "finished", "crashed", "failed" |
| `url` | str | Full W&B URL to run page |
| `path` | list | [entity, project, run_id] |

### Timing Properties

| Property | Type | Description |
|----------|------|-------------|
| `created_at` | str | ISO timestamp when run was created |
| `updated_at` | str | ISO timestamp of last update |
| `start_time` | datetime | Run start time |
| `end_time` | datetime | Run end time (None if running) |

### Configuration & Metadata

| Property | Type | Description |
|----------|------|-------------|
| `config` | dict | Hyperparameters and config values |
| `summary` | dict | Final metric values |
| `tags` | list | List of tag strings |
| `notes` | str | Run description/notes |
| `group` | str | Run group name |
| `job_type` | str | Job type label |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `history()` | DataFrame | Metric history over time |
| `files()` | list | List of uploaded files |
| `file()` | File | Get specific file by name |
| `logged_artifacts()` | list | Artifacts logged by this run |
| `used_artifacts()` | list | Artifacts used by this run |
| `update()` | None | Update run metadata |
| `delete()` | None | Delete the run |

### Property Access Examples

```python
run = api.run("factorio/takka-qwen3-8b/abc123")

# Basic info
print(f"ID: {run.id}")
print(f"Name: {run.name}")
print(f"State: {run.state}")
print(f"URL: {run.url}")

# Timing
print(f"Created: {run.created_at}")
print(f"Duration: {run.end_time - run.start_time}")

# Config (safe access with get)
lr = run.config.get("learning_rate")
batch_size = run.config.get("batch_size", 8)  # Default if missing

# Summary metrics
final_loss = run.summary.get("eval/loss")
total_steps = run.summary.get("train/global_step")

# Tags
if "production" in run.tags:
    print("This is a production run")
```

---

## run.history() Full Signature

```python
history = run.history(
    samples=500,         # Max samples to return (0 = all)
    keys=None,           # List of metric keys to fetch (None = all)
    x_axis="_step",      # X-axis column name
    pandas=True,         # Return as pandas DataFrame
    stream="default",    # Stream type: "default" or "system"
)
```

**Returns:** `pandas.DataFrame` (if `pandas=True`) or `list[dict]` (if `pandas=False`)

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `samples` | int | 500 | Max samples (0 = unlimited, use with caution) |
| `keys` | list[str] | None | Specific metrics to fetch (faster than all) |
| `x_axis` | str | "_step" | X-axis column (usually "_step" or "_runtime") |
| `pandas` | bool | True | Return DataFrame vs list of dicts |
| `stream` | str | "default" | "default" for metrics, "system" for system metrics |

**DataFrame Columns:**

- `_step` — Global training step
- `_runtime` — Elapsed time in seconds
- `_timestamp` — Unix timestamp
- `{metric_name}` — Logged metrics (may have NaN for sparse metrics)

**Examples:**

```python
# Get all metrics (default)
history = run.history()

# Get specific metrics only (faster)
history = run.history(keys=["loss", "eval/loss", "learning_rate"])

# Get all data points (no sampling)
history = run.history(samples=0)

# Sample large history
history = run.history(samples=1000)

# Use runtime as x-axis
history = run.history(x_axis="_runtime")

# Get as list of dicts
history = run.history(pandas=False)

# System metrics (GPU, CPU, memory)
system = run.history(stream="system")
```

**Working with Sparse Metrics:**

Eval metrics are only logged periodically and contain NaN values:

```python
history = run.history(keys=["loss", "eval/loss", "_step"])

# Separate train and eval (remove NaN)
train_loss = history[["_step", "loss"]].dropna()
eval_loss = history[["_step", "eval/loss"]].dropna()

# Plot both
import matplotlib.pyplot as plt

plt.plot(train_loss["_step"], train_loss["loss"], label="Train")
plt.plot(eval_loss["_step"], eval_loss["eval/loss"], label="Eval", marker='o')
plt.legend()
plt.show()
```

---

## Artifact Object Reference

Artifacts are versioned datasets, models, or files logged to W&B.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Artifact name |
| `type` | str | Artifact type ("model", "dataset", etc.) |
| `version` | str | Version string (e.g., "v0", "v1") |
| `size` | int | Size in bytes |
| `created_at` | str | Creation timestamp |
| `updated_at` | str | Last update timestamp |
| `digest` | str | Content hash |
| `entity` | str | Owner entity |
| `project` | str | Project name |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `download()` | str | Download artifact, returns local path |
| `file()` | File | Get specific file from artifact |
| `files()` | list | List all files in artifact |
| `verify()` | bool | Verify artifact integrity |
| `delete()` | None | Delete artifact |

### Download Patterns

```python
# Download entire artifact
artifact = api.artifact("factorio/takka-qwen3-8b/model-abc123:v0")
artifact_dir = artifact.download(root="./artifacts")

# Download to specific directory
artifact_dir = artifact.download(root="./models/checkpoint-1000")

# List files before downloading
for file in artifact.files():
    print(f"File: {file.name} ({file.size} bytes)")

# Download specific file only
model_file = artifact.file("pytorch_model.bin")
model_file.download(root="./model")
```

### Get Artifact from Run

```python
run = api.run("factorio/takka-qwen3-8b/abc123")

# Get logged artifacts
for artifact in run.logged_artifacts():
    print(f"Logged: {artifact.name} ({artifact.type})")

# Get used artifacts (inputs)
for artifact in run.used_artifacts():
    print(f"Used: {artifact.name} ({artifact.type})")

# Download latest model artifact
model_artifacts = [a for a in run.logged_artifacts() if a.type == "model"]
if model_artifacts:
    latest = model_artifacts[-1]
    path = latest.download()
    print(f"Downloaded to: {path}")
```

---

## Sweep Object Reference

A sweep is a hyperparameter search configuration.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | str | Sweep ID |
| `name` | str | Sweep name |
| `entity` | str | Entity name |
| `project` | str | Project name |
| `config` | dict | Sweep configuration |
| `state` | str | Sweep state |
| `runs` | list | List of runs in sweep |

### Access Sweep

```python
# Get sweep by ID
sweep = api.sweep("factorio/takka-qwen3-8b/sweep-id")

# Get sweep config
print(sweep.config)

# Get all runs in sweep
for run in sweep.runs:
    print(f"{run.name}: {run.summary.get('eval/loss')}")

# Find best run in sweep
best_run = min(sweep.runs, key=lambda r: r.summary.get("eval/loss", float('inf')))
print(f"Best run: {best_run.name}")
```

---

## Export Formats

### To DataFrame

```python
import pandas as pd

runs = api.runs("factorio/takka-qwen3-8b", filters={"state": "finished"})

data = []
for run in runs:
    row = {
        "run_id": run.id,
        "name": run.name,
        "state": run.state,
        "learning_rate": run.config.get("learning_rate"),
        "batch_size": run.config.get("batch_size"),
        "eval_loss": run.summary.get("eval/loss"),
        "perplexity": run.summary.get("eval/perplexity"),
    }
    data.append(row)

df = pd.DataFrame(data)
print(df.head())
```

### To JSON

```python
import json

runs = api.runs("factorio/takka-qwen3-8b", filters={"state": "finished"})

data = []
for run in runs:
    run_data = {
        "id": run.id,
        "name": run.name,
        "config": dict(run.config),
        "summary": dict(run.summary),
        "tags": run.tags,
    }
    data.append(run_data)

with open("runs.json", "w") as f:
    json.dump(data, f, indent=2)
```

### To CSV with pandas

```python
import pandas as pd

df = compare_hyperparameters(filters={"state": "finished"})
df.to_csv("run_comparison.csv", index=False)

# Load back
df_loaded = pd.read_csv("run_comparison.csv")
```

---

## Takka-Specific Examples

### Example 1: Find Best Qwen3-4B Run

```python
PROJECT = "factorio/takka-qwen3-8b"

# Filter for 4B model runs only
runs = api.runs(PROJECT, filters={
    "state": "finished",
    "config.model_name_or_path": {"$regex": "Qwen3-4B"}
})

# Find lowest eval loss
best_run = None
best_loss = float('inf')

for run in runs:
    eval_loss = run.summary.get("eval/loss")
    if eval_loss and eval_loss < best_loss:
        best_loss = eval_loss
        best_run = run

if best_run:
    print(f"Best Qwen3-4B run: {best_run.name}")
    print(f"Eval Loss: {best_loss:.4f}")
    print(f"Config: LR={best_run.config.get('learning_rate')}, "
          f"BS={best_run.config.get('batch_size')}")
    print(f"URL: {best_run.url}")
```

### Example 2: Compare v5 vs v7 Training Data

```python
# Assuming dataset version is in run name or config
v5_runs = api.runs(PROJECT, filters={
    "state": "finished",
    "display_name": {"$regex": "v5"}
})

v7_runs = api.runs(PROJECT, filters={
    "state": "finished",
    "display_name": {"$regex": "v7"}
})

# Calculate average eval loss
v5_losses = [r.summary.get("eval/loss") for r in v5_runs
             if r.summary.get("eval/loss")]
v7_losses = [r.summary.get("eval/loss") for r in v7_runs
             if r.summary.get("eval/loss")]

if v5_losses and v7_losses:
    print(f"v5 average eval loss: {sum(v5_losses)/len(v5_losses):.4f}")
    print(f"v7 average eval loss: {sum(v7_losses)/len(v7_losses):.4f}")

    improvement = (sum(v5_losses)/len(v5_losses) - sum(v7_losses)/len(v7_losses))
    print(f"Improvement: {improvement:.4f}")
```

### Example 3: Analyze Translation Loss Weighting

```python
def analyze_loss_weighting(run_id, project=PROJECT):
    """
    Analyze the effect of loss weighting on translation quality.
    Compares weighted loss vs unweighted translation_loss.
    """
    run = api.run(f"{project}/{run_id}")

    history = run.history(keys=[
        "loss",               # Weighted overall loss
        "translation_loss",   # Unweighted translation loss
        "_step"
    ])

    if "translation_loss" not in history.columns:
        print("No translation_loss metric in this run")
        return None

    # Calculate statistics
    loss_data = history[["loss", "translation_loss"]].dropna()

    correlation = loss_data["loss"].corr(loss_data["translation_loss"])
    gap = loss_data["translation_loss"] - loss_data["loss"]

    print(f"Run: {run.name}")
    print(f"Correlation: {correlation:.3f}")
    print(f"Mean gap (trans - weighted): {gap.mean():.3f}")
    print(f"Gap std: {gap.std():.3f}")

    # Final values
    final_weighted = history["loss"].iloc[-1]
    final_trans = history["translation_loss"].iloc[-1]

    print(f"\nFinal weighted loss: {final_weighted:.4f}")
    print(f"Final translation loss: {final_trans:.4f}")

    return {
        "correlation": correlation,
        "mean_gap": gap.mean(),
        "std_gap": gap.std(),
        "final_weighted": final_weighted,
        "final_translation": final_trans,
    }

analyze_loss_weighting("abc123")
```

### Example 4: Get Together AI Model Name

```python
def get_together_model(run_id, project=PROJECT):
    """
    Extract Together AI model name from W&B run.
    Used for inference with Together API.
    """
    run = api.run(f"{project}/{run_id}")

    together_model = run.config.get("together_model_name")
    together_job = run.config.get("together_job_id")

    if together_model:
        print(f"Together AI Model: {together_model}")
        print(f"Together Job ID: {together_job}")
        print(f"\nInference command:")
        print(f"  together.Complete.create(model='{together_model}', prompt='...')")
    else:
        print("No Together AI model found in config")

    return together_model

get_together_model("abc123")
```

### Example 5: Full Kaggle Checkpoint Selection

```python
def kaggle_checkpoint_selection(
    model_size="4B",
    strategy="lowest_eval_loss",
    project=PROJECT
):
    """
    Complete workflow to select best checkpoint for Kaggle submission.

    Args:
        model_size: "4B" or "8B"
        strategy: checkpoint selection strategy
        project: W&B project

    Returns:
        Dict with run info and download command
    """
    # Step 1: Filter for target model size
    model_filter = f"Qwen3-{model_size}"
    runs = api.runs(project, filters={
        "state": "finished",
        "config.model_name_or_path": {"$regex": model_filter}
    })

    print(f"Found {len(runs)} finished {model_size} runs")

    if len(runs) == 0:
        print(f"No finished runs found for {model_size}")
        return None

    # Step 2: Find best by eval loss
    best_run = min(runs, key=lambda r: r.summary.get("eval/loss", float('inf')))

    print(f"\nBest run: {best_run.name}")
    print(f"Eval loss: {best_run.summary['eval/loss']:.4f}")

    # Step 3: Check for overfitting
    history = best_run.history(keys=["eval/loss", "_step"])
    eval_data = history[["_step", "eval/loss"]].dropna()

    if len(eval_data) >= 5:
        # Check if loss increased in last 20%
        split = int(len(eval_data) * 0.8)
        early_min = eval_data["eval/loss"].iloc[:split].min()
        late_min = eval_data["eval/loss"].iloc[split:].min()

        overfitting = late_min > early_min * 1.02

        if overfitting:
            print("⚠️  Possible overfitting detected")
            strategy = "last_before_overfit"
    else:
        print("ℹ️  Insufficient eval data to check overfitting")

    # Step 4: Select checkpoint
    best_step = select_best_checkpoint(best_run.id, strategy=strategy, project=project)

    # Step 5: Generate download command
    result = {
        "run_id": best_run.id,
        "run_name": best_run.name,
        "eval_loss": best_run.summary["eval/loss"],
        "best_step": best_step,
        "model_size": model_size,
        "url": best_run.url,
    }

    print("\n" + "=" * 60)
    print("KAGGLE SUBMISSION CHECKPOINT")
    print("=" * 60)
    print(f"Run: {result['run_name']}")
    print(f"Step: {result['best_step']}")
    print(f"Eval Loss: {result['eval_loss']:.4f}")
    print(f"\nDownload:")
    print(f"  download_checkpoint('{result['run_id']}', download_dir='./kaggle_model')")

    return result

# Usage
kaggle_checkpoint_selection(model_size="4B", strategy="lowest_eval_loss")
```

### Example 6: Monitor Live Training

```python
import time
from datetime import datetime

def monitor_training(run_id, project=PROJECT, refresh=60):
    """
    Monitor live training run with periodic updates.

    Args:
        run_id: W&B run ID
        project: W&B project
        refresh: seconds between updates
    """
    print(f"Monitoring: {run_id}")
    print(f"Refresh: every {refresh}s")
    print("-" * 60)

    last_step = 0

    while True:
        try:
            run = api.run(f"{project}/{run_id}")

            timestamp = datetime.now().strftime("%H:%M:%S")

            if run.state in ["finished", "failed", "crashed"]:
                print(f"\n[{timestamp}] Training ended: {run.state}")
                break

            # Get latest metrics
            history = run.history(samples=100)

            if len(history) > 0:
                latest = history.iloc[-1]
                current_step = latest.get("_step", 0)

                if current_step > last_step:
                    loss = latest.get("loss", "N/A")
                    lr = latest.get("learning_rate", "N/A")

                    print(f"[{timestamp}] Step {current_step}: "
                          f"loss={loss:.4f if isinstance(loss, float) else loss}, "
                          f"lr={lr:.2e if isinstance(lr, float) else lr}")

                    last_step = current_step

            time.sleep(refresh)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(refresh)

# Usage
monitor_training("abc123", refresh=30)
```

### Example 7: Batch Export for Analysis

```python
def export_all_runs(output_file="runs_export.csv", project=PROJECT):
    """
    Export all run data to CSV for external analysis.

    Creates comprehensive CSV with config, metrics, and metadata.
    """
    import pandas as pd

    print(f"Exporting runs from {project}...")

    runs = api.runs(project)

    data = []
    for i, run in enumerate(runs):
        if i % 10 == 0:
            print(f"Processing run {i+1}/{len(runs)}...")

        row = {
            # Basic info
            "run_id": run.id,
            "name": run.name,
            "state": run.state,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "url": run.url,

            # Config (flatten common hyperparameters)
            "model": run.config.get("model_name_or_path"),
            "learning_rate": run.config.get("learning_rate"),
            "batch_size": run.config.get("batch_size"),
            "num_epochs": run.config.get("num_train_epochs"),
            "scheduler": run.config.get("lr_scheduler_type"),
            "warmup_ratio": run.config.get("warmup_ratio"),
            "weight_decay": run.config.get("weight_decay"),
            "gradient_accumulation": run.config.get("gradient_accumulation_steps"),

            # Summary metrics
            "final_loss": run.summary.get("loss"),
            "final_eval_loss": run.summary.get("eval/loss"),
            "final_perplexity": run.summary.get("eval/perplexity"),
            "total_steps": run.summary.get("train/global_step"),

            # Takka-specific
            "translation_loss": run.summary.get("translation_loss"),
            "dataset_version": run.config.get("dataset_version"),
            "together_model": run.config.get("together_model_name"),

            # Tags
            "tags": ",".join(run.tags) if run.tags else "",
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Sort by created_at descending
    df = df.sort_values("created_at", ascending=False)

    df.to_csv(output_file, index=False)
    print(f"\n✓ Exported {len(df)} runs to {output_file}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Total runs: {len(df)}")
    print(f"  Finished: {len(df[df['state'] == 'finished'])}")
    print(f"  Running: {len(df[df['state'] == 'running'])}")
    print(f"  Failed: {len(df[df['state'] == 'failed'])}")

    return df

# Usage
df = export_all_runs("takka_runs.csv")
```

---

## Rate Limits & Error Handling

### Rate Limits

W&B API has rate limits:
- **Public API:** 200 requests/minute
- **History queries:** Large histories count as multiple requests

**Best practices:**
- Cache API results locally for repeated analysis
- Use `samples` parameter to limit history size
- Use `keys` parameter to fetch only needed metrics
- Batch operations when possible

### Common Errors

**CommError** — Network/connection error:
```python
from wandb.errors import CommError

try:
    runs = api.runs(PROJECT)
except CommError as e:
    print(f"Connection error: {e}")
    print("Check internet connection and API key")
```

**UsageError** — Invalid API usage:
```python
from wandb.errors import UsageError

try:
    run = api.run("invalid/path")
except UsageError as e:
    print(f"Usage error: {e}")
```

**Error Handling Pattern:**
```python
import time
from wandb.errors import CommError

def fetch_run_with_retry(run_id, max_retries=3, project=PROJECT):
    """Fetch run with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return api.run(f"{project}/{run_id}")
        except CommError as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # Exponential backoff
            print(f"Retry {attempt+1}/{max_retries} after {wait}s...")
            time.sleep(wait)

run = fetch_run_with_retry("abc123")
```

---

## Links

**Official Documentation:**
- W&B Python API: https://docs.wandb.ai/ref/python/public-api
- Guides: https://docs.wandb.ai/guides
- API Reference: https://docs.wandb.ai/ref/python
- Run object: https://docs.wandb.ai/ref/python/run
- Artifact reference: https://docs.wandb.ai/guides/artifacts

**Takka Project:**
- Project CLAUDE.md: `/Users/jackhopkins/PycharmProjects/Takka/CLAUDE.md`
- W&B Project: https://wandb.ai/factorio/takka-qwen3-8b
- Training notebooks: `notebooks/together_finetune.ipynb`, `notebooks/post_training.ipynb`

**Related Skills:**
- `together-ai` — Together AI fine-tuning integration
- `inspect-ai` — Inspect AI evaluation workflows