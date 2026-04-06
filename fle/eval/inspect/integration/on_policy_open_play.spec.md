# FLE Inspect Eval Analysis Notebook Specification

## Purpose
Jupyter notebook for analyzing Factorio Learning Environment (FLE) evaluation runs. Uses the `inspect_ai.analysis` module to load `.eval` files into pandas DataFrames, then generates visualizations comparing model performance across production scores, achievements, research progress, latency breakdown, and code complexity.

## Dependencies

```python
# Core
import os
import ast
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Data & Visualization
import boto3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats

# Tokenization
import tiktoken

# Inspect AI - Analysis Module
from inspect_ai.analysis import (
    evals_df,
    samples_df,
    messages_df,
    events_df,
    prepare,
    model_info,
    score_to_float,
    Column,
    EvalColumn,
    SampleColumn,
    EventColumn,
    EvalColumns,
    SampleSummary,
    SampleScores,
    EventInfo,
    EventTiming,
    ModelEventColumns,
)
from inspect_ai.log import read_eval_log, EvalLog

# Environment
from dotenv import load_dotenv
```

## Configuration

```python
# S3 Configuration
S3_BUCKET = "dipika-lie-detection-data"
S3_PREFIX = "fle/test/21-12-2025/256_unbounded"  # Configurable path

# Local cache directory for downloaded files
CACHE_DIR = Path(tempfile.gettempdir()) / "_fle_eval_cache"

# Tokenizer
TOKENIZER = tiktoken.get_encoding("cl100k_base")
```

---

## Part A: Loading Data into DataFrames

### A1. S3 Download Functions

These remain as before for downloading `.eval` files from S3:

```python
@dataclass
class EvalFileInfo:
    """Information about an eval file in S3."""
    key: str
    size: int
    last_modified: datetime
    filename: str

    @property
    def local_path(self) -> Path:
        return CACHE_DIR / self.filename
```

**Functions:**
1. **list_eval_files(bucket, prefix)** → List[EvalFileInfo]
2. **download_eval_file(file_info, bucket, verbose)** → Path
3. **download_eval_files_parallel(eval_files, bucket, max_workers)** → List[Path]

### A2. Custom Column Definitions for TrajectoryData

Define custom columns to extract FLE-specific data from the sample store using JSONPath:

```python
# === Production Score Columns ===
TrajectoryScores = [
    SampleColumn(name="production_score", path="store.TrajectoryData:production_score", type=float, default=0.0),
    SampleColumn(name="final_score", path="store.TrajectoryData:final_score", type=float, default=0.0),
    SampleColumn(name="automated_production_score", path="store.TrajectoryData:automated_production_score", type=float, default=0.0),
    SampleColumn(name="final_automated_score", path="store.TrajectoryData:final_automated_score", type=float, default=0.0),
    SampleColumn(name="total_steps", path="store.TrajectoryData:total_steps", type=int, default=0),
    SampleColumn(name="scores", path="store.TrajectoryData:scores"),  # List[float]
    SampleColumn(name="automated_scores", path="store.TrajectoryData:automated_scores"),  # List[float]
    SampleColumn(name="ticks", path="store.TrajectoryData:ticks"),  # List[int]
    SampleColumn(name="error", path="store.TrajectoryData:error", type=str, default=""),
]

# === Achievement Columns ===
AchievementColumns = [
    SampleColumn(name="produced_item_types", path="store.TrajectoryData:produced_item_types"),  # List[str]
    SampleColumn(name="researched_technologies", path="store.TrajectoryData:researched_technologies"),  # List[str]
]

# === Latency Columns ===
LatencyColumns = [
    SampleColumn(name="inference_latencies", path="store.TrajectoryData:inference_latencies"),  # List[float]
    SampleColumn(name="env_execution_latencies", path="store.TrajectoryData:env_execution_latencies"),  # List[float]
    SampleColumn(name="policy_execution_latencies", path="store.TrajectoryData:policy_execution_latencies"),  # List[float]
    SampleColumn(name="sleep_durations", path="store.TrajectoryData:sleep_durations"),  # List[float]
    SampleColumn(name="total_step_latencies", path="store.TrajectoryData:total_step_latencies"),  # List[float]
]

# === Code Analysis Columns ===
CodeColumns = [
    SampleColumn(name="program_codes", path="store.TrajectoryData:program_codes"),  # List[str]
]

# === Step Details Columns ===
StepColumns = [
    SampleColumn(name="steps", path="store.TrajectoryData:steps"),  # List[dict] with step details
]

# Combined FLE columns
FLEColumns = TrajectoryScores + AchievementColumns + LatencyColumns + CodeColumns + StepColumns
```

