# Factorio Learning Environment - Analysis Framework

This directory contains a comprehensive analysis framework for evaluating and monitoring large-scale experiments in the Factorio Learning Environment.

## Overview

The analysis framework provides:

1. **DatabaseAnalyzer**: Query and aggregate results from PostgreSQL
2. **PerformanceMetrics**: Calculate success rates, pass@k, and statistical summaries  
3. **WandBLogger**: Real-time experiment tracking and visualization
4. **SweepManager**: Orchestrate large-scale evaluation sweeps
5. **ResultsVisualizer**: Generate plots and analysis reports

## Quick Start

### Basic Usage

```python
from fle.eval.analysis import DatabaseAnalyzer, PerformanceAnalyzer

# Analyze recent results
analyzer = DatabaseAnalyzer()
recent_results = await analyzer.get_recent_results(hours=24)

# Calculate performance metrics
trajectory_summary = await analyzer.get_trajectory_summaries([version_id])
metrics = PerformanceAnalyzer.calculate_metrics(
    trajectory_summary, 
    reward_column='final_reward'
)

print(f"Success rate: {metrics.success_rate:.1%}")
print(f"Pass@1: {metrics.pass_at_1:.3f}")
```

### Running Sweeps

```python
from fle.eval.analysis import SweepManager, SweepConfig

# Configure sweep
config = SweepConfig(
    name="my_evaluation",
    models=["gpt-4o", "gpt-4o-mini"],
    tasks=["Factorio-iron_ore_throughput_16-v0"],
    num_trials_per_config=8,  # Pass@8
    enable_wandb=True,
    output_dir="./results"
)

# Run sweep
manager = SweepManager(config)
results = await manager.run_sweep()
```

### WandB Integration

Enable real-time monitoring by setting environment variables:

```bash
export ENABLE_WANDB=true
export WANDB_PROJECT=my-factorio-eval
export WANDB_ENTITY=my-team  # optional
```

## Components

### DatabaseAnalyzer

Queries and aggregates evaluation results from PostgreSQL:

```python
analyzer = DatabaseAnalyzer()

# Get results by model and task
results = await analyzer.get_results_by_model_and_task(
    model="gpt-4o", 
    task_pattern="iron_ore"
)

# Compare model performance
comparison = await analyzer.get_model_comparison(
    models=["gpt-4o", "claude-3-5-sonnet"],
    min_trajectories=10
)

# Analyze task difficulty
task_breakdown = await analyzer.get_task_breakdown(model="gpt-4o")
```

### PerformanceMetrics

Calculate comprehensive performance statistics:

```python
from fle.eval.analysis import PerformanceAnalyzer

metrics = PerformanceAnalyzer.calculate_metrics(
    trajectory_df,
    reward_column='final_reward',
    success_threshold=0.0,
    token_column='total_tokens',
    k_values=[1, 3, 5, 8]  # Pass@k values
)

# Access metrics
print(f"Success rate: {metrics.success_rate:.1%}")
print(f"Pass@8: {metrics.pass_at_k[8]:.3f}")
print(f"Mean tokens per success: {metrics.tokens_per_success:.0f}")
```

### WandBLogger

Real-time experiment tracking:

```python
from fle.eval.analysis import WandBLogger

logger = WandBLogger(
    project="my-project",
    run_name="experiment-1",
    tags=["evaluation", "gpt-4o"]
)

# Log performance metrics
logger.log_performance_metrics(
    metrics, 
    model="gpt-4o", 
    task="iron_ore_throughput"
)

# Log trajectory progress
logger.log_trajectory_progress(
    version=123,
    instance=0,
    step=10,
    reward=0.85,
    model="gpt-4o",
    task="iron_ore"
)
```

### SweepManager

Orchestrate large-scale evaluations:

```python
config = SweepConfig(
    name="production_eval",
    models=["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
    tasks=[
        "Factorio-iron_ore_throughput_16-v0",
        "Factorio-copper_ore_throughput_16-v0",
        # ... more tasks
    ],
    num_trials_per_config=8,
    max_concurrent_processes=4,
    enable_wandb=True,
    retry_failed_runs=True,
    max_retries=2
)

manager = SweepManager(config)
results = await manager.run_sweep()
```

