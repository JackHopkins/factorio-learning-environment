import os
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv()


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of dictionaries."""
    data = []
    with open(file_path, "r") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def get_task_type(filename: str) -> str:
    """Extract task type from filename."""
    name = filename.replace(".jsonl", "")

    # Remove date suffix
    if "_2025-" in name:
        name = name.split("_2025-")[0]
    elif "_mc_2025-" in name:
        name = name.split("_mc_2025-")[0]

    # Categorize into main types
    if "terrain" in name:
        return "terrain"
    elif "factory" in name:
        return "factory"
    elif "blueprints" in name or name in [
        "entity_name",
        "position_finding",
        "entity_counting",
        "entity_direction",
        "denoising",
        "contrastive_alignment_title",
        "contrastive_alignment_purpose",
    ]:
        return "blueprints"
    else:
        return "other"


def generate_dataset_card(dataset_dir: Path) -> str:
    """Generate a comprehensive dataset card from JSONL files."""

    # Find all JSONL files
    jsonl_files = list(dataset_dir.glob("*.jsonl"))

    # Collect statistics and examples
    stats = {
        "total_samples": 0,
        "splits": {},
        "task_types": defaultdict(int),
        "question_types": defaultdict(int),
    }

    examples = {}

    for jsonl_file in sorted(jsonl_files):
        split_name = jsonl_file.stem
        data = load_jsonl(jsonl_file)

        if not data:
            continue

        # Collect stats
        stats["total_samples"] += len(data)
        stats["splits"][split_name] = len(data)

        # Get task type
        task_type = get_task_type(jsonl_file.name)
        stats["task_types"][task_type] += len(data)

        # Count question types
        for item in data:
            q_type = item.get("question_type", "unknown")
            stats["question_types"][q_type] += 1

        # Store first example
        if data:
            examples[split_name] = data[0]

    # Generate the dataset card with YAML frontmatter
    card = f"""---
license: mit
task_categories:
- visual-question-answering
- image-to-text
language:
- en
tags:
- factorio
- game
- vqa
- spatial-reasoning
- factory-simulation
pretty_name: Factorio Visual Question Answering Dataset
size_categories:
- 1K<n<10K
---

# Factorio Visual Question Answering (VQA) Dataset

## Dataset Description

This dataset contains visual question-answering pairs for the Factorio Learning Environment (FLE). It is designed to train and evaluate vision-language models on understanding Factorio game elements, spatial relationships, and factory designs.

### Dataset Summary

- **Total Samples**: {stats["total_samples"]:,}
- **Number of Splits**: {len(stats["splits"])}
- **Task Categories**: {len(stats["task_types"])}
- **Languages**: English
- **License**: MIT
- **Created**: {datetime.now().strftime("%Y-%m-%d")}

### Task Distribution

| Task Category | Samples |
|--------------|---------|
"""

    for task_type, count in sorted(stats["task_types"].items()):
        card += f"| {task_type.capitalize()} | {count:,} |\n"

    card += """
### Question Types

| Type | Count |
|------|-------|
"""

    for q_type, count in sorted(stats["question_types"].items()):
        card += f"| {q_type} | {count:,} |\n"

    card += """
## Dataset Structure

### Data Splits

Each JSONL file represents a different split focused on specific task types:

| Split Name | Samples | Description |
|------------|---------|-------------|
"""

    # Define task descriptions
    task_descriptions = {
        "terrain_nearest_entity": "Find nearest entities in terrain views",
        "terrain_nearest_resource": "Find nearest resources in terrain views",
        "factory_nearest_entity": "Find nearest entities in factory setups",
        "factory_entity_status": "Identify entity statuses in factories",
        "entity_name": "Identify entity names from blueprints",
        "position_finding": "Find entity positions in blueprints",
        "entity_counting": "Count entities in blueprints",
        "entity_direction": "Determine entity facing directions",
        "denoising": "Identify missing entities (denoising)",
        "contrastive_alignment_title": "Match blueprints to titles",
        "contrastive_alignment_purpose": "Match blueprints to purposes",
    }

    for split_name, count in sorted(stats["splits"].items()):
        base_name = split_name.split("_2025-")[0].replace("_mc", "")
        desc = task_descriptions.get(base_name, "Visual question answering task")
        if "_mc" in split_name:
            desc += " (multiple choice)"
        card += f"| {split_name} | {count:,} | {desc} |\n"

    card += """