### A3. Loading DataFrames with inspect_ai.analysis

```python
def load_fle_dataframes(log_paths: List[Path]) -> Dict[str, pd.DataFrame]:
    """Load all FLE eval data into structured DataFrames using inspect_ai.analysis.

    Returns dict with keys:
        - 'evals': Evaluation-level summary
        - 'samples': Sample-level data with TrajectoryData
        - 'events': Event-level data (ModelEvents for timing)
        - 'messages': Message-level data (optional)
    """

    # 1. Evaluation-level DataFrame
    evals = evals_df(
        logs=log_paths,
        columns=EvalColumns,
        strict=False,
        quiet=False
    )
    if isinstance(evals, tuple):
        evals, eval_errors = evals

    # 2. Sample-level DataFrame with FLE custom columns
    samples = samples_df(
        logs=log_paths,
        columns=SampleSummary + SampleScores + FLEColumns,
        full=True,  # Need full=True to access store data
        strict=False,
        parallel=True,
        quiet=False
    )
    if isinstance(samples, tuple):
        samples, sample_errors = samples

    # 3. Events DataFrame for detailed timing analysis
    events = events_df(
        logs=log_paths,
        columns=EventInfo + EventTiming + ModelEventColumns,
        filter=lambda e: type(e).__name__ == 'ModelEvent',  # Only ModelEvents
        strict=False,
        parallel=True,
        quiet=False
    )
    if isinstance(events, tuple):
        events, event_errors = events

    return {
        'evals': evals,
        'samples': samples,
        'events': events
    }
```

### A4. DataFrame Post-Processing with prepare()

```python
def prepare_fle_dataframes(dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Apply transformations to FLE DataFrames."""

    # Add model display names and metadata
    dfs['evals'] = prepare(dfs['evals'], [
        model_info(),  # Adds model_org, model_display_name, model_release_date
        score_to_float(['score_value', 'score_headline_value']),
    ])

    # Compute derived columns for samples
    samples = dfs['samples'].copy()

    # Automation ratio
    samples['automation_ratio'] = samples.apply(
        lambda row: (row['final_automated_score'] / row['final_score'] * 100)
                    if row['final_score'] > 0 else 0.0,
        axis=1
    )

    # Achievement counts
    samples['num_unique_items'] = samples['produced_item_types'].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    samples['num_technologies'] = samples['researched_technologies'].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    # Latency aggregates
    samples['total_inference_time'] = samples['inference_latencies'].apply(
        lambda x: sum(x) if isinstance(x, list) else 0.0
    )
    samples['total_env_time'] = samples['env_execution_latencies'].apply(
        lambda x: sum(x) if isinstance(x, list) else 0.0
    )
    samples['total_policy_time'] = samples['policy_execution_latencies'].apply(
        lambda x: sum(x) if isinstance(x, list) else 0.0
    )
    samples['total_sleep_time'] = samples['sleep_durations'].apply(
        lambda x: sum(x) if isinstance(x, list) else 0.0
    )
    samples['total_wall_clock_time'] = samples['total_step_latencies'].apply(
        lambda x: sum(x) if isinstance(x, list) else 0.0
    )

    # Average latencies
    samples['avg_inference_latency'] = samples['inference_latencies'].apply(
        lambda x: np.mean(x) if isinstance(x, list) and len(x) > 0 else 0.0
    )
    samples['avg_step_latency'] = samples['total_step_latencies'].apply(
        lambda x: np.mean(x) if isinstance(x, list) and len(x) > 0 else 0.0
    )

    dfs['samples'] = samples
    return dfs
```

### A5. Exploding List Columns for Time-Series Analysis

