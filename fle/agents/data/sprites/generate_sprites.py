#!/usr/bin/env python3
import sys
from pathlib import Path

from fle.agents.data.sprites.extractors.character import CharacterSpriteExtractor
from fle.agents.data.sprites.extractors.decoratives import DecorativeSpriteExtractor
from fle.agents.data.sprites.extractors.icons import IconSpriteExtractor
from fle.agents.data.sprites.extractors.alerts import AlertSpriteExtractor

# Add the parent directory to Python path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.entities import EntitySpritesheetExtractor
from extractors.resources import ResourceSpriteExtractor
from extractors.terrain import TerrainSpriteExtractor
from extractors.trees import TreeSpriteExtractor


def main():
    """Main entry point"""
    # Use relative paths or environment variables
    base = Path.cwd()  # Current working directory

    # Check if we're in the right directory structure
    if base.name == "sprites" or base.name == "data":
        project_root = base.parent.parent.parent.parent.parent
        if base.name == "sprites":
            project_root = base.parent.parent.parent.parent
    else:
        project_root = base.parent.parent.parent.parent.parent

    # Set up paths relative to project root
    base_input_path = project_root / ".fle" / "spritemaps" / "__base__" / "graphics"
    resources_path = base_input_path / "resources"
    terrain_path = base_input_path / "terrain"
    decoratives_path = base_input_path / "decorative"
    icons_path = base_input_path / "icons"
    alerts_path = icons_path / "alerts"

    entities_path = project_root / ".fle" / "spritemaps"
    output_dir = project_root / ".fle" / "sprites"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project root: {project_root}")
    print(f"Input path: {entities_path}")
    print(f"Output path: {output_dir}")

    # Check if input directories exist
    if not entities_path.exists():
        print(f"Error: Input directory does not exist: {entities_path}")
        print("Run 'fle sprites download' first to download the spritemaps.")
        return

    # Extract icons
    if icons_path.exists():
        print("\n=== Extracting Icon Sprites ===")
        icon = IconSpriteExtractor(str(icons_path), str(output_dir))
        icon.extract_all_icons()
    else:
        print(f"Warning: Icon path not found: {icons_path}")

    # Extract alerts
    if alerts_path.exists():
        print("\n=== Extracting Alert Sprites ===")
        alerts = AlertSpriteExtractor(str(alerts_path), str(output_dir))
        alerts.extract_all_alerts()
    else:
        print(f"Warning: Alerts path not found: {alerts_path}")

    # Extract decoratives
    if decoratives_path.exists():
        print("\n=== Extracting Decorative Sprites ===")
        decoratives = DecorativeSpriteExtractor(str(decoratives_path), str(output_dir))
        decoratives.extract_all_decoratives()
    else:
        print(f"Warning: Decoratives path not found: {decoratives_path}")

    # Extract entities
    if (entities_path / "data.json").exists():
        print("\n=== Extracting Entity Sprites ===")
        entities = EntitySpritesheetExtractor(str(entities_path), str(output_dir))
        entities.extract_all()
    else:
        print("Warning: data.json not found, skipping entity extraction")

    # Extract resources
    if resources_path.exists():
        print("\n=== Extracting Resource Sprites ===")
        resources = ResourceSpriteExtractor(str(resources_path), str(output_dir))
        resources.extract_all_resources()
        resources.create_all_icons()
    else:
        print(f"Warning: Resources path not found: {resources_path}")

    # Extract trees
    if resources_path.exists():
        print("\n=== Extracting Tree Sprites ===")
        trees = TreeSpriteExtractor(str(resources_path), str(output_dir))
        trees.extract_all_trees()

    # Extract terrain
    if terrain_path.exists():
        print("\n=== Extracting Terrain Sprites ===")
        terrain = TerrainSpriteExtractor(str(terrain_path), str(output_dir))
        terrain.extract_all_resources()
        terrain.create_all_icons()
    else:
        print(f"Warning: Terrain path not found: {terrain_path}")

    character_path = (
        base_input_path.parent / "character"
    )  # Assuming character folder is at same level as __base__
    if character_path.exists():
        print("\n=== Extracting Character Sprites ===")
        character = CharacterSpriteExtractor(str(character_path), str(output_dir))
        character.extract_all_character_sprites()
        character.extract_single_sprites()
        character.create_character_mapping()
    else:
        print(f"Warning: Character path not found: {character_path}")

    print("\n=== Extraction Complete ===")


if __name__ == "__main__":
    main()