### ResultsVisualizer

Generate analysis plots:

```python
from fle.eval.analysis import ResultsVisualizer

visualizer = ResultsVisualizer()

# Model comparison bar chart
fig = visualizer.plot_model_comparison(
    model_metrics, 
    metric='success_rate'
)

# Pass@k curves
fig = visualizer.plot_pass_at_k(model_metrics)

# Comprehensive report with all plots
viz_files = visualizer.create_comprehensive_report(
    model_metrics=model_metrics,
    results_df=trajectory_df,
    output_dir="./analysis_output"
)
```

## Examples

See the `examples/` directory for complete usage examples:

- `example_sweep_config.py`: Example sweep configurations
- `analyze_sweep_results.py`: Analysis script with various commands

### Running Examples

```bash
# Small test sweep
python examples/example_sweep_config.py

# Large production sweep  
python examples/example_sweep_config.py large

# Analyze recent results
python examples/analyze_sweep_results.py recent 24

# Compare models
python examples/analyze_sweep_results.py compare gpt-4o claude-3-5-sonnet

# Analyze task difficulty
python examples/analyze_sweep_results.py tasks

# Create comprehensive report
python examples/analyze_sweep_results.py report 123 124 125

# Monitor ongoing sweep
python examples/analyze_sweep_results.py monitor
```

## Integration with run_eval.py

The analysis framework integrates seamlessly with the existing evaluation system:

1. **WandB Logging**: Automatically enabled when `ENABLE_WANDB=true`
2. **Database Storage**: All results stored in PostgreSQL as before
3. **Real-time Monitoring**: Progress tracked in WandB during execution

### Environment Variables

- `ENABLE_WANDB`: Set to `true` to enable WandB logging
- `WANDB_PROJECT`: WandB project name (default: `factorio-learning-environment`)
- `WANDB_ENTITY`: WandB team/user entity (optional)
- `DISABLE_WANDB`: Set to `true` to explicitly disable WandB

## Dependencies

The analysis framework requires:

```bash
pip install pandas numpy scipy matplotlib seaborn wandb
```

Optional for some visualizations:
- matplotlib
- seaborn

WandB integration is optional but recommended for real-time monitoring.

## Performance Metrics

The framework calculates these key metrics:

### Basic Statistics
- **Success Rate**: Percentage of trajectories achieving reward > threshold
- **Mean/Median/Std Reward**: Distribution statistics
- **Min/Max Reward**: Reward range

### Pass@k Metrics
- **Pass@1**: Best single performance (max reward > threshold)
- **Pass@k**: Probability that at least one of k random samples succeeds

### Efficiency Metrics
- **Tokens per Success**: Average tokens used in successful trajectories
- **Mean Steps**: Average trajectory length
- **Time Efficiency**: Time-based performance metrics

### Statistical Significance
- **Confidence Intervals**: 95% CI for success rates
- **Statistical Tests**: Mann-Whitney U, t-tests for model comparisons

## Best Practices

### For Sweeps
1. Start with small test sweeps to validate configuration
2. Use appropriate `max_concurrent_processes` based on resources
3. Enable `retry_failed_runs` for production sweeps
4. Monitor progress with WandB for long-running experiments

### For Analysis
1. Filter by recent time periods for ongoing experiments
2. Require minimum trajectory counts for reliable statistics
3. Use statistical significance tests when comparing models
4. Save analysis results and visualizations for reports

### For Monitoring
1. Set appropriate `log_interval_minutes` based on experiment duration
2. Use WandB tags to organize experiments
3. Monitor both individual trajectory progress and aggregate metrics
4. Set up alerts for failed runs in production sweeps

## Troubleshooting

### Common Issues

**WandB not logging**: Check `ENABLE_WANDB` environment variable and WandB installation

**Database connection errors**: Ensure PostgreSQL is running and connection parameters are correct

**Import errors**: Verify all dependencies are installed in the correct virtual environment

**Memory issues with large sweeps**: Reduce `max_concurrent_processes` or analyze results in smaller batches

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new analysis features:

1. Add comprehensive docstrings
2. Include type hints for all functions
3. Add examples to the `examples/` directory
4. Update this README with new functionality
5. Add unit tests where appropriate