```python
def create_timeseries_df(samples_df: pd.DataFrame) -> pd.DataFrame:
    """Explode list columns to create step-by-step time series DataFrame.

    Each row represents one step in one trajectory.
    """
    # Select columns to explode
    ts_cols = ['scores', 'automated_scores', 'ticks', 'inference_latencies',
               'env_execution_latencies', 'policy_execution_latencies',
               'sleep_durations', 'total_step_latencies']

    # Keep identifier columns
    id_cols = ['id', 'model', 'task_name', 'final_score', 'total_steps']

    # Create exploded dataframe
    records = []
    for _, row in samples_df.iterrows():
        scores = row.get('scores', []) or []
        for step_idx, score in enumerate(scores):
            record = {
                'sample_id': row.get('id'),
                'model': row.get('model'),
                'task_name': row.get('task_name'),
                'step': step_idx + 1,
                'score': score,
            }
            # Add other time-series columns if available
            for col in ts_cols:
                if col != 'scores' and isinstance(row.get(col), list):
                    vals = row[col]
                    record[col.replace('_latencies', '_latency').replace('_durations', '_duration')] = \
                        vals[step_idx] if step_idx < len(vals) else None
            records.append(record)

    return pd.DataFrame(records)


def create_code_metrics_df(samples_df: pd.DataFrame) -> pd.DataFrame:
    """Create DataFrame with code metrics for each program in each trajectory."""
    records = []
    for _, row in samples_df.iterrows():
        program_codes = row.get('program_codes', []) or []
        for step_idx, code in enumerate(program_codes):
            metrics = analyze_code(code)
            record = {
                'sample_id': row.get('id'),
                'model': row.get('model'),
                'step': step_idx + 1,
                'cyclomatic_complexity': metrics.cyclomatic_complexity,
                'variable_assignments': metrics.variable_assignments,
                'conditionals': metrics.conditionals,
                'loops': metrics.loops,
                'function_definitions': metrics.function_definitions,
                'class_definitions': metrics.class_definitions,
                'try_except_blocks': metrics.try_except_blocks,
                'comprehensions': metrics.comprehensions,
                'total_lines': metrics.total_lines,
                'code_lines': metrics.code_lines,
                'parse_errors': metrics.parse_errors,
            }
            records.append(record)

    return pd.DataFrame(records)
```

---

## Part B: Generating Charts from DataFrames

All visualization functions receive DataFrames as input rather than custom objects.

### B1. Utility Functions

```python
def normalize_model_name(model: str) -> str:
    """Normalize model names for consistent grouping."""
    model = model.split('/')[-1] if '/' in model else model
    model = model.replace('claude-opus-4-5', 'claude-opus-4.5')
    model = model.replace('claude-sonnet-4-5', 'claude-sonnet-4.5')
    return model

def filter_valid_samples(df: pd.DataFrame, min_final_score: float = 0.0) -> pd.DataFrame:
    """Filter samples to include only valid trajectories."""
    return df[
        (df['total_steps'] > 0) &
        ((df['final_score'] > min_final_score) | (df['status'] != 'success'))
    ].copy()
```

### B2. CodeMetrics for Static Analysis

```python
@dataclass
class CodeMetrics:
    """Metrics extracted from static code analysis."""
    variable_assignments: int = 0
    conditionals: int = 0
    loops: int = 0
    function_definitions: int = 0
    class_definitions: int = 0
    try_except_blocks: int = 0
    with_statements: int = 0
    boolean_operators: int = 0
    comprehensions: int = 0
    assert_statements: int = 0
    cyclomatic_complexity: int = 1
    total_lines: int = 0
    code_lines: int = 0
    parse_errors: int = 0

class CodeMetricsVisitor(ast.NodeVisitor):
    """AST visitor for code metrics extraction."""
    # ... (implementation as in scorers.py)

def analyze_code(code: str) -> CodeMetrics:
    """Analyze Python code and return metrics."""
    # ... (implementation as in scorers.py)
```

---

## Visualization Functions (Using DataFrames)

### SECTION 1: Production Score Charts

#### 1. Production Score Over Steps
```python
def plot_production_score_over_steps(
    ts_df: pd.DataFrame,  # Time-series DataFrame from create_timeseries_df()
    title: str = "Production Score Over Steps",
    figsize: tuple = (14, 8),
    show_individual: bool = True,
    show_mean: bool = True,
    min_final_score: float = 0.0
):
    """Plot production score trajectories from time-series DataFrame."""
    # Group by step, calculate mean/std
    # Plot individual lines colored by sample_id
    # Overlay mean ± std band
```

#### 2. Final Scores Distribution
```python
def plot_final_scores_distribution(
    samples_df: pd.DataFrame,
    figsize: tuple = (12, 5)
):
    """Plot distribution of final scores from samples DataFrame."""
    # Use samples_df['final_score']
    # Histogram + box plot
```

