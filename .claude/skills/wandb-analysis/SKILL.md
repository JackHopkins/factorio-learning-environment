---
name: wandb-analysis
description: Analyze Weights & Biases runs programmatically. Use when asked to "analyze loss curves", "compare W&B runs", "find best checkpoint", "plot training metrics", "query wandb", or "download wandb artifacts". Covers Python API for querying runs, analyzing loss patterns, comparing hyperparameters, and working with artifacts.
---

# Weights & Biases Analysis — Programmatic Run Analysis & Loss Curve Inspection

This skill covers programmatic analysis of Weights & Biases training runs using the [W&B Python API](https://docs.wandb.ai/ref/python/public-api). Focus areas:

1. **Querying runs** using the Python API (`wandb.Api()`)
2. **Analyzing loss curves** — plotting, smoothing, detecting overfitting
3. **Comparing hyperparameters** across multiple runs
4. **Checkpoint selection** strategies for model deployment
5. **Takka-specific patterns** — translation loss analysis, Together AI integration

Reference documentation:
- W&B Python API: https://docs.wandb.ai/ref/python/public-api
- Guides: https://docs.wandb.ai/guides
- Run object reference: https://docs.wandb.ai/ref/python/run

---

## Installation

```bash
pip install wandb pandas matplotlib numpy scipy
```

**Authentication:**

```bash
# Interactive login
wandb login

# Or set API key directly
export WANDB_API_KEY=your_key_here
```

Find your API key at: https://wandb.ai/authorize

---

## Part 1: Python API Basics — Querying Runs

### Initialize the API

```python
import wandb

# Initialize API client
api = wandb.Api()

# Optional: specify timeout
api = wandb.Api(timeout=60)
```

### Fetch Runs from a Project

```python
# Get all runs from a project
PROJECT = "factorio/takka-qwen3-8b"
runs = api.runs(PROJECT)

print(f"Total runs: {len(runs)}")
for run in runs:
    print(f"{run.id}: {run.name} - {run.state}")
```

**Output:**
```
Total runs: 47
abc123: qwen3-4b-v5-lr5e5: finished
def456: qwen3-8b-v7-cosine: running
...
```

### Filter Runs

Use MongoDB-style filter syntax:

```python
# Only finished runs
runs = api.runs(PROJECT, filters={"state": "finished"})

# Runs with specific config value
runs = api.runs(PROJECT, filters={"config.learning_rate": 5e-5})

# Runs created after a date
runs = api.runs(PROJECT, filters={
    "created_at": {"$gt": "2026-01-01"}
})

# Multiple conditions (AND)
runs = api.runs(PROJECT, filters={
    "state": "finished",
    "config.model": {"$regex": "qwen3-4b"}
})

# Runs with eval_loss < 2.0
runs = api.runs(PROJECT, filters={
    "summary_metrics.eval/loss": {"$lt": 2.0}
})
```

**Common filter operators:**
- `$eq` — equals
- `$ne` — not equals
- `$gt`, `$gte` — greater than (or equal)
- `$lt`, `$lte` — less than (or equal)
- `$in` — value in list
- `$regex` — regex match
- `$exists` — field exists

### Access Run Properties

```python
run = api.run(f"{PROJECT}/abc123")  # Fetch specific run by ID

# Basic properties
print(run.id)           # abc123
print(run.name)         # qwen3-4b-v5-lr5e5
print(run.state)        # finished
print(run.url)          # https://wandb.ai/factorio/takka-qwen3-8b/runs/abc123
print(run.created_at)   # 2026-03-01 10:30:00

# Config (hyperparameters)
print(run.config)       # Dict of all config values
print(run.config["learning_rate"])   # 5e-5
print(run.config.get("batch_size", 8))  # Safe access with default

# Summary (final metrics)
print(run.summary)      # Dict of final metric values
print(run.summary["eval/loss"])       # 1.234
print(run.summary["train/global_step"])  # 10000
```

### Get Metric History

```python
# Get full history as pandas DataFrame
history = run.history()

# Get specific metrics only (faster)
history = run.history(keys=["loss", "eval/loss", "learning_rate"])

# Sample large histories (get every Nth point)
history = run.history(samples=1000)  # Max 1000 points

# Get history as list of dicts (not DataFrame)
history = run.history(pandas=False)

print(history.head())
```

**Output:**
```
   _step  _runtime  loss  eval/loss  learning_rate
0      0      10.5  3.45        NaN       5.00e-05
1     10      25.3  3.12        NaN       4.99e-05
2     20      40.1  2.98      2.456      4.98e-05
...
```

**Important:**
- `_step` is the global step counter
- `_runtime` is elapsed seconds
- Eval metrics (like `eval/loss`) are sparse (only logged on eval steps)
- Use `.dropna()` to filter out NaN values

---

## Part 2: Loss Curve Analysis ⭐

### Plot Training and Evaluation Loss

```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_loss_curve(run_id, project=PROJECT):
    """Plot train and eval loss for a single run."""
    run = api.run(f"{project}/{run_id}")

    # Fetch loss history
    history = run.history(keys=["loss", "eval/loss", "_step"])

    # Separate train and eval (eval is sparse)
    train_loss = history[["_step", "loss"]].dropna()
    eval_loss = history[["_step", "eval/loss"]].dropna()

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(train_loss["_step"], train_loss["loss"],
            label="Train Loss", alpha=0.7, linewidth=1)
    ax.plot(eval_loss["_step"], eval_loss["eval/loss"],
            label="Eval Loss", alpha=0.9, linewidth=2, marker='o', markersize=3)

    ax.set_xlabel("Step")
    ax.set_ylabel("Loss")
    ax.set_title(f"Loss Curves: {run.name}")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"loss_curve_{run_id}.png", dpi=150)
    plt.show()

    return fig

# Usage
plot_loss_curve("abc123")
```

### Apply Exponential Moving Average Smoothing

Raw loss curves are noisy. Smooth them for better trend visualization:

```python
def smooth_loss(values, alpha=0.9):
    """
    Exponential moving average smoothing.

    Args:
        values: array of loss values
        alpha: smoothing factor (0-1). Higher = smoother

    Returns:
        Smoothed array
    """
    smoothed = []
    last = values[0]

    for point in values:
        smoothed_val = last * alpha + (1 - alpha) * point
        smoothed.append(smoothed_val)
        last = smoothed_val

    return np.array(smoothed)

# Usage in plot
def plot_loss_smoothed(run_id, alpha=0.9, project=PROJECT):
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["loss", "eval/loss", "_step"])

    train_loss = history[["_step", "loss"]].dropna()
    eval_loss = history[["_step", "eval/loss"]].dropna()

    # Apply smoothing
    train_smoothed = smooth_loss(train_loss["loss"].values, alpha=alpha)
    eval_smoothed = smooth_loss(eval_loss["eval/loss"].values, alpha=alpha)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot raw (faint)
    ax.plot(train_loss["_step"], train_loss["loss"],
            alpha=0.2, color='blue', linewidth=0.5)
    ax.plot(eval_loss["_step"], eval_loss["eval/loss"],
            alpha=0.3, color='orange', linewidth=0.5)

    # Plot smoothed (bold)
    ax.plot(train_loss["_step"], train_smoothed,
            label="Train Loss (smoothed)", color='blue', linewidth=2)
    ax.plot(eval_loss["_step"], eval_smoothed,
            label="Eval Loss (smoothed)", color='orange', linewidth=2)

    ax.set_xlabel("Step")
    ax.set_ylabel("Loss")
    ax.set_title(f"Smoothed Loss Curves (α={alpha}): {run.name}")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    return fig

plot_loss_smoothed("abc123", alpha=0.95)
```

### Detect Overfitting

Overfitting occurs when eval loss stops decreasing while train loss continues to drop:

```python
def detect_overfitting(run_id, window=100, threshold=0.02, project=PROJECT):
    """
    Detect overfitting by comparing train vs eval loss trends.

    Args:
        run_id: W&B run ID
        window: number of steps to analyze for trend
        threshold: minimum gap increase to flag overfitting
        project: W&B project path

    Returns:
        Dict with overfitting analysis
    """
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["loss", "eval/loss", "_step"])

    train_loss = history[["_step", "loss"]].dropna()
    eval_loss = history[["_step", "eval/loss"]].dropna()

    if len(eval_loss) < 2:
        return {"overfitting": False, "reason": "Insufficient eval points"}

    # Align train and eval on common steps
    eval_steps = eval_loss["_step"].values
    train_at_eval = train_loss[train_loss["_step"].isin(eval_steps)]

    # Calculate gap (eval - train) over time
    gaps = []
    for step in eval_steps:
        eval_val = eval_loss[eval_loss["_step"] == step]["eval/loss"].values[0]
        train_val = train_at_eval[train_at_eval["_step"] == step]["loss"].values

        if len(train_val) > 0:
            gaps.append(eval_val - train_val[0])

    gaps = np.array(gaps)

    # Check if gap is widening in recent window
    if len(gaps) >= window:
        early_gap = np.mean(gaps[:window])
        recent_gap = np.mean(gaps[-window:])
        gap_increase = recent_gap - early_gap

        is_overfitting = gap_increase > threshold

        return {
            "overfitting": is_overfitting,
            "early_gap": early_gap,
            "recent_gap": recent_gap,
            "gap_increase": gap_increase,
            "final_train_loss": train_loss["loss"].iloc[-1],
            "final_eval_loss": eval_loss["eval/loss"].iloc[-1],
        }
    else:
        return {"overfitting": False, "reason": "Insufficient data for trend"}

# Usage
result = detect_overfitting("abc123", window=50, threshold=0.05)
print(f"Overfitting detected: {result['overfitting']}")
if result['overfitting']:
    print(f"Gap increased from {result['early_gap']:.3f} to {result['recent_gap']:.3f}")
```

### Analyze Translation Loss (Takka-Specific)

The Takka project logs both weighted and unweighted translation loss:

```python
def analyze_translation_loss(run_id, project=PROJECT):
    """
    Compare weighted vs unweighted translation loss.
    Takka logs custom metrics for translation quality.
    """
    run = api.run(f"{project}/{run_id}")

    # Check if custom metrics exist
    history = run.history(keys=[
        "loss",              # Overall weighted loss
        "translation_loss",  # Unweighted translation loss
        "_step"
    ])

    if "translation_loss" not in history.columns:
        print("No translation_loss metric found in this run")
        return None

    # Plot comparison
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Top: both losses
    ax1.plot(history["_step"], history["loss"],
             label="Weighted Loss", alpha=0.8)
    ax1.plot(history["_step"], history["translation_loss"],
             label="Translation Loss", alpha=0.8)
    ax1.set_ylabel("Loss")
    ax1.set_title(f"Weighted vs Translation Loss: {run.name}")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Bottom: gap over time
    gap = history["translation_loss"] - history["loss"]
    ax2.plot(history["_step"], gap, color='green', alpha=0.8)
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax2.set_xlabel("Step")
    ax2.set_ylabel("Gap (Translation - Weighted)")
    ax2.set_title("Loss Gap Over Time")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    return {
        "final_weighted": history["loss"].iloc[-1],
        "final_translation": history["translation_loss"].iloc[-1],
        "mean_gap": gap.mean(),
    }

analyze_translation_loss("abc123")
```

### Compare Perplexity Trends

```python
def plot_perplexity(run_id, project=PROJECT):
    """Plot perplexity alongside loss."""
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["loss", "eval/perplexity", "_step"])

    eval_data = history[["_step", "eval/perplexity"]].dropna()
    loss_data = history[["_step", "loss"]].dropna()

    # Dual-axis plot
    fig, ax1 = plt.subplots(figsize=(12, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Step')
    ax1.set_ylabel('Loss', color=color)
    ax1.plot(loss_data["_step"], loss_data["loss"],
             color=color, alpha=0.8, label="Train Loss")
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()  # Second y-axis
    color = 'tab:orange'
    ax2.set_ylabel('Perplexity', color=color)
    ax2.plot(eval_data["_step"], eval_data["eval/perplexity"],
             color=color, alpha=0.8, marker='o', markersize=4, label="Eval Perplexity")
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title(f"Loss vs Perplexity: {run.name}")
    fig.tight_layout()
    plt.show()

    return fig

plot_perplexity("abc123")
```

---

## Part 3: Comparing Multiple Runs

### Overlay Loss Curves from Different Runs

```python
def compare_runs(run_ids, metric="eval/loss", project=PROJECT):
    """
    Overlay loss curves from multiple runs for comparison.

    Args:
        run_ids: list of run IDs
        metric: metric to compare (default: eval/loss)
        project: W&B project
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    for run_id in run_ids:
        run = api.run(f"{project}/{run_id}")
        history = run.history(keys=[metric, "_step"])

        data = history[["_step", metric]].dropna()

        # Smooth for clarity
        smoothed = smooth_loss(data[metric].values, alpha=0.95)

        ax.plot(data["_step"], smoothed,
                label=f"{run.name}", alpha=0.8, linewidth=2)

    ax.set_xlabel("Step")
    ax.set_ylabel(metric)
    ax.set_title(f"Comparison: {metric}")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    return fig

# Usage
compare_runs(["abc123", "def456", "ghi789"], metric="eval/loss")
```

### Create Hyperparameter Comparison Table

```python
def compare_hyperparameters(run_ids=None, filters=None, project=PROJECT):
    """
    Create comparison table of hyperparameters and results.

    Args:
        run_ids: specific run IDs to compare (optional)
        filters: W&B filters dict (optional, used if run_ids not provided)
        project: W&B project

    Returns:
        pandas DataFrame with comparison
    """
    import pandas as pd

    if run_ids:
        runs = [api.run(f"{project}/{rid}") for rid in run_ids]
    else:
        runs = api.runs(project, filters=filters or {})

    data = []
    for run in runs:
        row = {
            "run_id": run.id,
            "name": run.name,
            "state": run.state,
            # Config
            "learning_rate": run.config.get("learning_rate"),
            "batch_size": run.config.get("batch_size"),
            "epochs": run.config.get("num_train_epochs"),
            "scheduler": run.config.get("lr_scheduler_type"),
            "warmup_ratio": run.config.get("warmup_ratio"),
            # Results
            "final_loss": run.summary.get("loss"),
            "final_eval_loss": run.summary.get("eval/loss"),
            "final_perplexity": run.summary.get("eval/perplexity"),
            "total_steps": run.summary.get("train/global_step"),
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Sort by eval loss (best first)
    df = df.sort_values("final_eval_loss")

    return df

# Usage
df = compare_hyperparameters(filters={"state": "finished"})
print(df.to_string())

# Export to CSV
df.to_csv("run_comparison.csv", index=False)
```

**Output:**
```
  run_id              name     state  learning_rate  batch_size  epochs scheduler  ...
0 abc123  qwen3-4b-v5-lr5e5  finished       5.00e-05           8       6    cosine  ...
1 def456  qwen3-4b-v7-lr3e5  finished       3.00e-05           8       6    cosine  ...
...
```

### Find Best Run by Metric

```python
def find_best_run(metric="eval/loss", minimize=True, project=PROJECT, filters=None):
    """
    Find the best run according to a metric.

    Args:
        metric: metric to optimize
        minimize: True to find minimum, False for maximum
        project: W&B project
        filters: additional filters

    Returns:
        Best run object
    """
    runs = api.runs(project, filters=filters or {})

    best_run = None
    best_value = float('inf') if minimize else float('-inf')

    for run in runs:
        value = run.summary.get(metric)

        if value is None:
            continue

        if minimize and value < best_value:
            best_value = value
            best_run = run
        elif not minimize and value > best_value:
            best_value = value
            best_run = run

    if best_run:
        print(f"Best run: {best_run.name} ({best_run.id})")
        print(f"{metric}: {best_value}")
        print(f"URL: {best_run.url}")
    else:
        print("No runs found")

    return best_run

# Usage
best = find_best_run("eval/loss", minimize=True, filters={"state": "finished"})
```

---

## Part 4: Learning Rate Analysis

### Plot Learning Rate Schedule

```python
def plot_lr_schedule(run_id, project=PROJECT):
    """Plot learning rate over training."""
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["learning_rate", "_step"])

    lr_data = history[["_step", "learning_rate"]].dropna()

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(lr_data["_step"], lr_data["learning_rate"],
            linewidth=2, color='green')
    ax.set_xlabel("Step")
    ax.set_ylabel("Learning Rate")
    ax.set_title(f"Learning Rate Schedule: {run.name}")
    ax.grid(alpha=0.3)

    # Annotate scheduler type
    scheduler = run.config.get("lr_scheduler_type", "unknown")
    ax.text(0.02, 0.98, f"Scheduler: {scheduler}",
            transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.show()

    return fig

plot_lr_schedule("abc123")
```

### Compare Different Schedulers

```python
def compare_schedulers(project=PROJECT):
    """Compare runs with different LR schedulers."""
    # Get runs grouped by scheduler
    runs = api.runs(project, filters={"state": "finished"})

    schedulers = {}
    for run in runs:
        sched = run.config.get("lr_scheduler_type", "unknown")
        if sched not in schedulers:
            schedulers[sched] = []
        schedulers[sched].append(run)

    # Plot one example from each scheduler type
    fig, axes = plt.subplots(len(schedulers), 1,
                             figsize=(12, 4 * len(schedulers)))

    if len(schedulers) == 1:
        axes = [axes]

    for ax, (sched, sched_runs) in zip(axes, schedulers.items()):
        run = sched_runs[0]  # Pick first run
        history = run.history(keys=["learning_rate", "loss", "_step"])

        # Dual axis: LR and loss
        color = 'tab:green'
        ax.set_xlabel('Step')
        ax.set_ylabel('Learning Rate', color=color)
        ax.plot(history["_step"], history["learning_rate"],
                color=color, linewidth=2)
        ax.tick_params(axis='y', labelcolor=color)

        ax2 = ax.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Loss', color=color)
        ax2.plot(history["_step"], history["loss"],
                 color=color, alpha=0.6)
        ax2.tick_params(axis='y', labelcolor=color)

        ax.set_title(f"Scheduler: {sched} ({run.name})")
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    return fig

compare_schedulers()
```

### Correlate LR with Loss Changes

```python
def analyze_lr_loss_correlation(run_id, project=PROJECT):
    """Analyze how learning rate changes correlate with loss changes."""
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["learning_rate", "loss", "_step"])

    # Calculate rate of change
    history["lr_delta"] = history["learning_rate"].diff()
    history["loss_delta"] = history["loss"].diff()

    # Remove NaN
    clean = history.dropna()

    # Scatter plot: LR delta vs loss delta
    fig, ax = plt.subplots(figsize=(10, 6))

    scatter = ax.scatter(clean["lr_delta"], clean["loss_delta"],
                         c=clean["_step"], cmap='viridis',
                         alpha=0.5, s=10)

    ax.set_xlabel("Learning Rate Change")
    ax.set_ylabel("Loss Change")
    ax.set_title(f"LR vs Loss Correlation: {run.name}")
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.3)
    ax.grid(alpha=0.3)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Step')

    plt.tight_layout()
    plt.show()

    return fig

analyze_lr_loss_correlation("abc123")
```

---

## Part 5: Artifacts & Checkpoints

### List Artifacts for a Run

```python
def list_artifacts(run_id, project=PROJECT):
    """List all artifacts logged by a run."""
    run = api.run(f"{project}/{run_id}")

    artifacts = []
    for artifact in run.logged_artifacts():
        artifacts.append({
            "name": artifact.name,
            "type": artifact.type,
            "size": artifact.size,
            "created_at": artifact.created_at,
            "version": artifact.version,
        })

    df = pd.DataFrame(artifacts)
    print(df.to_string())

    return artifacts

# Usage
list_artifacts("abc123")
```

### Download Model Checkpoint

```python
def download_checkpoint(run_id, artifact_name=None, download_dir="./checkpoints", project=PROJECT):
    """
    Download model checkpoint from W&B.

    Args:
        run_id: W&B run ID
        artifact_name: specific artifact name (if None, downloads latest model)
        download_dir: local directory to save
        project: W&B project

    Returns:
        Path to downloaded checkpoint
    """
    import os

    run = api.run(f"{project}/{run_id}")

    # Find model artifact
    if artifact_name is None:
        # Get latest model artifact
        artifacts = list(run.logged_artifacts())
        model_artifacts = [a for a in artifacts if a.type == "model"]

        if not model_artifacts:
            print("No model artifacts found")
            return None

        artifact = model_artifacts[-1]  # Latest
    else:
        artifact = api.artifact(f"{project}/{artifact_name}")

    print(f"Downloading {artifact.name} ({artifact.size / 1e9:.2f} GB)...")

    # Download
    artifact_dir = artifact.download(root=download_dir)

    print(f"Downloaded to: {artifact_dir}")
    return artifact_dir

# Usage
path = download_checkpoint("abc123", download_dir="./models")
```

### Checkpoint Selection Strategies

```python
def select_best_checkpoint(run_id, strategy="lowest_eval_loss", project=PROJECT):
    """
    Select best checkpoint using various strategies.

    Strategies:
        - lowest_eval_loss: checkpoint with lowest eval loss
        - last_before_overfit: last checkpoint before overfitting detected
        - stable_plateau: checkpoint where loss has stabilized
        - final: final checkpoint (last epoch)

    Returns:
        Step number of best checkpoint
    """
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=["eval/loss", "_step"])
    eval_data = history[["_step", "eval/loss"]].dropna()

    if len(eval_data) == 0:
        print("No eval data available")
        return None

    if strategy == "lowest_eval_loss":
        # Simply find minimum eval loss
        best_idx = eval_data["eval/loss"].idxmin()
        best_step = eval_data.loc[best_idx, "_step"]
        best_loss = eval_data.loc[best_idx, "eval/loss"]

        print(f"Strategy: lowest_eval_loss")
        print(f"Best step: {best_step}")
        print(f"Eval loss: {best_loss:.4f}")

        return int(best_step)

    elif strategy == "last_before_overfit":
        # Find where eval loss starts increasing
        eval_losses = eval_data["eval/loss"].values
        steps = eval_data["_step"].values

        # Find local minimum followed by sustained increase
        window = min(3, len(eval_losses) // 4)

        for i in range(len(eval_losses) - window):
            current = eval_losses[i]
            future = eval_losses[i+1:i+1+window]

            if all(f > current for f in future):
                # Found point before sustained increase
                print(f"Strategy: last_before_overfit")
                print(f"Best step: {steps[i]}")
                print(f"Eval loss: {eval_losses[i]:.4f}")
                return int(steps[i])

        # Fallback to lowest
        best_idx = eval_data["eval/loss"].idxmin()
        return int(eval_data.loc[best_idx, "_step"])

    elif strategy == "stable_plateau":
        # Find where loss variance is lowest
        eval_losses = eval_data["eval/loss"].values
        steps = eval_data["_step"].values

        window = min(5, len(eval_losses) // 3)
        min_variance = float('inf')
        best_idx = 0

        for i in range(len(eval_losses) - window):
            variance = np.var(eval_losses[i:i+window])
            if variance < min_variance:
                min_variance = variance
                best_idx = i + window // 2  # Middle of stable region

        print(f"Strategy: stable_plateau")
        print(f"Best step: {steps[best_idx]}")
        print(f"Eval loss: {eval_losses[best_idx]:.4f}")
        print(f"Variance: {min_variance:.6f}")

        return int(steps[best_idx])

    elif strategy == "final":
        # Just use last checkpoint
        final_step = eval_data["_step"].iloc[-1]
        final_loss = eval_data["eval/loss"].iloc[-1]

        print(f"Strategy: final")
        print(f"Final step: {final_step}")
        print(f"Eval loss: {final_loss:.4f}")

        return int(final_step)

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

# Usage
best_step = select_best_checkpoint("abc123", strategy="lowest_eval_loss")
```

---

## Part 6: Advanced Patterns

### Custom Dual-Axis Charts

```python
def plot_dual_metric(run_id, metric1="loss", metric2="eval/perplexity", project=PROJECT):
    """Plot two metrics on dual y-axes."""
    run = api.run(f"{project}/{run_id}")
    history = run.history(keys=[metric1, metric2, "_step"])

    data1 = history[["_step", metric1]].dropna()
    data2 = history[["_step", metric2]].dropna()

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color1 = 'tab:blue'
    ax1.set_xlabel('Step')
    ax1.set_ylabel(metric1, color=color1)
    ax1.plot(data1["_step"], data1[metric1],
             color=color1, alpha=0.8, linewidth=2)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    color2 = 'tab:orange'
    ax2.set_ylabel(metric2, color=color2)
    ax2.plot(data2["_step"], data2[metric2],
             color=color2, alpha=0.8, linewidth=2)
    ax2.tick_params(axis='y', labelcolor=color2)

    plt.title(f"{metric1} vs {metric2}: {run.name}")
    fig.tight_layout()
    plt.show()

    return fig

plot_dual_metric("abc123", "loss", "eval/perplexity")
```

### Hyperparameter Sweep Analysis

```python
def analyze_sweep(sweep_id=None, param="learning_rate", metric="eval/loss", project=PROJECT):
    """
    Analyze hyperparameter sweep results.

    Args:
        sweep_id: W&B sweep ID (optional)
        param: hyperparameter to analyze
        metric: target metric
        project: W&B project
    """
    import pandas as pd

    if sweep_id:
        # Get runs from specific sweep
        sweep = api.sweep(f"{project}/{sweep_id}")
        runs = sweep.runs
    else:
        # Analyze all runs
        runs = api.runs(project, filters={"state": "finished"})

    # Collect data
    data = []
    for run in runs:
        param_value = run.config.get(param)
        metric_value = run.summary.get(metric)

        if param_value is not None and metric_value is not None:
            data.append({
                param: param_value,
                metric: metric_value,
                "run_id": run.id,
                "name": run.name,
            })

    df = pd.DataFrame(data)
    df = df.sort_values(param)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(df[param], df[metric], s=100, alpha=0.6)

    # Annotate best point
    best_idx = df[metric].idxmin()
    best_param = df.loc[best_idx, param]
    best_metric = df.loc[best_idx, metric]

    ax.scatter([best_param], [best_metric],
               s=200, color='red', marker='*',
               label=f"Best: {best_param}")

    ax.set_xlabel(param)
    ax.set_ylabel(metric)
    ax.set_title(f"Hyperparameter Sweep: {param} vs {metric}")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    print("\nTop 5 runs:")
    print(df.nsmallest(5, metric).to_string())

    return df

# Usage
df = analyze_sweep(param="learning_rate", metric="eval/loss")
```

### Together AI Run Integration

The Takka project uses Together AI for training. Fetch Together AI model metadata:

```python
def get_together_model_info(run_id, project=PROJECT):
    """
    Extract Together AI model information from W&B run.
    Takka logs Together AI job IDs and model names in config.
    """
    run = api.run(f"{project}/{run_id}")

    info = {
        "run_id": run.id,
        "run_name": run.name,
        "together_job_id": run.config.get("together_job_id"),
        "together_model_name": run.config.get("together_model_name"),
        "base_model": run.config.get("model_name_or_path"),
        "training_file": run.config.get("training_file"),
        "dataset_version": run.config.get("dataset_version"),
    }

    print("Together AI Model Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    return info

# Usage
info = get_together_model_info("abc123")
```

### Live Training Monitoring

Monitor a running training job in real-time:

```python
import time

def monitor_live_training(run_id, metric="loss", refresh_interval=30, project=PROJECT):
    """
    Monitor live training run, printing updates.

    Args:
        run_id: W&B run ID
        metric: metric to monitor
        refresh_interval: seconds between updates
        project: W&B project
    """
    print(f"Monitoring run {run_id}...")
    print(f"Metric: {metric}")
    print(f"Refresh interval: {refresh_interval}s")
    print("-" * 50)

    last_step = 0

    try:
        while True:
            run = api.run(f"{project}/{run_id}")

            if run.state == "finished":
                print("\n✓ Training finished!")
                break
            elif run.state == "failed":
                print("\n✗ Training failed!")
                break
            elif run.state == "crashed":
                print("\n✗ Training crashed!")
                break

            # Get latest metric value
            history = run.history(keys=[metric, "_step"], samples=100)

            if len(history) > 0:
                latest = history.iloc[-1]
                current_step = latest["_step"]
                current_value = latest[metric]

                if current_step > last_step:
                    print(f"Step {current_step}: {metric} = {current_value:.4f}")
                    last_step = current_step

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

# Usage
monitor_live_training("abc123", metric="loss", refresh_interval=60)
```

---

## Part 7: CLI Commands

W&B provides CLI commands for quick tasks:

```bash
# Login
wandb login

# List recent runs
wandb runs factorio/takka-qwen3-8b

# Show run details
wandb run factorio/takka-qwen3-8b/abc123

# Download artifacts
wandb artifact get factorio/takka-qwen3-8b/model-abc123:v0

# Export run history to CSV
wandb export factorio/takka-qwen3-8b/abc123 --format csv --output run.csv

# Restore files from a run
wandb restore run.py --run abc123
```

---

## Part 8: Common Workflows

### Workflow 1: Find Best Model for Kaggle Submission

Complete workflow to identify and download the best checkpoint for competition submission:

```python
def kaggle_checkpoint_workflow(project=PROJECT):
    """Complete workflow for Kaggle checkpoint selection."""

    print("=" * 60)
    print("KAGGLE CHECKPOINT SELECTION WORKFLOW")
    print("=" * 60)

    # Step 1: Find all finished runs
    print("\n[1/5] Fetching finished runs...")
    runs = api.runs(project, filters={"state": "finished"})
    print(f"Found {len(runs)} finished runs")

    # Step 2: Compare hyperparameters and results
    print("\n[2/5] Comparing runs...")
    comparison = compare_hyperparameters(filters={"state": "finished"}, project=project)
    print("\nTop 5 runs by eval loss:")
    print(comparison.head(5)[["name", "learning_rate", "final_eval_loss"]].to_string())

    # Step 3: Find best run
    print("\n[3/5] Selecting best run...")
    best = find_best_run("eval/loss", minimize=True, project=project)

    # Step 4: Analyze best run's loss curve
    print("\n[4/5] Analyzing loss curve...")
    plot_loss_smoothed(best.id, project=project)

    # Step 5: Check for overfitting
    print("\n[5/5] Checking for overfitting...")
    overfit_check = detect_overfitting(best.id, project=project)

    if overfit_check.get("overfitting"):
        print("⚠️  Overfitting detected!")
        print(f"Consider using checkpoint from step ~{overfit_check.get('early_gap', 0) * 1000}")
    else:
        print("✓ No overfitting detected")

    # Final recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    print(f"Run ID: {best.id}")
    print(f"Run Name: {best.name}")
    print(f"Final Eval Loss: {best.summary['eval/loss']:.4f}")
    print(f"URL: {best.url}")

    # Determine checkpoint strategy
    if overfit_check.get("overfitting"):
        strategy = "last_before_overfit"
    else:
        strategy = "lowest_eval_loss"

    best_step = select_best_checkpoint(best.id, strategy=strategy, project=project)

    print(f"\nBest checkpoint: step {best_step}")
    print(f"Download command:")
    print(f"  python download_checkpoint('{best.id}', download_dir='./kaggle_model')")

    return {
        "run_id": best.id,
        "run_name": best.name,
        "best_step": best_step,
        "eval_loss": best.summary["eval/loss"],
    }

# Usage
result = kaggle_checkpoint_workflow()
```

### Workflow 2: Debug Training Divergence

When a training run fails or diverges, compare it to successful runs:

```python
def debug_divergence(failed_run_id, project=PROJECT):
    """Compare failed run to successful runs to debug issues."""

    print("=" * 60)
    print("TRAINING DIVERGENCE DEBUGGING")
    print("=" * 60)

    failed_run = api.run(f"{project}/{failed_run_id}")

    print(f"\nFailed run: {failed_run.name} ({failed_run_id})")
    print(f"State: {failed_run.state}")

    # Get config
    config = failed_run.config

    # Find similar successful runs
    print("\n[1/3] Finding similar successful runs...")
    similar_runs = api.runs(project, filters={
        "state": "finished",
        "config.model_name_or_path": config.get("model_name_or_path"),
    })

    if len(similar_runs) == 0:
        print("No similar successful runs found")
        return

    print(f"Found {len(similar_runs)} similar successful runs")

    # Compare loss curves
    print("\n[2/3] Comparing loss curves...")
    run_ids = [failed_run_id] + [r.id for r in similar_runs[:3]]
    compare_runs(run_ids, metric="loss", project=project)

    # Compare hyperparameters
    print("\n[3/3] Comparing hyperparameters...")
    all_runs = [failed_run] + list(similar_runs[:3])

    print("\nHyperparameter comparison:")
    print(f"{'Param':<20} {'Failed':<15} {'Successful (avg)':<15}")
    print("-" * 50)

    params_to_check = ["learning_rate", "batch_size", "warmup_ratio",
                       "weight_decay", "gradient_accumulation_steps"]

    for param in params_to_check:
        failed_val = config.get(param, "N/A")

        successful_vals = [r.config.get(param) for r in similar_runs
                          if r.config.get(param) is not None]

        if successful_vals:
            avg_successful = sum(successful_vals) / len(successful_vals)
            print(f"{param:<20} {str(failed_val):<15} {avg_successful:<15.6f}")
        else:
            print(f"{param:<20} {str(failed_val):<15} {'N/A':<15}")

    print("\n" + "=" * 60)
    print("FINDINGS")
    print("=" * 60)

    # Analyze failed run's loss trajectory
    history = failed_run.history(keys=["loss", "_step"])
    loss_data = history[["loss"]].dropna()

    if len(loss_data) > 10:
        initial_loss = loss_data["loss"].iloc[:10].mean()
        final_loss = loss_data["loss"].iloc[-10:].mean()

        if final_loss > initial_loss * 2:
            print("⚠️  Loss diverged (increased over training)")
            print("   → Check learning rate (may be too high)")
            print("   → Check gradient clipping")
        elif final_loss > 100:
            print("⚠️  Loss exploded")
            print("   → Likely learning rate too high")
            print("   → Check for NaN in data")
        else:
            print("ℹ️  Loss trajectory seems normal")
            print("   → Check other metrics or system logs")

# Usage
debug_divergence("failed_run_id")
```

### Workflow 3: Hyperparameter Sweep Analysis

After running a sweep, analyze results:

```python
def sweep_summary(sweep_id=None, project=PROJECT):
    """Generate comprehensive sweep summary."""

    print("=" * 60)
    print("HYPERPARAMETER SWEEP SUMMARY")
    print("=" * 60)

    if sweep_id:
        sweep = api.sweep(f"{project}/{sweep_id}")
        runs = sweep.runs
        print(f"\nSweep ID: {sweep_id}")
        print(f"Sweep config: {sweep.config}")
    else:
        runs = api.runs(project, filters={"state": "finished"})
        print("\nAnalyzing all finished runs")

    print(f"Total runs: {len(runs)}")

    # Collect data
    data = []
    for run in runs:
        row = {
            "run_id": run.id,
            "name": run.name,
            "lr": run.config.get("learning_rate"),
            "bs": run.config.get("batch_size"),
            "warmup": run.config.get("warmup_ratio"),
            "scheduler": run.config.get("lr_scheduler_type"),
            "eval_loss": run.summary.get("eval/loss"),
            "perplexity": run.summary.get("eval/perplexity"),
        }
        data.append(row)

    df = pd.DataFrame(data)
    df = df.dropna(subset=["eval_loss"])
    df = df.sort_values("eval_loss")

    print("\n" + "=" * 60)
    print("TOP 10 RUNS")
    print("=" * 60)
    print(df.head(10).to_string())

    # Correlation analysis
    print("\n" + "=" * 60)
    print("PARAMETER CORRELATIONS")
    print("=" * 60)

    numeric_df = df[["lr", "bs", "warmup", "eval_loss"]].dropna()

    if len(numeric_df) > 1:
        corr = numeric_df.corr()["eval_loss"].drop("eval_loss")
        print("\nCorrelation with eval_loss:")
        for param, corr_val in corr.items():
            print(f"  {param:<10}: {corr_val:>7.3f}")

    # Plot correlations
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    axes[0].scatter(df["lr"], df["eval_loss"])
    axes[0].set_xlabel("Learning Rate")
    axes[0].set_ylabel("Eval Loss")
    axes[0].set_title("LR vs Eval Loss")

    axes[1].scatter(df["bs"], df["eval_loss"])
    axes[1].set_xlabel("Batch Size")
    axes[1].set_ylabel("Eval Loss")
    axes[1].set_title("Batch Size vs Eval Loss")

    axes[2].scatter(df["warmup"], df["eval_loss"])
    axes[2].set_xlabel("Warmup Ratio")
    axes[2].set_ylabel("Eval Loss")
    axes[2].set_title("Warmup vs Eval Loss")

    plt.tight_layout()
    plt.show()

    return df

# Usage
summary = sweep_summary()
```

---

## Part 9: Tips & Best Practices

### Filter on Server-Side

Always use filters to reduce data transfer:

```python
# ❌ Bad: fetch all runs, filter locally
runs = api.runs(PROJECT)
finished = [r for r in runs if r.state == "finished"]

# ✓ Good: filter on server
finished = api.runs(PROJECT, filters={"state": "finished"})
```

### Sample Large Histories

For runs with millions of steps, sample the history:

```python
# ❌ Bad: fetch entire history
history = run.history()  # Could be GBs of data

# ✓ Good: sample to manageable size
history = run.history(samples=1000)  # Max 1000 points
```

### Smooth Noisy Metrics

Always smooth loss curves before visual analysis:

```python
# Raw data is too noisy to interpret
smoothed = smooth_loss(raw_values, alpha=0.95)
```

### Check for NaN in Sparse Metrics

Eval metrics are only logged periodically:

```python
# ❌ Bad: assumes eval/loss is always present
eval_loss = history["eval/loss"]

# ✓ Good: filter out NaN
eval_data = history[["_step", "eval/loss"]].dropna()
```

### Cache API Calls Locally

W&B API can be slow. Cache results for repeated analysis:

```python
import pickle

def get_run_cached(run_id, cache_dir="./cache", project=PROJECT):
    """Fetch run with local caching."""
    import os
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = f"{cache_dir}/{run_id}.pkl"

    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    # Fetch from API
    run = api.run(f"{project}/{run_id}")

    # Cache
    with open(cache_file, "wb") as f:
        pickle.dump(run, f)

    return run
```

### Use Pandas for Bulk Analysis

Export to DataFrame for complex queries:

```python
# Collect all run data
data = []
for run in api.runs(PROJECT):
    data.append({
        "id": run.id,
        "name": run.name,
        "lr": run.config.get("learning_rate"),
        "eval_loss": run.summary.get("eval/loss"),
    })

df = pd.DataFrame(data)

# Now use pandas for analysis
best_lr = df.loc[df["eval_loss"].idxmin(), "lr"]
```

---

## Summary

This skill covered:
- ✓ Querying W&B runs with filters
- ✓ Analyzing loss curves with smoothing
- ✓ Detecting overfitting patterns
- ✓ Comparing multiple runs
- ✓ Learning rate schedule analysis
- ✓ Checkpoint selection strategies
- ✓ Artifact management
- ✓ Takka-specific patterns (translation loss, Together AI)
- ✓ Complete Kaggle submission workflow

**Key Functions:**
- `plot_loss_curve()` — basic loss visualization
- `plot_loss_smoothed()` — smoothed loss with EMA
- `detect_overfitting()` — automated overfitting detection
- `compare_runs()` — overlay multiple runs
- `select_best_checkpoint()` — checkpoint selection strategies
- `kaggle_checkpoint_workflow()` — complete submission workflow

For detailed API reference, see `REFERENCE.md`.

**External Resources:**
- W&B Documentation: https://docs.wandb.ai
- Python API Reference: https://docs.wandb.ai/ref/python/public-api
- Takka CLAUDE.md: /Users/jackhopkins/PycharmProjects/Takka/CLAUDE.md