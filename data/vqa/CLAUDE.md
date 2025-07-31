# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Visual Question Answering (VQA) module for the Factorio Learning Environment (FLE). The goal is to train visual encoders for Factorio using text representations as ground truth.

## Key Commands

### Running Tasks
```bash
# Run all VQA tasks
python tasks.py

# Run specific task type
python tasks/basic/task.py
python tasks/spatial_reasoning/task.py
python tasks/denoising/task.py
# etc.
```

### Installation
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

1. **Blueprint Loading**: Blueprints are loaded from `.fle/blueprints/` via `utils.find_blueprints_dir()`
2. **Rendering**: Use `instance.namespace._render(blueprint=blueprint)` to render blueprints to images
3. **Dataset Generation**: `dataset.py` creates `MemoryDataset` from blueprints
4. **Task System**: Each task type has:
   - `task.py`: Task definitions using `@task` decorator
   - `solver.py`: Question generation logic using `@solver` decorator
   - `templates/`: Jinja2 templates for prompts
5. **Common Solvers**: `common_solvers.py` contains:
   - `validate_qa_answerability()`: Validates if questions are answerable and unambiguous
   - `convert_directions_to_compass()`: Converts numeric directions to compass directions
6. **Direction Utilities**: `direction_utils.py` provides Direction enum and conversion utilities

### Task Types

1. **Basic** (`tasks/basic/`)
   - Entity name prediction from position
   - Position prediction from entity name
   - Entity counting

2. **Spatial Reasoning** (`tasks/spatial_reasoning/`)
   - Relative entity positions
   - Distance calculations
   - Spatial context questions

3. **State Prediction** - **NOT IMPLEMENTED**
   - Should predict entity states from live factories
   - Needs access to live game state, not just blueprints

4. **Denoising** (`tasks/denoising/`)
   - Remove/modify/replace entities
   - Predict original entity

5. **Action Prediction** (`tasks/action_prediction/`)
   - Predict next construction action
   - Construction order questions

6. **Productivity Planning** (`tasks/productivity_planning/`)
   - Throughput predictions
   - Bottleneck analysis
   - Optimization suggestions

7. **Contrastive Alignment** (`tasks/contrastive_alignment/`)
   - Blueprint title/purpose matching
   - Multiple choice format

### Data Flow

1. Blueprint JSON → `raw_blueprint_dataset()` → Task
2. Task uses solver to generate questions
3. Solver renders blueprint: `instance.namespace._render(blueprint=blueprint)`
4. Image saved to `dataset/images/{blueprint_name}/{variant_hash}.jpg`
5. **Validation Pipeline**:
   - `convert_directions_to_compass()`: Converts numeric directions (0,2,4,6) to compass (north/east/south/west)
   - `validate_qa_answerability()`: Validates questions are answerable and unambiguous, regenerates if needed
6. QA pairs collected by `VQAPairsHook`
7. Results saved as JSONL in `dataset/`

### Key Integration Points

- **FLE Instance**: Create with `create_factorio_instance()` from `fle.agents.data.screenshots_from_run`
- **Rendering**: Returns `RenderedImage` object, save with `.save(path)`
- **Image IDs**: Use folder structure `/dataset/images/{blueprint_name}/{variant_hash}` with clean blueprint names and variant-specific hashes
- **Hooks**: `VQAPairsHook` automatically serializes QA pairs after evaluation

### Adding New Task Types

1. Create directory: `tasks/new_task_type/`
2. Create `task.py` with `@task` decorated functions
3. Create `solver.py` with `@solver` decorated question generators
4. Add templates in `templates/` if needed
5. Update `tasks/__init__.py` to export new tasks
6. Add normalization method in `hook.py` for new QA format

### Important Notes

- **State Prediction tasks** need live game state, not implemented yet
- **Direction Handling**: All tasks now convert numeric directions to compass directions automatically
- **Question Validation**: All generated questions are validated for answerability and clarity
- **Images** are saved with organized folder structure `{blueprint_name}/{variant_hash}.jpg` for better organization
- **QA Pairs** are normalized to consistent format in `hook.py`
- **Framework**: Use `inspect_ai` framework for task/solver definitions
- **Validation Steps**: Always include `convert_directions_to_compass()` and `validate_qa_answerability()` in solver pipelines