#### 3. Score by Model with CI
```python
def plot_by_model_with_ci(
    ts_df: pd.DataFrame,
    figsize: tuple = (14, 8),
    min_final_score: float = 0.0
):
    """Plot mean score per step by model with 95% CI."""
    # Group ts_df by ['model', 'step']
    # Calculate mean, CI using scipy.stats
```

#### 4. Score by Model Subplots
```python
def plot_by_model_subplots(
    ts_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    figsize_per_model: tuple = (6, 5),
    min_final_score: float = 0.0
):
    """Subplot grid with one panel per model."""
```

### SECTION 2: Automated vs Total Production

#### 5. Automated vs Total Production Score
```python
def plot_automated_vs_total_score(
    ts_df: pd.DataFrame,  # Must include 'automated_scores' column exploded
    figsize: tuple = (14, 8)
):
    """Compare total vs automated production over steps."""
```

#### 6. Automation Ratio Over Steps
```python
def plot_automation_ratio_by_model(
    ts_df: pd.DataFrame,
    figsize: tuple = (14, 8)
):
    """Plot automation ratio (automated/total * 100) over steps by model."""
```

#### 7. Final Automation Ratio Distribution
```python
def plot_automation_ratio_distribution(
    samples_df: pd.DataFrame,
    figsize: tuple = (12, 5)
):
    """Histogram/box plot of samples_df['automation_ratio']."""
```

### SECTION 3: Token & Cost Analysis

#### 8. Tokens vs Score (3 Charts)
```python
def plot_tokens_vs_score_three_charts(
    samples_df: pd.DataFrame,
    events_df: pd.DataFrame,  # For API token data from ModelEvents
    figsize: tuple = (18, 6)
):
    """Three-panel chart: program length, output tokens, thinking tokens vs score."""
```

#### 9-11. Score vs Execution Time / Ticks / Growth Rate
```python
def plot_score_vs_execution_time_by_model(ts_df: pd.DataFrame, ...): ...
def plot_score_vs_ticks_by_model(ts_df: pd.DataFrame, ...): ...
def plot_growth_rate_vs_ticks_by_model(ts_df: pd.DataFrame, ...): ...
```

### SECTION 4: Latency Analysis

#### 12-13. Inference Latency Charts
```python
def plot_inference_latency_vs_step_by_model(ts_df: pd.DataFrame, ...): ...
def plot_inference_latency_vs_tokens_by_model(ts_df: pd.DataFrame, events_df: pd.DataFrame, ...): ...
```

#### 14. Latency Breakdown Stacked Area
```python
def plot_latency_breakdown_stacked(
    ts_df: pd.DataFrame,
    figsize: tuple = (14, 8)
):
    """Stacked area: inference, env, policy, sleep latencies over steps."""
    # Use ts_df columns: inference_latency, env_execution_latency,
    #                    policy_execution_latency, sleep_duration
```

#### 15. Latency Component Comparison by Model
```python
def plot_latency_components_by_model(
    samples_df: pd.DataFrame,
    figsize: tuple = (14, 8)
):
    """Grouped bar chart of avg latency components per model."""
    # Use samples_df aggregated columns: avg_inference_latency, etc.
```

#### 16-18. Policy/Sleep/Wall-Clock Charts
```python
def plot_policy_execution_distribution(samples_df: pd.DataFrame, ...): ...
def plot_sleep_duration_analysis(ts_df: pd.DataFrame, samples_df: pd.DataFrame, ...): ...
def plot_total_wallclock_by_model(samples_df: pd.DataFrame, ...): ...
```

### SECTION 5: Achievement Tracking

#### 19. Unique Items Produced Over Steps
```python
def plot_unique_items_over_steps(
    samples_df: pd.DataFrame,
    figsize: tuple = (14, 8)
):
    """Plot cumulative unique item count over steps.

    Note: Need to track item accumulation per step from store.TrajectoryData:steps
    or infer from produced_item_types list.
    """
```

#### 20. Item Category Breakdown by Model
```python
def plot_item_categories_by_model(
    samples_df: pd.DataFrame,
    figsize: tuple = (14, 8)
):
    """Stacked bar: raw resources, basic intermediates, advanced items per model."""
    # Parse samples_df['produced_item_types'] and categorize
    RAW_RESOURCES = {'iron-ore', 'copper-ore', 'coal', 'stone', 'wood', 'crude-oil', 'water', 'uranium-ore'}
    BASIC_INTERMEDIATES = {'iron-plate', 'copper-plate', 'steel-plate', 'stone-brick',
                          'copper-cable', 'iron-gear-wheel', 'iron-stick'}
```

