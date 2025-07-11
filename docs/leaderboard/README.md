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
  "model": "Your Model Name",
  "productionScore": 123456,
  "milestones": 20,
  "labTasksSuccessRate": 15.5,
  "mostComplexItem": "advanced-circuit",
  "submittedBy": "Your Name",
  "submissionDate": "YYYY-MM-DD"
}
```

4. Submit a pull request with your new result file
5. Upon PR creation, the results will be processed and marked as "Pending"
6. Once the PR is merged, the results will be marked as "Verified" on the leaderboard

## Fields Explanation

| Field | Description | Required |
|-------|-------------|----------|
| `model` | Name of the model | Yes |
| `productionScore` | Total production score achieved | Yes |
| `milestones` | Number of milestones reached | Yes |
| `labTasksSuccessRate` | Percentage of lab tasks successfully completed | Yes |
| `mostComplexItem` | Most complex item produced | Yes |
| `timeToElectricDrill` | Steps until first electric drill deployed | No |
| `submittedBy` | Your name or identifier | Yes |
| `submissionDate` | Date of submission (YYYY-MM-DD) | Yes |

## How It Works

1. When you submit a new result file via PR, a GitHub Action processes all result files to create a combined dataset
2. The processed results are stored in a dedicated `results` branch with "Pending" status
3. A comment is added to your PR showing the processed results
4. Once the PR is merged, the results are marked as "Verified" and merged from the `results` branch into `main`
5. The leaderboard is automatically built and deployed to GitHub Pages
6. The leaderboard UI is updated to include your new data

## Verification Process

Model results go through a two-stage verification process:
1. **Pending**: Results submitted via PR that haven't been reviewed
2. **Verified**: Results that have been reviewed and merged into the main branch

Only verified results are considered official for research comparisons.
