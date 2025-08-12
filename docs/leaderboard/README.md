# Factorio Learning Environment Leaderboard

This directory contains the FLE leaderboard system, which tracks and displays performance metrics for different LLM agents in the Factorio Learning Environment.

## Structure

- `/results/`: JSON files with raw results from each model
- `/processed/`: Combined and processed results (auto-generated, do not modify directly)

## Adding New Results

To submit new model results to the leaderboard:

1. Create a new JSON file in the `docs/leaderboard/results/` directory
2. Name the file using the model name: `model-name.json` (e.g., `claude-3-5-sonnet.json`)
3. Use the following format for your result data:

```json
{
  "name": "Your Model Name",
  "productionScore": 123456,
  "milestones": 20,
  "automationMilestones": 4,
  "labTasksSuccessRate": 15.5,
  "mostComplexItem": "advanced-circuit",
  "submittedBy": "Your Name",
  "submissionDate": "YYYY-MM-DD"
}
```

4. Submit a pull request with your new result file
5. Once the PR is merged, the results will be processed and the leaderboard will be updated

## Fields Explanation

| Field | Description |
|-------|-------------|
| `name` | Name of the model
| `productionScore` | Total production score achieved
| `milestones` | Number of milestones reached
| `automationMilestones` | Number of automation milestones reached
| `labTasksSuccessRate` | Percentage of lab tasks successfully completed
| `mostComplexItem` | Most complex item produced
| `submittedBy` | Your name or identifier
| `submissionDate` | Date of submission (YYYY-MM-DD)

## How It Works

1. When you submit a new result file via PR, a GitHub Action processes all result files to create a combined dataset
2. The leaderboard is automatically built and deployed to GitHub Pages
3. The leaderboard UI is updated to include your new data
