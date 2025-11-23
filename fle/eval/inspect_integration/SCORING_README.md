# Enhanced Factorio Scoring System

## Overview

The enhanced scoring system tracks three key metrics during Factorio trajectory execution using inspect_ai's intermediate scoring capabilities:

1. **Proportion of Desired Throughput** - Ratio of achieved vs expected production
2. **Overall Production Score** - Raw production values with efficiency metrics  
3. **Step-by-Step Change Tracking** - Production score changes between steps

## Scorers Available

### `comprehensive_factorio_scorer()` 
**File**: `enhanced_scorer.py:144`
- **Metrics**: `@scorer(metrics=[accuracy(), mean()])`
- **Combines**: All three metrics + success/failure
- **Use**: Default scorer for complete analysis

### `throughput_proportion_scorer()`
**File**: `enhanced_scorer.py:15`  
- **Metric**: `proportion = min(achieved/expected, 1.0)`
- **Tracks**: Throughput achievement ratio (capped at 100%)
- **Use**: Focus on quota achievement analysis

### `production_score_tracker()`
**File**: `enhanced_scorer.py:54`
- **Metric**: Raw production score + efficiency
- **Tracks**: Total production, score-per-step, steps-per-score
- **Use**: Overall production performance analysis

### `step_change_tracker()`
**File**: `enhanced_scorer.py:91`
- **Metric**: `change = scores[-1] - scores[-2]`
- **Tracks**: Last step change, total change, average change
- **Use**: Step-by-step improvement analysis

### `binary_success_scorer()`
**File**: `enhanced_scorer.py:233`
- **Metric**: Boolean success/failure
- **Tracks**: Pass@N evaluation
- **Use**: Simple binary outcomes

## Intermediate Scoring

### Real-Time Step Scoring
**Function**: `apply_intermediate_scoring()` in `enhanced_scorer.py:351`

Called during each step of trajectory execution:
```python
await apply_intermediate_scoring(
    state=state,
    step_num=step + 1,
    production_score=production_score,
    expected_score=quota,
    scores_history=production_scores
)
```

### Metrics Captured Per Step
- **Throughput Proportion**: Current achievement vs goal
- **Production Score**: Current raw score 
- **Step Change**: Improvement from previous step
- **Metadata**: Step number, metric type, calculations

## Usage Examples

### Basic Evaluation
```bash
# Default comprehensive scoring
inspect eval factorio_eval_set.py@iron_ore_throughput --epochs 8

# Focus on specific metrics
inspect eval factorio_eval_set.py@iron_ore_throughput_proportion --epochs 8
inspect eval factorio_eval_set.py@iron_ore_throughput_production --epochs 8
inspect eval factorio_eval_set.py@iron_ore_throughput_step_change --epochs 8
```

### Multiple Tasks with Different Metrics
```bash
# Compare different scoring approaches
inspect eval factorio_eval_set.py@iron_ore_throughput,iron_ore_throughput_proportion --epochs 5
```

## Metadata Captured

### Comprehensive Scorer Metadata
```json
{
  "throughput_proportion": 0.75,
  "production_score": 75.2,
  "last_step_change": 2.3,
  "expected_score": 100.0,
  "quota_achieved": false,
  "total_change": 75.2,
  "average_step_change": 1.17,
  "score_per_step": 1.17,
  "max_single_step_gain": 5.8,
  "total_steps": 64,
  "has_error": false,
  "scores_count": 64,
  "final_10_scores": [65.1, 67.4, 69.8, 72.1, 75.2],
  "env_id": "iron_ore_throughput",
  "trajectory_length": 64
}
```

### Intermediate Score Metadata (Per Step)
```json
{
  "step": 32,
  "metric_type": "throughput_proportion", 
  "production_score": 45.6,
  "expected_score": 100.0,
  "proportion": 0.456
}
```

## Key Benefits

1. **Real-Time Tracking**: Metrics captured at every step, not just final
2. **Multiple Perspectives**: Different scorers focus on different aspects
3. **Rich Context**: Comprehensive metadata for analysis
4. **Intermediate Analysis**: Track progress patterns during execution
5. **Flexible Evaluation**: Choose scoring approach based on research needs

## Technical Implementation

- **Intermediate Scoring**: Uses `inspect_ai.scorer.score()` function
- **Store Integration**: Uses `store_as(TrajectoryData)` for data access
- **Error Handling**: Graceful degradation on scoring errors
- **Performance**: Minimal overhead during trajectory execution

The system provides granular insights into model performance across different aspects of Factorio production optimization tasks.