#### 21-22. Achievement Distribution & Heatmap
```python
def plot_achievement_distribution(samples_df: pd.DataFrame, ...): ...
def plot_item_production_heatmap(samples_df: pd.DataFrame, top_n: int = 30, ...): ...
```

### SECTION 6: Research/Technology Tracking

#### 23-27. Technology Charts
```python
def plot_technologies_over_steps(samples_df: pd.DataFrame, ...): ...
def plot_tech_tiers_by_model(samples_df: pd.DataFrame, ...): ...
def plot_research_vs_production_score(samples_df: pd.DataFrame, ...): ...
def plot_technology_heatmap(samples_df: pd.DataFrame, ...): ...
def plot_time_to_first_research(samples_df: pd.DataFrame, ...): ...
```

Technology tier definitions:
```python
TIER1_TECHS = {'automation', 'logistics', 'optics', 'turrets', 'stone-wall', 'electronics', 'steel-processing'}
TIER2_TECHS = {'automation-2', 'logistics-2', 'fast-inserter', 'steel-axe', 'military', 'military-2',
               'engine', 'fluid-handling', 'oil-processing', 'plastics', 'sulfur-processing'}
TIER3_TECHS = {'automation-3', 'logistics-3', 'advanced-electronics', 'advanced-electronics-2',
               'advanced-oil-processing', 'chemical-science-pack', 'production-science-pack',
               'utility-science-pack', 'rocket-silo', 'space-science-pack'}
```

### SECTION 7: Code Complexity Analysis

#### 28-34. Code Metrics Charts
```python
def plot_cyclomatic_complexity_over_steps(
    code_df: pd.DataFrame,  # From create_code_metrics_df()
    figsize: tuple = (14, 8)
):
    """Plot cyclomatic complexity over steps by model."""

def plot_code_complexity_distribution(code_df: pd.DataFrame, ...): ...
def plot_code_metrics_radar(code_df: pd.DataFrame, ...): ...
def plot_code_structure_breakdown(code_df: pd.DataFrame, ...): ...
def plot_complexity_vs_score(samples_df: pd.DataFrame, code_df: pd.DataFrame, ...): ...
def plot_code_lines_vs_length(code_df: pd.DataFrame, ...): ...
def plot_parse_error_rate(code_df: pd.DataFrame, ...): ...
```

### SECTION 8: Correlation & Summary Charts

#### 35-38. Summary Charts
```python
def plot_correlation_matrix(
    samples_df: pd.DataFrame,
    figsize: tuple = (12, 10)
):
    """Correlation heatmap of key numeric columns."""
    cols = ['final_score', 'final_automated_score', 'automation_ratio',
            'num_unique_items', 'num_technologies', 'total_steps',
            'avg_inference_latency', 'total_wall_clock_time', 'total_sleep_time']
    corr = samples_df[cols].corr()
    # sns.heatmap with annotations

def plot_model_summary_dashboard(samples_df: pd.DataFrame, ...): ...
def plot_efficiency_frontier(samples_df: pd.DataFrame, ...): ...
def plot_score_per_latency(samples_df: pd.DataFrame, ...): ...
```

---

## Complete Notebook Workflow

```python
# === CELL 1: Setup ===
# pip install inspect-ai boto3 matplotlib pandas seaborn tiktoken scipy

# === CELL 2: Imports ===
from inspect_ai.analysis import evals_df, samples_df, events_df, prepare, ...

# === CELL 3: S3 Download ===
eval_files = list_eval_files(S3_BUCKET, S3_PREFIX)
download_eval_files_parallel(eval_files)
log_paths = [ef.local_path for ef in eval_files if ef.local_path.exists()]

# === CELL 4: Load DataFrames ===
dfs = load_fle_dataframes(log_paths)
dfs = prepare_fle_dataframes(dfs)

evals = dfs['evals']
samples = dfs['samples']
events = dfs['events']

# === CELL 5: Create Derived DataFrames ===
ts_df = create_timeseries_df(samples)
code_df = create_code_metrics_df(samples)

# === CELL 6: Summary Statistics ===
print(f"Loaded {len(evals)} evaluations, {len(samples)} samples")
print(samples.groupby('model')['final_score'].describe())

# === CELLS 7-40: Visualizations ===
# Each chart function receives the appropriate DataFrame(s)
plot_production_score_over_steps(ts_df)
plot_by_model_with_ci(ts_df)
plot_automation_ratio_by_model(ts_df)
plot_latency_breakdown_stacked(ts_df)
plot_item_categories_by_model(samples)
plot_tech_tiers_by_model(samples)
plot_cyclomatic_complexity_over_steps(code_df)
plot_correlation_matrix(samples)
# ... etc

# === CELL 41: Export ===
samples.to_csv('fle_analysis_summary.csv', index=False)
```

