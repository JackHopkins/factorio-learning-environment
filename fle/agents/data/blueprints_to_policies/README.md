## Blueprint Policies Module

A system for converting Factorio blueprints into executable build policies using various advanced code generation techniques.

### Overview

This module transforms Factorio blueprint JSON files into optimized Python code that can recreate the blueprint in-game. It supports multiple approaches:

- Basic entity placement with coordinates
- Transport belt connection optimization
- Relative entity placement using reference points
- Advanced placement using ML-generated policies

### Core Components

#### Blueprint Analysis

- `blueprint_analyzer.py`: Base analyzer for converting blueprints to placement instructions
- `blueprint_analyzer_with_connect.py`: Adds transport belt connection optimization
- `blueprint_analyzer_with_place_next_to.py`: Implements relative entity placement
- `blueprint_refactor.py`: Uses ML models to optimize and refactor placement code

#### Data Processing

- `blueprint_metadata_generator.py`: Generates metadata and embeddings for blueprints
- `parse_blueprints.py`: Parses and categorizes blueprint files
- `factorio_school.py`: Scrapes blueprints from factorio.school
- `trajectory_generator.py`: Creates optimized build sequences

#### State Management

- `loop_generator.py`: Handles repeatable build patterns
- `processing_state.py`: Tracks blueprint processing status

### Key Features

- Entity pattern detection and grouping
- Coordinate normalization and origin calculation
- Bounding box optimization
- Path planning for efficient construction
- Multi-model code generation with GPT-4, Claude, and DeepSeek
- Parallel processing support using AWS ECS

### Usage

1. Place blueprint JSON files in `blueprints/` subdirectories
2. Use corresponding analyzer class for desired optimization:
```python
analyzer = BlueprintAnalyzer(blueprint)  # Basic placement
analyzer = BlueprintAnalyzerWithConnect(blueprint)  # With belt optimization 
analyzer = BlueprintAnalyzerWithPlaceNextTo(blueprint)  # With relative placement
```

3. Generate and execute placement code:
```python
code = analyzer.generate_program()
instance.eval_with_error(code)
```

### Configuration

- `RefactorConfig`: Controls ML-based optimization settings
- `ServerConfig`: Manages Factorio server connections
- Environment variables:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `DB_PASSWORD`

### Metrics & Verification

The system tracks:
- Entity placement accuracy
- Code optimization ratios
- Build sequence efficiency
- Model performance metrics

Verification ensures generated code produces identical entity layouts to original blueprints.