### Data Fields

All entries contain these common fields:
- `question` (string): The question text
- `answer` (string): The answer
- `image` (string): Path to the associated image
- `question_type` (string): Type of question (open_ended, multiple_choice, etc.)
- `metadata` (dict): Additional task-specific metadata

### Data Examples

Here are examples from different task types:

"""

    # Add a few diverse examples
    example_splits = [
        "terrain_task",
        "terrain_task_mc",
        "factory_task",
        "factory_task_mc",
        "position_task",
        "position_task_mc",
        "entity_name_task",
        "entity_name_task_mc",
        "contrastive_alignment_title",
        "counting_task",
        "counting_task_mc",
        "direction_task",
        "simple_denoising_blueprint_task",
        "entity_counting",
        "denoising_mc",
        "contrastive_alignment_purpose",
    ]

    for split in example_splits:
        split_match = None
        for split_name in examples:
            if split in split_name:
                split_match = split_name
                break

        if split_match and split_match in examples:
            example = examples[split_match]
            card += f"""#### {split}
```json
{{
  "question": "{example["question"]}",
  "answer": "{example["answer"]}",
  "image": "/blueprints/{{id}}.png"",
  "question_type": "{example.get("question_type", "unknown")}"
}}
```

"""

    card += """## Dataset Creation

### Generation Process

The dataset was generated using the Factorio Learning Environment (FLE) with the following approach:

1. **Terrain Tasks**: Generated by spawning at random coordinates and querying about nearby entities/resources
2. **Factory Tasks**: Created by placing random entities and generating spatial/status questions
3. **Blueprint Tasks**: Used pre-existing blueprint files to generate various question types
4. **Denoising Tasks**: Modified blueprints by removing entities and asking about missing components
5. **Contrastive Tasks**: Paired blueprints with titles/purposes for multiple-choice selection

### Image Information

Images are organized in three directories:
- `blueprints/`: Rendered blueprint images
- `terrain/`: Terrain view captures
- `factory/`: Factory setup images

All images are saved as PNG files for lossless quality.

## Usage

### Loading the Dataset

```python
from datasets import load_dataset

# Load all splits
dataset = load_dataset("Noddybear/fle_vqa")

# Load specific split
terrain_data = load_dataset("Noddybear/fle_vqa", split="terrain_nearest_entity_mc")
```

### Answer Formats

- **Open-ended position answers**: `"Position(x=X, y=Y)"`
- **Multiple choice answers**: Single letter `"a"`, `"b"`, `"c"`, or `"d"`
- **Entity names**: Lowercase with hyphens (e.g., `"transport-belt"`)
- **Directions**: Compass directions (e.g., `"north"`, `"east"`)
- **Counts**: Integer strings (e.g., `"5"`)

## Considerations

- Questions are designed to be answerable from visual information alone
- Multiple choice questions include plausible distractors
- Positions are given in integer game coordinates
- Some images may contain multiple valid entities for "nearest" questions

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{factorio_vqa_2025,
  title={Factorio Visual Question Answering Dataset},
  author={FLE Contributors},
  year={2025},
  publisher={HuggingFace}
}
```
"""

    return card


def main():
    """Generate dataset card and upload to HuggingFace."""
    dataset_dir = Path(
        "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/vqa/dataset"
    )

    # Generate dataset card
    print("Generating dataset card...")
    dataset_card = generate_dataset_card(dataset_dir)

    # Save dataset card
    readme_path = dataset_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(dataset_card)
    print(f"Dataset card saved to {readme_path}")

    # Upload to HuggingFace
    print("\nUploading to HuggingFace...")
    api = HfApi(token=os.getenv("HF_TOKEN"))
    api.upload_large_folder(
        folder_path=str(dataset_dir),
        repo_id="Noddybear/fle_vqa",
        repo_type="dataset",
    )
    print("Upload complete!")


if __name__ == "__main__":
    main()
