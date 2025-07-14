import json
from pathlib import Path

from data.sprites.renderer import load_game_data, ImageResolver, parse_blueprint, Renderer


def render_blueprints_from_directory(blueprints_dir: str, output_dir: str = None, show_images: bool = True):
    """
    Render all JSON blueprint files from a directory

    Args:
        blueprints_dir: Directory containing JSON blueprint files
        output_dir: Optional directory to save rendered images (default: blueprints_dir/rendered)
        show_images: Whether to display images on screen (default: True)
    """
    blueprints_path = Path(blueprints_dir)

    if not blueprints_path.exists():
        print(f"Error: Blueprint directory not found: {blueprints_dir}")
        return

    # Set up output directory
    if output_dir is None:
        output_path = blueprints_path / "rendered"
    else:
        output_path = Path(output_dir)

    output_path.mkdir(exist_ok=True)

    # Set up paths for resources
    sprites_dir = Path(".fle/sprites")

    # Try to import the enhanced resolver
    try:
        from basis_image_resolver import BasisImageResolver
        print("Using BasisImageResolver for .basis file support")
        base = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/rendering"
        # Load game data
        game_data, game_recipes = load_game_data(f"{base}/data.json")
        image_resolver = ImageResolver(".fle/sprites")
    except ImportError:
        print("BasisImageResolver not found, using simple PNG resolver")
        print("Place PNG files in 'images' directory")
        # Fallback to simple resolver
        game_data, game_recipes = load_game_data("data.json")
        image_resolver = ImageResolver(str(sprites_dir))

    # Find all JSON files
    json_files = list(blueprints_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {blueprints_dir}")
        return

    print(f"Found {len(json_files)} blueprint files to render")

    # Process each blueprint
    successful = 0
    failed = 0

    for json_file in json_files:
        try:
            print(f"\nProcessing: {json_file.name}")

            # Load the JSON file
            with open(json_file, 'r') as f:
                blueprint_data = json.load(f)

            # Handle different blueprint formats
            if 'blueprint' in blueprint_data:
                blueprint_content = blueprint_data['blueprint']
            elif 'entities' in blueprint_data:
                blueprint_content = blueprint_data
            else:
                # Try to parse as blueprint string
                if isinstance(blueprint_data, str):
                    parsed = parse_blueprint(blueprint_data)
                    blueprint_content = parsed.get('blueprint', parsed)
                else:
                    print(f"  Warning: Unknown blueprint format in {json_file.name}")
                    failed += 1
                    continue

            # Create blueprint object
            blueprint = Renderer(blueprint_content, game_data, game_recipes, sprites_dir)

            # Calculate render size
            size = blueprint.get_size()
            if size['width'] == 0 or size['height'] == 0:
                print(f"  Warning: Blueprint has no entities to render")
                failed += 1
                continue

            scaling = 32
            width = min((size['width'] + 2) * scaling, 2048)  # Cap max width
            height = min((size['height'] + 2) * scaling, 2048)  # Cap max height

            # Render the blueprint
            image = blueprint.render(width, height, image_resolver)

            # Save the image
            output_filename = json_file.stem + ".png"
            output_file = output_path / output_filename
            image.save(output_file)
            print(f"  Rendered to: {output_file} ({width}x{height})")

            # Display the image if requested
            if show_images:
                image.show()

            successful += 1

        except Exception as e:
            print(f"  Error processing {json_file.name}: {str(e)}")
            failed += 1

    print(f"\n=== Summary ===")
    print(f"Successfully rendered: {successful}")
    print(f"Failed: {failed}")
    print(f"Output directory: {output_path}")


def main():
    """Main function to render all blueprints in the specified directory"""
    blueprints_dir = "fle/agents/data/blueprints_to_policies/blueprints/other"

    # Render all blueprints
    # Set show_images=False if you don't want them to pop up on screen
    render_blueprints_from_directory(
        blueprints_dir=blueprints_dir,
        output_dir=None,  # Will create 'rendered' subdirectory
        show_images=True  # Set to False to just save without displaying
    )


if __name__ == "__main__":
    main()