---

## DataFrame Schemas

### evals DataFrame (from evals_df)
| Column | Type | Description |
|--------|------|-------------|
| eval_id | str | Unique evaluation ID |
| run_id | str | Run identifier |
| task_name | str | Task name |
| model | str | Model identifier |
| status | str | Eval status (success/error/cancelled) |
| created | datetime | Creation timestamp |
| total_samples | int | Number of samples |
| completed_samples | int | Completed samples |
| score_headline_value | float | Primary score value |

### samples DataFrame (from samples_df + FLEColumns)
| Column | Type | Description |
|--------|------|-------------|
| id | str | Sample ID |
| model | str | Model name |
| task_name | str | Task name |
| epoch | int | Epoch number |
| status | str | Sample status |
| **final_score** | float | Final production score |
| **final_automated_score** | float | Final automated score |
| **automation_ratio** | float | Derived: automated/total * 100 |
| **total_steps** | int | Number of trajectory steps |
| **scores** | List[float] | Score at each step |
| **automated_scores** | List[float] | Automated score at each step |
| **ticks** | List[int] | Game ticks at each step |
| **produced_item_types** | List[str] | Unique items produced |
| **num_unique_items** | int | Derived: len(produced_item_types) |
| **researched_technologies** | List[str] | Technologies researched |
| **num_technologies** | int | Derived: len(researched_technologies) |
| **inference_latencies** | List[float] | Inference time per step |
| **env_execution_latencies** | List[float] | Env execution time per step |
| **policy_execution_latencies** | List[float] | Policy execution time per step |
| **sleep_durations** | List[float] | Sleep time per step |
| **total_step_latencies** | List[float] | Wall-clock time per step |
| **total_inference_time** | float | Derived: sum of inference |
| **avg_inference_latency** | float | Derived: mean of inference |
| **total_wall_clock_time** | float | Derived: sum of step latencies |
| **program_codes** | List[str] | Python code at each step |
| error | str | Error message if any |

### ts_df DataFrame (from create_timeseries_df)
| Column | Type | Description |
|--------|------|-------------|
| sample_id | str | Parent sample ID |
| model | str | Model name |
| step | int | Step number (1-indexed) |
| score | float | Production score at step |
| automated_score | float | Automated score at step |
| tick | int | Game tick at step |
| inference_latency | float | Inference time for step |
| env_execution_latency | float | Env time for step |
| policy_execution_latency | float | Policy time for step |
| sleep_duration | float | Sleep time for step |
| total_step_latency | float | Wall-clock time for step |

### code_df DataFrame (from create_code_metrics_df)
| Column | Type | Description |
|--------|------|-------------|
| sample_id | str | Parent sample ID |
| model | str | Model name |
| step | int | Step number |
| cyclomatic_complexity | int | CC metric |
| variable_assignments | int | Assignment count |
| conditionals | int | if/elif count |
| loops | int | for/while count |
| function_definitions | int | Function count |
| class_definitions | int | Class count |
| try_except_blocks | int | Try/except count |
| comprehensions | int | Comprehension count |
| total_lines | int | Total lines |
| code_lines | int | Non-empty, non-comment lines |
| parse_errors | int | Syntax error count |

---

## Key Benefits of DataFrame Approach

1. **Standard API**: Uses `inspect_ai.analysis` module - maintained by Inspect team
2. **Parallel Loading**: Built-in parallel processing for large datasets
3. **Flexible Columns**: Custom columns via JSONPath for any store data
4. **Composable Transforms**: `prepare()` chains transformations cleanly
5. **pandas Integration**: Full pandas/seaborn/matplotlib ecosystem available
6. **Memory Efficient**: Can filter/sample before loading into memory
7. **Type Safety**: Column specifications enforce types with defaults
8. **Error Handling**: `strict=False` returns errors alongside data

---

## Reference: Cyclomatic Complexity Formula

```
CC = 1 + (if/elif) + (for/while) + (and/or) + (except handlers)
     + (comprehension ifs) + (ternary) + (assert)
```
