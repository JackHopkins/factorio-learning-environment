---
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

- **Total Samples**: 4,522
- **Number of Splits**: 14
- **Task Categories**: 4
- **Languages**: English
- **License**: MIT
- **Created**: 2025-08-05

### Task Distribution

| Task Category | Samples |
|--------------|---------|
| Blueprints | 4 |
| Factory | 298 |
| Other | 3,980 |
| Terrain | 240 |

### Question Types

| Type | Count |
|------|-------|
| multiple_choice | 1,775 |
| open_ended | 1,763 |
| unknown | 984 |

## Dataset Structure

### Data Splits

Each JSONL file represents a different split focused on specific task types:

| Split Name | Samples | Description |
|------------|---------|-------------|
| contrastive_alignment_purpose | 3 | Match blueprints to purposes |
| contrastive_alignment_title | 1 | Match blueprints to titles |
| counting_task | 500 | Visual question answering task |
| counting_task_mc | 500 | Visual question answering task (multiple choice) |
| direction_task | 480 | Visual question answering task |
| entity_name_task | 500 | Visual question answering task |
| entity_name_task_mc | 500 | Visual question answering task (multiple choice) |
| factory_task | 144 | Visual question answering task |
| factory_task_mc | 154 | Visual question answering task (multiple choice) |
| position_task | 500 | Visual question answering task |
| position_task_mc | 500 | Visual question answering task (multiple choice) |
| simple_denoising_blueprint_task | 500 | Visual question answering task |
| terrain_task | 119 | Visual question answering task |
| terrain_task_mc | 121 | Visual question answering task (multiple choice) |

### Data Fields

All entries contain these common fields:
- `question` (string): The question text
- `answer` (string): The answer
- `image` (string): Path to the associated image
- `question_type` (string): Type of question (open_ended, multiple_choice, etc.)
- `metadata` (dict): Additional task-specific metadata

### Data Examples

Here are examples from different task types:

#### terrain_task
```json
{
  "question": "What is the position of the nearest iron-ore to you?",
  "answer": "Position(x=-15.5 y=-50.5)",
  "image": "/blueprints/{id}.png"",
  "question_type": "open_ended"
}
```

#### terrain_task_mc
```json
{
  "question": "What is the position of the nearest iron-ore to you?
Provide the correct letter and nothing else.
a) Position(x=-15.5 y=-50.5)
b) Position(x=40.5 y=-82.5)
c) Position(x=60.5 y=-54.5)
d) Position(x=-28.5 y=-61.5)",
  "answer": "a",
  "image": "/blueprints/{id}.png"",
  "question_type": "multiple_choice"
}
```

#### factory_task
```json
{
  "question": "What is the position of the nearest offshore pump?",
  "answer": "Position(x=-19.5, y=29.5)",
  "image": "/blueprints/{id}.png"",
  "question_type": "open_ended"
}
```

#### factory_task_mc
```json
{
  "question": "What is the position of the nearest assembling machine 2?
Provide the correct letter and nothing else.
a) Position(x=-13.5, y=6.5)
b) Position(x=-23.5, y=27.5)
c) Position(x=-1.5, y=27.5)
d) Position(x=16.5, y=-28.5)",
  "answer": "d",
  "image": "/blueprints/{id}.png"",
  "question_type": "multiple_choice"
}
```

#### position_task
```json
{
  "question": "What is the position of the express-underground-belt that is located 1 tile east of the express-transport-belt at position Position(x=3.0, y=16.0)?",
  "answer": "Position(x=4.0, y=16.0)",
  "image": "/blueprints/{id}.png"",
  "question_type": "open_ended"
}
```

#### position_task_mc
```json
{
  "question": "What is the position of the express-transport-belt that is orthogonally adjacent to the express-underground-belt at position Position(x=4.0, y=16.0)? (Note: If there are multiple such belts, select the one with the smallest y-coordinate, then smallest x-coordinate if tied)
A) Position(x=4.0, y=18.0)
B) Position(x=3.0, y=16.0)
C) Position(x=4.0, y=17.0)
D) Position(x=5.0, y=16.0)",
  "answer": "C",
  "image": "/blueprints/{id}.png"",
  "question_type": "multiple_choice"
}
```

#### entity_name_task
```json
{
  "question": "What entity is located at Position(x=4.0, y=0.0)?",
  "answer": "An express-transport-belt",
  "image": "/blueprints/{id}.png"",
  "question_type": "open_ended"
}
```

#### entity_name_task_mc
```json
{
  "question": "What entity is located at Position(x=0.0, y=21.0)?
   A) express-underground-belt
   B) express-transport-belt
   C) express-splitter
   D) fast-transport-belt",
  "answer": "B",
  "image": "/blueprints/{id}.png"",
  "question_type": "multiple_choice"
}
```

#### contrastive_alignment_title
```json
{
  "question": "What is the best title for this blueprint?
A) 13-to-11 Express Belt Balancer
B) 13-to-11 Express Belt Balancer
C) Express Belt 1110 Signal Balancer
D) 11-to-10 Express Belt Balancer",
  "answer": "D",
  "image": "/blueprints/{id}.png"",
  "question_type": "unknown"
}
```

#### counting_task
```json
{
  "question": "How many express transport belts are facing either north or south in this blueprint?",
  "answer": "81",
  "image": "/blueprints/{id}.png"",
  "question_type": "open_ended"
}
```

#### counting_task_mc
```json
{
  "question": "How many express-transport-belts are facing north in this blueprint?
   A) 70
   B) 68
   C) 72
   D) 74",
  "answer": "A",
  "image": "/blueprints/{id}.png"",
  "question_type": "multiple_choice"
}
```

#### direction_task
```json
{
  "question": "What direction is the express-transport-belt facing at Position(x=2.0, y=0.0)?",
  "answer": "Direction.NORTH",
  "image": "/blueprints/{id}.png"",
  "question_type": "unknown"
}
```

#### simple_denoising_blueprint_task
```json
{
  "question": "Name the missing entity at: Position(x=2.0, y=14.0)",
  "answer": "express-transport-belt",
  "image": "/blueprints/{id}.png"",
  "question_type": "unknown"
}
```

#### contrastive_alignment_purpose
```json
{
  "question": "What is the purpose of this blueprint?
A) Evenly distributes items from 11 input belts to 11 output belts, ensuring balanced throughput across all lanes. Essential for maintaining consistent item flow in large-scale production setups.
B) Converts excess light oil from refineries into solid fuel for trains, boilers, or rocket fuel production. Features 34 chemical plants with integrated belt output and buffer chests for continuous operation.
C) Evenly distributes items across 12 express transport belt lanes. Essential for maintaining consistent throughput in large-scale production setups where multiple belt lanes need equal item distribution.
D) Evenly distributes items across 10 express transport belts, ensuring balanced throughput for large-scale production lines. Essential for maintaining consistent item flow in high-volume factories.",
  "answer": "A",
  "image": "/blueprints/{id}.png"",
  "question_type": "unknown"
}
```

## Dataset Creation

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
