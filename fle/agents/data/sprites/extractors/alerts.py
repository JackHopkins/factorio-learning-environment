#!/usr/bin/env python3
"""
Alert sprite extractor for Factorio alert/warning icons
Handles individual alert icon files and renames them consistently
"""

import shutil
from pathlib import Path
from PIL import Image


class AlertSpriteExtractor:
    """Extract and process alert/warning sprites"""

    def __init__(self, alerts_path: str, output_dir: str = "images"):
        self.alerts_path = Path(alerts_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Mapping of original filenames to standardized alert names
        self.alert_mappings = {
            "warning-icon.png": "alert-warning",
            "danger-icon.png": "alert-danger",
            "destroyed-icon.png": "alert-destroyed",
            "electricity-icon-red.png": "alert-no-electricity",
            "electricity-icon-unplugged.png": "alert-disconnected",
            "fluid-icon-red.png": "alert-no-fluid",
            "fuel-icon-red.png": "alert-no-fuel",
            "ammo-icon-red.png": "alert-no-ammo",
            "too-far-from-roboport-icon.png": "alert-no-roboport-coverage",
            "no-building-material-icon.png": "alert-no-building-materials",
            "no-storage-space-icon.png": "alert-no-storage",
            "not-enough-repair-packs-icon.png": "alert-no-repair-packs",
            "not-enough-construction-robots-icon.png": "alert-no-construction-robots",
            "recharge-icon.png": "alert-recharge-needed",
            "logistic-delivery.png": "alert-logistic-delivery",
        }

    def extract_alert_icon(self, original_filename: str, alert_name: str):
        """
        Extract and save an alert icon with standardized naming

        Args:
            original_filename: Original filename in the alerts directory
            alert_name: Standardized alert name for output
        """
        input_path = self.alerts_path / original_filename

        if not input_path.exists():
            print(f"Alert icon not found: {input_path}")
            return

        try:
            # Load the icon
            icon = Image.open(input_path).convert("RGBA")

            # Save with standardized name
            output_filename = f"{alert_name}.png"
            output_path = self.output_dir / output_filename

            icon.save(output_path)
            print(f"Saved alert icon: {output_path} (size: {icon.width}x{icon.height})")

            # Also create a copy with 'icon_' prefix for consistency with other extractors
            icon_output_path = self.output_dir / f"icon_{alert_name}.png"
            icon.save(icon_output_path)
            print(f"Saved icon variant: {icon_output_path}")

        except Exception as e:
            print(f"Error processing {original_filename}: {e}")

    def extract_all_alerts(self):
        """Extract all alert sprites from the alerts directory"""
        print("=== Extracting Alert Sprites ===")

        if not self.alerts_path.exists():
            print(f"Alerts directory not found: {self.alerts_path}")
            return

        # Process mapped alerts
        processed_count = 0
        for original_name, alert_name in self.alert_mappings.items():
            print(f"\nProcessing alert: {original_name} -> {alert_name}")
            self.extract_alert_icon(original_name, alert_name)
            processed_count += 1

        # Check for any unmapped alert files
        unmapped_files = []
        for file_path in self.alerts_path.glob("*.png"):
            if file_path.name not in self.alert_mappings:
                unmapped_files.append(file_path.name)

        if unmapped_files:
            print(f"\nWarning: Found {len(unmapped_files)} unmapped alert files:")
            for filename in unmapped_files:
                print(f"  - {filename}")
                # Process unmapped files with a generic naming scheme
                base_name = filename.replace(".png", "").replace("-icon", "")
                alert_name = f"alert-{base_name}"
                print(f"    Processing as: {alert_name}")
                self.extract_alert_icon(filename, alert_name)
                processed_count += 1

        print(f"\n=== Extracted {processed_count} alert sprites ===")

    def create_alert_composite(self, output_filename: str = "alert-composite.png"):
        """
        Create a composite image showing all alert icons in a grid
        Useful for documentation or overview purposes
        """
        print("\n=== Creating Alert Composite ===")

        # Collect all extracted alert images
        alert_files = list(self.output_dir.glob("alert-*.png"))

        if not alert_files:
            print("No alert files found to create composite")
            return

        # Load all icons and find max dimensions
        icons = []
        max_width = 0
        max_height = 0

        for file_path in sorted(alert_files):
            if "composite" in file_path.name or file_path.name.startswith("icon_"):
                continue

            try:
                icon = Image.open(file_path).convert("RGBA")
                icons.append((file_path.name, icon))
                max_width = max(max_width, icon.width)
                max_height = max(max_height, icon.height)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        if not icons:
            print("No valid icons found for composite")
            return

        # Calculate grid dimensions
        grid_cols = min(8, len(icons))  # Max 8 columns
        grid_rows = (len(icons) + grid_cols - 1) // grid_cols

        # Add padding between icons
        padding = 10
        cell_width = max_width + padding * 2
        cell_height = max_height + padding * 2

        # Create composite image
        composite_width = grid_cols * cell_width
        composite_height = grid_rows * cell_height
        composite = Image.new("RGBA", (composite_width, composite_height), (0, 0, 0, 0))

        # Place icons in grid
        for idx, (filename, icon) in enumerate(icons):
            col = idx % grid_cols
            row = idx // grid_cols

            # Center icon in cell
            x = col * cell_width + padding + (max_width - icon.width) // 2
            y = row * cell_height + padding + (max_height - icon.height) // 2

            composite.paste(icon, (x, y), icon)

        # Save composite
        composite_path = self.output_dir / output_filename
        composite.save(composite_path)
        print(
            f"Saved alert composite: {composite_path} (size: {composite_width}x{composite_height})"
        )
        print(f"Grid: {grid_cols}x{grid_rows}, {len(icons)} icons")

    def generate_alert_categories(self):
        """
        Organize alerts by category and create category-specific composites
        """
        categories = {
            "resource": [
                "no-electricity",
                "no-fluid",
                "no-fuel",
                "no-ammo",
                "no-building-materials",
            ],
            "robot": [
                "no-roboport-coverage",
                "no-construction-robots",
                "no-repair-packs",
                "recharge-needed",
            ],
            "status": ["warning", "danger", "destroyed", "disconnected"],
            "logistics": ["no-storage", "logistic-delivery"],
        }

        print("\n=== Organizing Alerts by Category ===")

        for category_name, alert_types in categories.items():
            print(f"\nCategory: {category_name}")

            # Create category subdirectory
            category_dir = self.output_dir / "alerts" / category_name
            category_dir.mkdir(exist_ok=True, parents=True)

            # Copy relevant alerts to category directory
            copied_count = 0
            for alert_type in alert_types:
                source_path = self.output_dir / f"alert-{alert_type}.png"
                if source_path.exists():
                    dest_path = category_dir / f"alert-{alert_type}.png"
                    shutil.copy2(source_path, dest_path)
                    print(f"  - Copied: alert-{alert_type}.png")
                    copied_count += 1
                else:
                    print(f"  - Warning: alert-{alert_type}.png not found")

            print(f"  Total: {copied_count} alerts in {category_name} category")

    def create_alert_mapping_json(self):
        """
        Create a JSON mapping file for alert icons
        Useful for game integration
        """
        import json

        mapping = {
            "alerts": {},
            "categories": {
                "resource": [
                    "no-electricity",
                    "no-fluid",
                    "no-fuel",
                    "no-ammo",
                    "no-building-materials",
                ],
                "robot": [
                    "no-roboport-coverage",
                    "no-construction-robots",
                    "no-repair-packs",
                    "recharge-needed",
                ],
                "status": ["warning", "danger", "destroyed", "disconnected"],
                "logistics": ["no-storage", "logistic-delivery"],
            },
        }

        # Build alert mappings
        for original, standardized in self.alert_mappings.items():
            alert_key = standardized.replace("alert-", "")
            mapping["alerts"][alert_key] = {
                "filename": f"{standardized}.png",
                "icon_filename": f"icon_{standardized}.png",
                "original": original,
            }

        # Save mapping
        mapping_path = self.output_dir / "alert_mapping.json"
        with open(mapping_path, "w") as f:
            json.dump(mapping, f, indent=2, sort_keys=True)

        print(f"\nCreated alert mapping: {mapping_path}")
        print(f"Total alerts mapped: {len(mapping['alerts'])}")


def main():
    """Main entry point for alert extraction"""
    import sys

    # Default paths - adjust as needed
    alerts_path = ".fle/spritemaps/__base__/graphics/icons/alerts"
    output_dir = ".fle/sprites"

    # Allow command line overrides
    if len(sys.argv) > 1:
        alerts_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print(f"Alerts path: {alerts_path}")
    print(f"Output path: {output_dir}")

    # Create extractor and run
    extractor = AlertSpriteExtractor(alerts_path, output_dir)

    # Extract all alerts
    extractor.extract_all_alerts()

    # Create composite image
    extractor.create_alert_composite()

    # Organize by categories
    extractor.generate_alert_categories()

    # Create mapping file
    extractor.create_alert_mapping_json()

    print("\n=== Alert Extraction Complete ===")


if __name__ == "__main__":
    main()
