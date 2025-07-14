# BPRenderer Python Port

A Python port of the Factorio Blueprint Renderer for backend rendering using Pillow.

## Installation

```bash
pip install -r requirements.txt
```

## Directory Structure

```
BPRenderer/
├── bprenderer.py          # Main renderer module
├── renderers/             # Entity renderer modules
│   ├── __init__.py       # Base renderer
│   ├── transport_belt.py
│   ├── inserter.py
│   ├── pipe.py
│   ├── assembling_machine.py
│   └── ...               # Other entity renderers
├── images/                # Entity sprite images (PNG files)
├── data.json             # Factorio game data
├── sample_blueprint.txt  # Sample blueprint for testing
└── requirements.txt
```

## Usage

### Basic Usage

```python
from bprenderer import parse_blueprint, load_game_data, Blueprint, ImageResolver

# Load game data
game_data, game_recipes = load_game_data("data.json")

# Parse blueprint string
with open("sample_blueprint.txt", "r") as f:
    blueprint_string = f.read().strip()

blueprint_json = parse_blueprint(blueprint_string)
blueprint = Blueprint(blueprint_json, game_data, game_recipes)

# Setup image resolver
image_resolver = ImageResolver("images")

# Render blueprint
size = blueprint.get_size()
scaling = 32
width = (size['width'] + 2) * scaling
height = (size['height'] + 2) * scaling

image = blueprint.render(width, height, image_resolver)
image.save("output.png")
```

### Command Line Usage

```bash
python bprenderer.py
```

This will render the sample blueprint to `output.png`.

## Adding New Entity Renderers

To add support for a new entity type:

1. Create a new module in the `renderers/` directory
2. Implement the required functions:
   - `render(entity, grid, image_resolver)` - Main rendering function
   - `render_shadow(entity, grid, image_resolver)` - Shadow rendering (optional)
   - `get_key(entity, grid)` - Cache key generation
   - `get_size(entity)` - Entity size in tiles

3. Add the entity mapping to the `RENDERERS` dictionary in `bprenderer.py`

Example renderer:

```python
# renderers/my_entity.py
from typing import Dict, Tuple, Optional, Callable
from PIL import Image

def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    direction = entity.get('direction', 0)
    return image_resolver(f"{entity['name']}_{direction}")

def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    return None  # No shadow

def get_key(entity: Dict, grid) -> str:
    return str(entity.get('direction', 0))

def get_size(entity: Dict) -> Tuple[float, float]:
    return (2, 2)  # 2x2 entity
```

## Notes

- This port focuses on backend rendering using Pillow instead of Canvas
- Font rendering is simplified (grid numbers not rendered by default)
- Not all entity renderers are implemented - add as needed
- The image files (`images/` directory) need to be generated separately using the original spritesheet.js script

## Differences from Original

- Uses Pillow instead of node-canvas
- Python-style module organization
- Simplified some rendering features for initial port
- Type hints for better code clarity