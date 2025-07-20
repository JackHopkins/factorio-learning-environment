# Factorio Blueprint VQA Dataset

This package creates Visual Question Answering (VQA) datasets from Factorio game blueprints using the Inspect AI framework.

## Overview

The system takes Factorio blueprint JSON files, renders them as images using the Factorio Learning Environment (FLE), generates relevant questions about the blueprints, and creates a comprehensive VQA dataset suitable for training and evaluating vision-language models.

## Components

### 1. Blueprint Loader (`blueprint_loader.py`)
- Loads and parses Factorio blueprint JSON files
- Provides utilities for filtering blueprints by complexity
- Analyzes blueprint structure and entity counts
- Categorizes entities into functional groups

### 2. Blueprint Renderer (`blueprint_renderer.py`)
- Renders blueprint JSON files to images using the FLE environment
- Handles entity placement and visualization
- Supports batch rendering of multiple blueprints
- Manages the Factorio game instance lifecycle

### 3. Question Generator (`question_generator.py`)
- Generates diverse VQA questions for blueprints
- Supports multiple question types:
  - **Counting**: "How many inserters are there?"
  - **Existence**: "Is there a gun turret in this blueprint?"
  - **Comparison**: "Are there more belts than inserters?"
  - **Spatial**: "What is the width of this blueprint?"
  - **Functional**: "Is this a mining setup?"

### 4. Inspect Solver (`inspect_solver.py`)
- Implements Inspect AI solver for blueprint VQA tasks
- Provides evaluation framework for vision-language models
- Creates Inspect AI compatible datasets
- Includes blueprint analysis tools

### 5. Dataset Pipeline (`dataset_pipeline.py`)
- Complete end-to-end pipeline for dataset generation
- Orchestrates all components
- Generates multiple output formats (JSON, CSV, Inspect AI)
- Provides comprehensive statistics and metadata

## Installation

1. Ensure you have the Factorio Learning Environment (FLE) installed
2. Install the Inspect AI framework:
   ```bash
   uv add inspect-ai
   ```
3. The VQA dataset package is located in the `vqa_dataset/` directory

## Usage

### Quick Start

Run the complete pipeline:

```bash
python vqa_dataset/dataset_pipeline.py \
    --blueprints-dir fle/agents/data/blueprints_to_policies/blueprints \
    --output-dir vqa_output \
    --max-blueprints 50 \
    --questions-per-blueprint 8
```

### Command Line Options

- `--blueprints-dir`: Directory containing blueprint JSON files
- `--output-dir`: Output directory for generated dataset
- `--max-blueprints`: Maximum number of blueprints to process
- `--min-entities`: Minimum entities per blueprint (filter)
- `--max-entities`: Maximum entities per blueprint (filter)
- `--questions-per-blueprint`: Number of questions per blueprint
- `--no-render`: Skip image rendering (faster for testing)
- `--blueprint-subdirs`: Subdirectories to process (default: example, other)

### Programmatic Usage

```python
import asyncio
from vqa_dataset import VQADatasetPipeline

async def create_dataset():
    pipeline = VQADatasetPipeline(
        blueprints_dir="path/to/blueprints",
        output_dir="output"
    )
    
    results = await pipeline.run_pipeline(
        max_blueprints=100,
        questions_per_blueprint=10,
        render_images=True
    )
    
    print(f"Generated {results['questions_count']} questions")

asyncio.run(create_dataset())
```

### Individual Components

```python
# Load blueprints
from vqa_dataset import BlueprintLoader
loader = BlueprintLoader("blueprints/")
blueprints = loader.load_all_blueprints(['example'])

# Generate questions
from vqa_dataset import QuestionGenerator
generator = QuestionGenerator()
questions = generator.generate_questions_batch(blueprints)

# Analyze blueprints
from vqa_dataset import FactorioBlueprintAnalyzer
analyzer = FactorioBlueprintAnalyzer()
results = analyzer.run_evaluation("blueprints/", max_blueprints=10)
```

## Output Formats

The pipeline generates several output files:

1. **vqa_dataset.json**: Complete dataset in JSON format
2. **vqa_dataset.csv**: Dataset in CSV format for easy analysis
3. **inspect_dataset.json**: Inspect AI compatible dataset
4. **blueprint_metadata.json**: Detailed blueprint metadata
5. **statistics.json**: Comprehensive dataset statistics
6. **pipeline_results.json**: Pipeline execution summary

### Example Dataset Entry

```json
{
  "question": "How many electric mining drills are there?",
  "answer": "4",
  "question_type": "counting",
  "blueprint_name": "example/miner_cycle.json",
  "image_path": "rendered_images/example_miner_cycle.png",
  "metadata": {
    "entity_count": 4,
    "unique_types": 1
  }
}
```

## Question Types

### Counting Questions
- Count specific entity types
- Count total entities
- Count unique entity types
- Count by functional category

### Existence Questions
- Check for specific entities
- Check for entity categories
- Threshold-based existence checks

### Comparison Questions
- Compare entity counts
- Identify most common entities

### Spatial Questions
- Blueprint dimensions
- Entity positions
- Spatial relationships

### Functional Questions
- Identify factory type
- Check for specific setups
- Analyze functional patterns

## Testing

Run the test suite:

```bash
python test_vqa_system.py
```

This will test all components and create sample outputs.

## Supported Entity Types

The system recognizes and categorizes these Factorio entities:

- **Mining**: electric-mining-drill, burner-mining-drill
- **Production**: assembling-machine-1/2/3
- **Smelting**: stone-furnace, steel-furnace, electric-furnace
- **Transport**: transport-belt, fast-transport-belt, express-transport-belt
- **Insertion**: inserter, fast-inserter, stack-inserter, filter-inserter
- **Power**: steam-engine, steam-turbine, solar-panel, nuclear-reactor
- **Poles**: small-electric-pole, medium-electric-pole, big-electric-pole
- **Defense**: gun-turret, laser-turret, artillery-turret
- **And many more...**

## Blueprint Sources

Blueprints are loaded from these subdirectories:
- `balancing/`: Belt balancer designs
- `other/`: General factory blueprints
- `example/`: Simple example blueprints
- `decoded/`: Additional community blueprints

## Performance Considerations

- Image rendering is the most time-consuming step
- Use `--no-render` for faster testing
- Filter blueprints by entity count to manage complexity
- Process blueprints in batches for memory efficiency

## Integration with Inspect AI

The system creates Inspect AI compatible datasets that can be used with the evaluation framework:

```python
from inspect_ai import eval
from vqa_dataset.inspect_solver import factorio_blueprint_vqa

# Run evaluation
results = eval(
    factorio_blueprint_vqa(max_blueprints=50),
    model="anthropic/claude-3-5-sonnet-20241022"
)
```

## Future Enhancements

- Support for more complex blueprint analysis
- Additional question types and templates
- Multi-modal question generation
- Integration with more vision-language models
- Blueprint modification and comparison tasks

## Contributing

To add new question types:
1. Add templates to `QuestionGenerator._load_question_templates()`
2. Implement corresponding answer functions
3. Test with various blueprint types

To support new entity types:
1. Add to `COMMON_ENTITY_TYPES` in `blueprint_loader.py`
2. Add prototype mapping in `blueprint_renderer.py`
3. Update question templates as needed