#!/usr/bin/env python3
"""
Python port of spritesheet.js for extracting Factorio sprites (https://github.com/BlooperDB/BPRenderer)
Handles complex sprite extraction including multi-layer sprites, rotations, and combinations
"""

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw,ImageChops
from typing import Dict, List, Optional, Tuple, Any

TILE_PX = 32

class EntitySpritesheetExtractor:
    """Extract and process Factorio sprites from game data"""

    def __init__(self, data_path: str, output_dir: str = "images"):
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Create cache directory for transcoded basis files
        self.cache_dir = self.data_path / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Load game data
        with open(self.data_path / "data.json", 'r') as f:
            full_data = json.load(f)
            # Handle both 'raw' and 'entities' formats
            # if 'items' in full_data:
            #     self.data = full_data['items']
            if 'entities' in full_data:
               self.data = full_data['entities']
            else:
                self.data = full_data

        self.directions = ['north', 'east', 'south', 'west']


    def get_file(self, path: str) -> Image.Image:
        """Load image file from path"""
        # Remove ALL __ prefixes (global replace) to match JavaScript
        clean_path = path
        while "__" in clean_path:
            clean_path = clean_path.replace("__", "")

        # If path starts with "base/", we need to map it to "__base__/"
        if clean_path.startswith("base/"):
            file_path = self.data_path / "__base__" / clean_path[5:]  # Remove "base/"
        else:
            file_path = self.data_path / clean_path

        # First, check if the file exists as-is (could be .png or .basis)
        if file_path.exists():
            if file_path.suffix == '.basis':
                return self._load_basis_file(file_path)
            else:
                return Image.open(file_path).convert('RGBA')

        # If no extension, try .basis first, then .png
        if file_path.suffix == '':
            basis_path = file_path.with_suffix('.basis')
            if basis_path.exists():
                return self._load_basis_file(basis_path)

            png_path = file_path.with_suffix('.png')
            if png_path.exists():
                return Image.open(png_path).convert('RGBA')

        # If the original path has .png extension but doesn't exist, try .basis
        if file_path.suffix == '.png' and not file_path.exists():
            basis_path = file_path.with_suffix('.basis')
            if basis_path.exists():
                return self._load_basis_file(basis_path)

        raise FileNotFoundError(f"Image not found: {file_path} (tried .basis and .png)")

    def _load_basis_file(self, basis_path: Path) -> Image.Image:
        """Load a basis file, transcoding if necessary"""
        # Check cache first
        cache_key = str(basis_path).replace('/', '_').replace('.basis', '')
        cached_png = self.cache_dir / f"{cache_key}.png"

        if not cached_png.exists():
            # Transcode basis to PNG
            if not self._transcode_basis_to_png(basis_path, cached_png):
                raise FileNotFoundError(f"Failed to transcode: {basis_path}")

        return Image.open(cached_png).convert('RGBA')

    def _transcode_basis_to_png(self, basis_path: Path, output_path: Path) -> bool:
        """
        Transcode a .basis file to PNG using basisu

        Args:
            basis_path: Path to the .basis file
            output_path: Path where PNG should be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create temporary directory for basisu output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Run basisu transcoder
                cmd = ["basisu", "-unpack", str(basis_path)]
                result = subprocess.run(
                    cmd,
                    cwd=temp_path,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"basisu failed for {basis_path.name}: {result.stderr}")
                    return False

                # Find the generated RGBA PNG (best quality)
                possible_patterns = [
                    "*_unpacked_rgba_BC7_RGBA_0_0000.png",
                    "*_unpacked_rgba_BC3_RGBA_0_0000.png",
                    "*_unpacked_rgba_ETC2_RGBA_0_0000.png",
                    "*_unpacked_rgba_*_0_0000.png",
                ]

                generated_png = None
                for pattern in possible_patterns:
                    matches = list(temp_path.glob(pattern))
                    if matches:
                        generated_png = matches[0]
                        break

                if not generated_png or not generated_png.exists():
                    print(f"No suitable PNG generated from {basis_path}")
                    return False

                # Copy to output location
                shutil.copy2(generated_png, output_path)
                return True

        except Exception as e:
            print(f"Error transcoding {basis_path}: {e}")
            return False

    def save_canvas(self, path: str, image: Image.Image):
        """Save image to file"""
        output_path = self.output_dir / path
        output_path.parent.mkdir(exist_ok=True, parents=True)
        image.save(output_path)
        print(f"Saved: {output_path}")

    def combine_canvas(self, first: Image.Image, second: Image.Image) -> Image.Image:
        """Combine two images, centering both"""
        width = max(first.width, second.width)
        height = max(first.height, second.height)

        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        # Center first image - use floor division to match JavaScript Math.floor
        x1 = (width - first.width) // 2
        y1 = (height - first.height) // 2
        result.paste(first, (x1, y1), first)

        # Center second image - use floor division to match JavaScript Math.floor
        x2 = (width - second.width) // 2
        y2 = (height - second.height) // 2
        result.paste(second, (x2, y2), second)

        return result

    def rotate_canvas(self, image: Image.Image, degrees: float) -> Image.Image:
        """Rotate image by degrees"""
        # PIL rotates counter-clockwise, canvas rotates clockwise, so negate
        return image.rotate(-degrees, expand=False, fillcolor=(0, 0, 0, 0))

    def extend_canvas(self, image: Image.Image, up: int = 0, right: int = 0,
                      down: int = 0, left: int = 0) -> Image.Image:
        """Extend canvas in specified directions"""
        new_width = image.width + right + left
        new_height = image.height + up + down

        result = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        result.paste(image, (left, up), image)

        return result

    def crop_image(self, image: Image.Image, x: int, y: int,
                   width: int, height: int) -> Image.Image:
        """Crop image to specified rectangle"""
        return image.crop((x, y, x + width, y + height))

    def process_picture(self, picture: Dict, x_offset: int = 0, y_offset: int = 0,
                        width_x: Optional[int] = None, height_y: Optional[int] = None) -> Optional[Image.Image]:
        """Process a picture definition from game data"""
        if picture is None:
            return None

        # Skip runtime tint and filenames (animated)
        if picture.get('apply_runtime_tint') is not None or picture.get('filenames') is not None:
            return None

        if 'filename' not in picture:
            return None

        try:
            image = self.get_file(picture['filename'])
        except FileNotFoundError:
            print(f"Warning: Could not load {picture['filename']}")
            return None

        # Get dimensions
        width = width_x or picture.get('width', image.width)
        height = height_y or picture.get('height', image.height)

        # Calculate center position
        center_x = width / 2
        center_y = height / 2

        # Apply shift if specified - match JavaScript calculation exactly
        if 'shift' in picture:
            center_x = round(abs((picture['shift'][0] - width / 64) * 32))
            center_y = round(abs((picture['shift'][1] - height / 64) * 32))

        # Calculate canvas size
        canvas_width = width + abs(width / 2 - center_x)
        canvas_height = height + abs(height / 2 - center_y)

        # Create result canvas
        result = Image.new('RGBA', (int(canvas_width), int(canvas_height)), (0, 0, 0, 0))

        # Calculate position to draw at
        delta_x = round(canvas_width / 2) - center_x
        delta_y = round(canvas_height / 2) - center_y

        # Extract the specified region from source image
        src_x = x_offset or picture.get('x', 0)
        src_y = y_offset or picture.get('y', 0)

        if src_x + width <= image.width and src_y + height <= image.height:
            cropped = image.crop((src_x, src_y, src_x + width, src_y + height))
            result.paste(cropped, (int(delta_x), int(delta_y)), cropped)

        return result

    def extract_from_picture(self, name: str, picture: Any, suffix: str = ""):
        """Extract sprites from picture definition"""
        if picture is None:
            print(f"Skipping (no data): {name} {suffix}")
            return

        if isinstance(picture, dict):
            if 'filename' in picture:
                # Single sprite
                result_name = name + suffix
                if picture.get('draw_as_shadow'):
                    result_name += "_shadow"

                canvas = self.process_picture(picture)
                if canvas:
                    self.save_canvas(f"{result_name}.png", canvas)

            elif 'north' in picture:
                # Directional sprites
                for direction in self.directions:
                    if direction in picture:
                        self.extract_from_picture(name, picture[direction],
                                                  suffix + "_" + direction)

            elif 'layers' in picture:
                # Layered sprites
                layers = picture['layers']
                if len(layers) == 2 and len(layers) > 1 and layers[1].get('draw_as_shadow'):
                    # Main + shadow
                    self.extract_from_picture(name, layers[0], suffix)
                    self.extract_from_picture(name, layers[1], suffix)
                else:
                    # Multiple layers
                    for i, layer in enumerate(layers):
                        self.extract_from_picture(name, layer, suffix + f"_{i}")

            else:
                # Other structure - check for sheet
                for key, value in picture.items():
                    if key == "sheet":
                        self.extract_from_picture(name, value, suffix)
                    else:
                        self.extract_from_picture(name, value, suffix + f"_{key}")

    # Entity-specific extraction methods
    def transport_belt(self, entity: str, data: Dict):
        """Extract transport belt sprites"""
        animations = data.get('animations')
        if not animations:
            animations = data.get('belt_animation_set', {}).get('animation_set', [])

        # Horizontal
        img = self.process_picture(animations)
        if img:
            self.save_canvas(f"{entity}_horizontal.png", img)

        # Vertical
        img = self.process_picture(animations, 0, animations.get('height', 0))
        if img:
            self.save_canvas(f"{entity}_vertical.png", img)

        # Bend right
        img = self.process_picture(animations, 0, 8 * animations.get('height', 0))
        if img:
            self.save_canvas(f"{entity}_bend_right.png", img)

        # Bend left
        img = self.process_picture(animations, 0, 9 * animations.get('height', 0))
        if img:
            self.save_canvas(f"{entity}_bend_left.png", img)

    def underground_belt(self, entity: str, data: Dict):
        """Extract underground belt sprites"""
        structure = data.get('structure', {})

        # Get belt animations from the correct location
        belt_animation = data.get('belt_animation_set', {}).get('animation_set')
        if not belt_animation:
            print(f"Warning: No belt animation found for {entity}")
            return

        # For underground belts, we need to extract horizontal and vertical sections
        # from the main animation sheet
        if not structure:
            print(f"Warning: No structure found for {entity}")
            return

        out_sprites = structure.get('direction_out', {})
        in_sprites = structure.get('direction_in', {})

        # The belt animation contains all directions in one sheet
        # We need to process it similarly to transport_belt to get horizontal and vertical

        # First, let's get the belt animations for different orientations
        belt_h = self.process_picture(belt_animation)  # Horizontal belt
        belt_v = self.process_picture(belt_animation, 0, belt_animation.get('height', 0))  # Vertical belt

        if not belt_h or not belt_v:
            print(f"Warning: Could not process belt animations for {entity}")
            return

        # Output sprites
        if out_sprites.get('sheet'):
            sheet = out_sprites['sheet']

            # Down
            belt = self.process_picture(belt_animation, 0, belt_animation.get('height', 0) + 40, 40, 20)
            if belt:
                belt = self.rotate_canvas(belt, 180)
                belt = self.extend_canvas(belt, 20, 0, 0, 1)
                out_img = self.process_picture(sheet)
                if out_img:
                    combined = self.combine_canvas(belt, out_img)
                    self.save_canvas(f"{entity}_out_down.png", combined)

            # Left
            out_img = self.process_picture(sheet, sheet.get('width', 0), 0)
            if belt_h and out_img:
                combined = self.combine_canvas(belt_h, out_img)
                self.save_canvas(f"{entity}_out_left.png", combined)

            # Up
            belt = self.extend_canvas(belt_v, 0, 0, 0, 1)
            out_img = self.process_picture(sheet, 2 * sheet.get('width', 0), 0)
            if belt and out_img:
                combined = self.combine_canvas(belt, out_img)
                self.save_canvas(f"{entity}_out_up.png", combined)

            # Right
            belt = self.process_picture(belt_animation, 20, 0, 20, 40)
            if belt:
                belt = self.extend_canvas(belt, 0, 0, 0, 21)
                out_img = self.process_picture(sheet, 3 * sheet.get('width', 0), 0)
                if out_img:
                    combined = self.combine_canvas(belt, out_img)
                    self.save_canvas(f"{entity}_out_right.png", combined)

        # Input sprites
        if in_sprites.get('sheet'):
            sheet = in_sprites['sheet']
            sheet_h = sheet.get('height', 0)

            # Up
            belt = self.process_picture(belt_animation, 0, belt_animation.get('height', 0) + 60, 40, 20)
            if belt:
                belt = self.extend_canvas(belt, 20, 0, 0, 1)
                in_img = self.process_picture(sheet, 0, sheet_h)
                if in_img:
                    combined = self.combine_canvas(belt, in_img)
                    self.save_canvas(f"{entity}_in_up.png", combined)

            # Right
            belt = self.process_picture(belt_animation, 0, 0, 19, 40)
            if belt:
                belt = self.extend_canvas(belt, 0, 20, 0, 0)
                in_img = self.process_picture(sheet, sheet.get('width', 0), sheet_h)
                if in_img:
                    combined = self.combine_canvas(belt, in_img)
                    self.save_canvas(f"{entity}_in_right.png", combined)

            # Down
            belt = self.process_picture(belt_animation, 0, belt_animation.get('height', 0))
            if belt:
                belt = self.rotate_canvas(belt, 180)
                belt = self.extend_canvas(belt, 0, 0, 0, 1)
                in_img = self.process_picture(sheet, 2 * sheet.get('width', 0), sheet_h)
                if in_img:
                    combined = self.combine_canvas(belt, in_img)
                    self.save_canvas(f"{entity}_in_down.png", combined)

            # Left
            belt = self.process_picture(belt_animation, 0, 0, 20, 40)
            if belt:
                belt = self.rotate_canvas(belt, 180)
                belt = self.extend_canvas(belt, 0, 0, 0, 20)
                in_img = self.process_picture(sheet, 3 * sheet.get('width', 0), sheet_h)
                if in_img:
                    combined = self.combine_canvas(belt, in_img)
                    self.save_canvas(f"{entity}_in_left.png", combined)

    def lab(self, entity: str, data: Dict) -> None:
        """
        Render the Factorio lab.

        Saves:
            <entity>_off.png           – single static sprite
            <entity>_on_XX.png         – 33‑frame animation, zero‑based

        Needs:
            - data["off_animation"]["layers"]
            - data["on_animation"]["layers"]
        """

        # ------------------------------------------------------------------
        # 1.  Little helpers
        # ------------------------------------------------------------------
        def slice_frame(layer: Dict, frame: int) -> Image.Image | None:
            """
            Return PIL.Image for *layer* at *frame* (handles HR fallback).
            """
            sheet = self.process_picture(layer)
            if sheet is None:
                return None

            w, h = layer["width"], layer["height"]
            fc = layer.get("frame_count", 1)
            ll = layer.get("line_length", fc)

            # When frame_count == 1 but repeat_count > 1 (integration/shadow)
            # we still slice 0 – factorio repeats that single tile.
            local_f = 0 if fc == 1 else frame % fc
            col = local_f % ll
            row = local_f // ll
            x0, y0 = col * w, row * h
            return sheet.crop((x0, y0, x0 + w, y0 + h))

        def shift_img(img: Image.Image, shift_xy: list[float]) -> Image.Image:
            """
            Add transparent borders so *img* is offset by `shift`.
            Positive shift.x  →  right, positive shift.y → down (Factorio style).
            """
            dx = int(round(shift_xy[0] * TILE_PX))
            dy = int(round(shift_xy[1] * TILE_PX))

            left, right = (dx, 0) if dx > 0 else (0, -dx)
            top, bottom = (dy, 0) if dy > 0 else (0, -dy)
            return self.extend_canvas(img, left, top, right, bottom)

        def composite(base: Image.Image | None, top: Image.Image, mode: str) -> Image.Image:
            """
            Composite *top* onto *base* using *mode*.
            """
            if base is None:
                return top

            if mode == "additive":
                # Pillow's add clips at 255 → faithful enough
                return ImageChops.add(base, top)
            else:
                return self.combine_canvas(base, top)

        # ------------------------------------------------------------------
        # 2.  Convenience to render one complete frame
        # ------------------------------------------------------------------
        def render_frame(layers: list[Dict], frame_idx: int) -> Image.Image | None:
            base = None
            shadows: list[Image.Image] = []

            # 2a. paint normal + additive layers immediately
            for lyr in layers:
                img = slice_frame(lyr, frame_idx)
                if img is None:
                    continue

                img = shift_img(img, lyr.get("shift", [0, 0]))

                if lyr.get("draw_as_shadow"):
                    shadows.append(img)  # postpone until after everything else
                    continue

                blend = "additive" if lyr.get("blend_mode") == "additive" or lyr.get("draw_as_light") else "normal"
                base = composite(base, img, blend)

            # 2b. shadows go on top, normal blend
            for sh in shadows:
                base = composite(base, sh, "normal")

            return base

        # ------------------------------------------------------------------
        # 3.  OFF sprite (single frame)
        # ------------------------------------------------------------------
        off_layers = data.get("off_animation", {}).get("layers", [])
        if off_layers:
            off = render_frame(off_layers, 0)
            if off:
                self.save_canvas(f"{entity}_off.png", off)

        # ------------------------------------------------------------------
        # 4.  ON animation (33 frames)
        # ------------------------------------------------------------------
        on_layers = data.get("on_animation", {}).get("layers", [])
        if on_layers:
            frame_count = on_layers[0].get("frame_count", 1)
            for f in range(frame_count):
                frame_img = render_frame(on_layers, f)
                if frame_img:
                    self.save_canvas(f"{entity}_on_{f:02d}.png", frame_img)

    def splitter(self, entity: str, data: Dict):
        """
        Render the four static splitter sprites (N/E/S/W) from the new
        1.1‑style prototype definition.

        Required keys inside *data*:
            - structure:        {north|east|south|west: {...}}
            - belt_animation_set.animation_set: {...}
        Optional:
            - structure_patch:  {east|west: {...}}  # only E/W use patches
        """
        # ------------------------------------------------------------------
        # 1.  Collect the three sprite sources we need
        # ------------------------------------------------------------------
        structure = data.get("structure", {})
        if not structure:
            return

        anim_set = (
            data.get("belt_animation_set", {})
            .get("animation_set")
        )
        if not anim_set:
            return

        patch = data.get("structure_patch", {})  # may be empty

        # ------------------------------------------------------------------
        # 2.  Helpers for slicing the belt sprite sheet and applying patches
        # ------------------------------------------------------------------
        def belt_frame(direction: int, frame: int = 0):
            """
            Crop a *single* belt tile from the big 64×64 (HR:128×128) sheet.
            *direction* is the sprite‑row (0 = north, 2 = east, 4 = south, 6 = west)
            *frame*     is the animation frame column (we render frame 0 for static)
            """
            sheet = self.process_picture(anim_set)
            if not sheet:
                return None

            w, h = anim_set["width"], anim_set["height"]
            line_len = anim_set.get("line_length", anim_set["frame_count"])

            col = frame % line_len
            row = direction
            x0, y0 = col * w, row * h
            return sheet.crop((x0, y0, x0 + w, y0 + h))

        def add_patch(canvas, direction: str):
            """
            Overlay the (optional) top patch used by east/west splitters.
            """
            p = patch.get(direction)
            # Ignore the canonical 1×1 empty sprite
            if p and not p["filename"].endswith("empty.png"):
                patch_img = self.process_picture(p)
                if patch_img:
                    canvas = self.combine_canvas(canvas, patch_img)
            return canvas

        # Pre‑slice static belt tiles once; reuse them for both belts
        belt_v = belt_frame(0)  # vertical (north‑facing)
        belt_h = belt_frame(2)  # horizontal (east‑facing)
        if not belt_v or not belt_h:
            return

        # ------------------------------------------------------------------
        # 3.  NORTH
        # ------------------------------------------------------------------
        if "north" in structure:
            belt1 = self.extend_canvas(belt_v.copy(), 0, 30)  # belt entering
            belt2 = self.extend_canvas(belt_v.copy(), 0, 0, 0, 30)  # belt leaving
            belts = self.combine_canvas(belt1, belt2)

            struct = self.process_picture(structure["north"])
            if struct:
                combined = self.combine_canvas(belts, struct)
                self.save_canvas(f"{entity}_north.png", combined)

        # ------------------------------------------------------------------
        # 4.  EAST
        # ------------------------------------------------------------------
        if "east" in structure:
            belt1 = self.extend_canvas(belt_h.copy(), 34)  # belt entering
            belt2 = self.extend_canvas(belt_h.copy(), 0, 0, 34)  # belt leaving
            belts = self.combine_canvas(belt1, belt2)

            struct = self.process_picture(structure["east"])
            if struct:
                combined = self.combine_canvas(belts, struct)
                combined = add_patch(combined, "east")
                self.save_canvas(f"{entity}_east.png", combined)

        # ------------------------------------------------------------------
        # 5.  SOUTH (rotate belts 180°)
        # ------------------------------------------------------------------
        if "south" in structure:
            belt1 = self.rotate_canvas(belt_v.copy(), 180)
            belt2 = self.rotate_canvas(belt_v.copy(), 180)
            belt1 = self.extend_canvas(belt1, 0, 32)
            belt2 = self.extend_canvas(belt2, 0, 0, 0, 32)
            belts = self.combine_canvas(belt1, belt2)

            struct = self.process_picture(structure["south"])
            if struct:
                combined = self.combine_canvas(belts, struct)
                self.save_canvas(f"{entity}_south.png", combined)

        # ------------------------------------------------------------------
        # 6.  WEST (rotate belts 180° + optional patch)
        # ------------------------------------------------------------------
        if "west" in structure:
            belt1 = self.rotate_canvas(belt_h.copy(), 180)
            belt2 = self.rotate_canvas(belt_h.copy(), 180)
            belt1 = self.extend_canvas(belt1, 34)
            belt2 = self.extend_canvas(belt2, 0, 0, 34)
            belts = self.combine_canvas(belt1, belt2)

            struct = self.process_picture(structure["west"])
            if struct:
                combined = self.combine_canvas(belts, struct)
                combined = add_patch(combined, "west")
                self.save_canvas(f"{entity}_west.png", combined)

    def pipe_to_ground(self, entity: str, data: Dict):
        """Extract pipe-to-ground sprites - similar to underground belt"""
        # Just use standard extraction for pipe-to-ground
        if 'pictures' in data:
            self.extract_from_picture(entity, data['pictures'])
        elif 'picture' in data:
            self.extract_from_picture(entity, data['picture'])

    def inserter(self, entity: str, data: Dict):
        """Extract inserter sprites"""
        platform = data.get('platform_picture', {}).get('sheet')
        hand_open = data.get('hand_open_picture')
        hand_base = data.get('hand_base_picture')

        if not all([platform, hand_open, hand_base]):
            return

        # North
        plat = self.process_picture(platform)
        hand = self.process_picture(hand_open)
        if plat and hand:
            hand = self.extend_canvas(hand, 0, 0, 40, 2)
            combined = self.combine_canvas(plat, hand)
            self.save_canvas(f"{entity}_north.png", combined)

        # East
        plat = self.process_picture(platform, 3 * platform['width'], 0)
        if plat and hand_base and hand_open:
            base = self.process_picture(hand_base)
            hand = self.process_picture(hand_open)
            if base and hand:
                base = self.extend_canvas(base, 15, 15, 15, 15)
                base = self.rotate_canvas(base, 35)
                base = self.extend_canvas(base, 0, 0, 20, 10)

                hand = self.extend_canvas(hand, 15, 15, 15, 15)
                hand = self.rotate_canvas(hand, 145)
                hand = self.extend_canvas(hand, 0, 0, 15, 45)

                hands = self.combine_canvas(base, hand)
                combined = self.combine_canvas(plat, hands)
                self.save_canvas(f"{entity}_east.png", combined)

        # South
        plat = self.process_picture(platform, 2 * platform['width'], 0)
        hand = self.process_picture(hand_open)
        if plat and hand:
            hand = self.rotate_canvas(hand, 180)
            hand = self.extend_canvas(hand, 32, 0, 0, 2)
            combined = self.combine_canvas(plat, hand)
            self.save_canvas(f"{entity}_south.png", combined)

        # West
        plat = self.process_picture(platform, 1 * platform['width'], 0)
        if plat and hand_base and hand_open:
            base = self.process_picture(hand_base)
            hand = self.process_picture(hand_open)
            if base and hand:
                base = self.extend_canvas(base, 15, 15, 15, 15)
                base = self.rotate_canvas(base, -35)
                base = self.extend_canvas(base, 0, 15, 20, 0)

                hand = self.extend_canvas(hand, 15, 15, 15, 15)
                hand = self.rotate_canvas(hand, -145)
                hand = self.extend_canvas(hand, 0, 50, 15, 0)

                hands = self.combine_canvas(base, hand)
                combined = self.combine_canvas(plat, hands)
                self.save_canvas(f"{entity}_west.png", combined)

    def long_handed_inserter(self, entity: str, data: Dict):
        """Extract long-handed inserter sprites"""
        platform = data.get('platform_picture', {}).get('sheet')
        hand_open = data.get('hand_open_picture')
        hand_base = data.get('hand_base_picture')

        if not all([platform, hand_open, hand_base]):
            return

        # North
        plat = self.process_picture(platform)
        hand = self.process_picture(hand_open)
        base = self.process_picture(hand_base)
        if plat and hand and base:
            hand = self.extend_canvas(hand, 0, 0, 90, 2)
            base = self.extend_canvas(base, 0, 0, 30, 3)
            hands = self.combine_canvas(hand, base)
            combined = self.combine_canvas(plat, hands)
            self.save_canvas(f"{entity}_north.png", combined)

        # East
        plat = self.process_picture(platform, 3 * platform['width'], 0)
        if plat and hand_base and hand_open:
            base = self.process_picture(hand_base)
            hand = self.process_picture(hand_open)
            if base and hand:
                base = self.extend_canvas(base, 15, 15, 15, 15)
                base = self.rotate_canvas(base, 75)
                base = self.extend_canvas(base, 0, 0, 20, 20)

                hand = self.extend_canvas(hand, 15, 15, 15, 15)
                hand = self.rotate_canvas(hand, 115)
                hand = self.extend_canvas(hand, 0, 0, 15, 85)

                hands = self.combine_canvas(base, hand)
                combined = self.combine_canvas(plat, hands)
                self.save_canvas(f"{entity}_east.png", combined)

        # South
        plat = self.process_picture(platform, 2 * platform['width'], 0)
        hand = self.process_picture(hand_open)
        base = self.process_picture(hand_base)
        if plat and hand and base:
            hand = self.rotate_canvas(hand, 180)
            hand = self.extend_canvas(hand, 85, 0, 0, 2)
            base = self.rotate_canvas(base, 180)
            base = self.extend_canvas(base, 25, 0, 0, 3)
            hands = self.combine_canvas(hand, base)
            combined = self.combine_canvas(plat, hands)
            self.save_canvas(f"{entity}_south.png", combined)

        # West
        plat = self.process_picture(platform, 1 * platform['width'], 0)
        if plat and hand_base and hand_open:
            base = self.process_picture(hand_base)
            hand = self.process_picture(hand_open)
            if base and hand:
                base = self.extend_canvas(base, 15, 15, 15, 15)
                base = self.rotate_canvas(base, -75)
                base = self.extend_canvas(base, 0, 15, 20, 0)

                hand = self.extend_canvas(hand, 15, 15, 15, 15)
                hand = self.rotate_canvas(hand, -115)
                hand = self.extend_canvas(hand, 0, 85, 15, 0)

                hands = self.combine_canvas(base, hand)
                combined = self.combine_canvas(plat, hands)
                self.save_canvas(f"{entity}_west.png", combined)

    def combinator_displays(self):
        """Extract combinator display symbols"""
        grid = [
            ["empty", "plus", "minus", "multiply", "divide", "modulo"],
            ["power", "left_shift", "right_shift", "and", "or", "xor"],
            ["gt", "lt", "eq", "neq", "lte", "gte"]
        ]

        width = 15
        height = 11

        try:
            image = self.get_file("__base__/graphics/entity/combinator/combinator-displays.png")
        except FileNotFoundError:
            print("Warning: Could not find combinator displays")
            return

        for y in range(len(grid)):
            for x in range(len(grid[y])):
                cropped = self.crop_image(image, x * width, y * height, width, height)
                self.save_canvas(f"display_{grid[y][x]}.png", cropped)

    def roboport(self, entity: str, data: Dict):
        """Extract roboport sprites"""
        base = self.process_picture(data.get('base'))
        base_patch = self.process_picture(data.get('base_patch'))
        door_up = self.process_picture(data.get('door_animation_up'))
        door_down = self.process_picture(data.get('door_animation_down'))
        base_anim = self.process_picture(data.get('base_animation'))

        result = base
        if base_patch:
            result = self.combine_canvas(result, base_patch) if result else base_patch
        if door_up:
            result = self.combine_canvas(result, door_up) if result else door_up
        if door_down:
            result = self.combine_canvas(result, door_down) if result else door_down
        if base_anim:
            result = self.combine_canvas(result, base_anim) if result else base_anim

        if result:
            self.save_canvas(f"{entity}.png", result)

    def heat_pipe(self, entity: str, data: Dict):
        """Extract heat pipe sprites"""
        sprites = data.get('connection_sprites', {})

        sprite_names = [
            'single', 'straight_horizontal', 'ending_right', 'corner_right_up',
            't_left', 't_down', 'ending_up', 't_right', 't_up', 'ending_left',
            'ending_down', 'straight_vertical', 'corner_right_down', 'cross',
            'corner_left_down', 'corner_left_up'
        ]

        for sprite_name in sprite_names:
            if sprite_name in sprites and sprites[sprite_name]:
                img = self.process_picture(sprites[sprite_name][0])
                if img:
                    self.save_canvas(f"{entity}_{sprite_name}.png", img)

    def stone_wall(self, entity: str, data: Dict):
        """Extract stone wall sprites"""
        pics = data.get('pictures', {})

        # Regular sprites
        if 'single' in pics and 'layers' in pics['single']:
            img = self.process_picture(pics['single']['layers'][0])
            if img:
                self.save_canvas(f"{entity}_single.png", img)
            img = self.process_picture(pics['single']['layers'][1])
            if img:
                self.save_canvas(f"{entity}_single_shadow.png", img)

        # Other wall types
        wall_types = [
            ('straight_horizontal', 0),
            ('ending_right', None),
            ('t_up', None),
            ('ending_left', None),
            ('straight_vertical', 0),
            ('corner_right_down', None),
            ('corner_left_down', None)
        ]

        for wall_type, index in wall_types:
            if wall_type in pics:
                pic_data = pics[wall_type]
                if index is not None and isinstance(pic_data, list):
                    pic_data = pic_data[index]

                if 'layers' in pic_data:
                    img = self.process_picture(pic_data['layers'][0])
                    if img:
                        self.save_canvas(f"{entity}_{wall_type}.png", img)
                    img = self.process_picture(pic_data['layers'][1])
                    if img:
                        self.save_canvas(f"{entity}_{wall_type}_shadow.png", img)

    def assembling_machine(self, entity: str, data: Dict):
        """Extract assembling machine sprites"""
        if 'animation' in data and 'layers' in data['animation']:
            img = self.process_picture(data['animation']['layers'][0])
            if img:
                self.save_canvas(f"{entity}.png", img)
            if len(data['animation']['layers']) > 1:
                img = self.process_picture(data['animation']['layers'][1])
                if img:
                    self.save_canvas(f"{entity}_shadow.png", img)

        # Pipe connections - try to load directly
        for direction in ['N', 'E', 'S', 'W']:
            try:
                img = self.get_file(f"__base__/graphics/entity/{entity}/{entity}-pipe-{direction}.png")
                if direction == 'N':
                    img = self.extend_canvas(img, 0, 0, 100, 5)
                elif direction == 'E':
                    img = self.extend_canvas(img, 0, 0, 0, 80)
                elif direction == 'S':
                    img = self.extend_canvas(img, 70, 0, 0, 0)
                elif direction == 'W':
                    img = self.extend_canvas(img, 0, 77, 0, 0)
                self.save_canvas(f"{entity}_pipe_{direction.lower()}orth.png" if direction == 'N' else
                                 f"{entity}_pipe_{direction.lower()}ast.png" if direction == 'E' else
                                 f"{entity}_pipe_{direction.lower()}outh.png" if direction == 'S' else
                                 f"{entity}_pipe_{direction.lower()}est.png", img)
            except:
                pass

    def rocket_silo(self, entity: str, data: Dict):
        """Extract rocket silo sprites"""
        door_back = self.process_picture(data.get('door_back_sprite'))
        base_day = self.process_picture(data.get('base_day_sprite'))

        # Door front needs special handling
        door_front = None
        if 'door_front_sprite' in data and 'filename' in data['door_front_sprite']:
            try:
                door_front = self.get_file(data['door_front_sprite']['filename'])
                door_front = self.extend_canvas(door_front, 130, 0, 0, 0)
            except:
                pass

        result = base_day
        if door_back:
            result = self.combine_canvas(door_back, result) if result else door_back
        if door_front:
            result = self.combine_canvas(result, door_front) if result else door_front

        if result:
            self.save_canvas(f"{entity}.png", result)

        shadow = self.process_picture(data.get('shadow_sprite'))
        if shadow:
            self.save_canvas(f"{entity}_shadow.png", shadow)

    def nuclear_reactor(self, entity: str, data: Dict):
        """Extract nuclear reactor sprites"""
        lower = self.process_picture(data.get('lower_layer_picture'))
        upper = None

        if 'picture' in data and 'layers' in data['picture']:
            upper = self.process_picture(data['picture']['layers'][0])

        if lower and upper:
            result = self.combine_canvas(lower, upper)
            self.save_canvas(f"{entity}.png", result)
        elif lower:
            self.save_canvas(f"{entity}.png", lower)
        elif upper:
            self.save_canvas(f"{entity}.png", upper)

        if 'picture' in data and 'layers' in data['picture'] and len(data['picture']['layers']) > 1:
            shadow = self.process_picture(data['picture']['layers'][1])
            if shadow:
                self.save_canvas(f"{entity}_shadow.png", shadow)

    def storage_tank(self, entity: str, data: Dict):
        """Extract storage tank sprites"""
        if 'pictures' in data and 'picture' in data['pictures'] and 'sheet' in data['pictures']['picture']:
            sheet = data['pictures']['picture']['sheet']
            img = self.process_picture(sheet)
            if img:
                self.save_canvas(f"{entity}_north.png", img)
            img = self.process_picture(sheet, sheet.get('width', 0), 0)
            if img:
                self.save_canvas(f"{entity}_east.png", img)

    def beacon(self, entity: str, data: Dict):
        """Extract beacon sprites"""
        base = self.process_picture(data.get('base_picture'))
        animation = self.process_picture(data.get('animation'))

        if base and animation:
            result = self.combine_canvas(base, animation)
            self.save_canvas(f"{entity}.png", result)
        elif base:
            self.save_canvas(f"{entity}.png", base)
        elif animation:
            self.save_canvas(f"{entity}.png", animation)

    def centrifuge(self, entity: str, data: Dict):
        """Extract centrifuge sprites"""
        if 'idle_animation' in data and 'layers' in data['idle_animation']:
            layers = data['idle_animation']['layers']

            # Main sprite
            if len(layers) >= 5:
                layer0 = self.process_picture(layers[0])
                layer2 = self.process_picture(layers[2])
                layer4 = self.process_picture(layers[4])

                result = layer0
                if layer2:
                    result = self.combine_canvas(result, layer2) if result else layer2
                if layer4:
                    result = self.combine_canvas(result, layer4) if result else layer4

                if result:
                    self.save_canvas(f"{entity}.png", result)

            # Shadow sprite
            if len(layers) >= 6:
                layer1 = self.process_picture(layers[1])
                layer3 = self.process_picture(layers[3])
                layer5 = self.process_picture(layers[5])

                result = layer1
                if layer3:
                    result = self.combine_canvas(result, layer3) if result else layer3
                if layer5:
                    result = self.combine_canvas(result, layer5) if result else layer5

                if result:
                    self.save_canvas(f"{entity}_shadow.png", result)

    def flamethrower_turret(self, entity: str, data: Dict):
        """Extract flamethrower turret sprites"""
        pipe_pics = data.get('fluid_box', {}).get('pipe_picture', {})
        base_pics = data.get('base_picture', {})
        folded_anim = data.get('folded_animation', {})

        # Process each direction
        for direction in self.directions:
            if direction in base_pics and direction in folded_anim:
                base_layers = base_pics[direction].get('layers', [])
                folded_layers = folded_anim[direction].get('layers', [])

                if base_layers and folded_layers:
                    # Main sprite
                    base = self.process_picture(base_layers[0])
                    folded = self.process_picture(folded_layers[0])

                    # Add pipes based on direction
                    if direction == 'north':
                        pipe_e = self.process_picture(pipe_pics.get('east'))
                        pipe_w = self.process_picture(pipe_pics.get('west'))
                        if pipe_e:
                            pipe_e = self.extend_canvas(pipe_e, 64, 0, 0, 32)
                        if pipe_w:
                            pipe_w = self.extend_canvas(pipe_w, 64, 32, 0, 0)
                    elif direction == 'east':
                        pipe_n = self.process_picture(pipe_pics.get('north'))
                        pipe_s = self.process_picture(pipe_pics.get('south'))
                        if pipe_n:
                            pipe_n = self.extend_canvas(pipe_n, 0, 64, 32, 0)
                        if pipe_s:
                            pipe_s = self.extend_canvas(pipe_s, 32, 64, 0, 0)
                    elif direction == 'south':
                        pipe_e = self.process_picture(pipe_pics.get('east'))
                        pipe_w = self.process_picture(pipe_pics.get('west'))
                        if pipe_e:
                            pipe_e = self.extend_canvas(pipe_e, 0, 0, 64, 32)
                        if pipe_w:
                            pipe_w = self.extend_canvas(pipe_w, 0, 32, 64, 0)
                    elif direction == 'west':
                        pipe_n = self.process_picture(pipe_pics.get('north'))
                        pipe_s = self.process_picture(pipe_pics.get('south'))
                        if pipe_n:
                            pipe_n = self.extend_canvas(pipe_n, 0, 0, 32, 64)
                        if pipe_s:
                            pipe_s = self.extend_canvas(pipe_s, 32, 0, 0, 64)

                    # Combine all elements
                    result = base
                    if folded:
                        result = self.combine_canvas(result, folded) if result else folded

                    if direction in ['north', 'south']:
                        if 'pipe_e' in locals() and pipe_e:
                            result = self.combine_canvas(pipe_e, result) if result else pipe_e
                        if 'pipe_w' in locals() and pipe_w:
                            result = self.combine_canvas(pipe_w, result) if result else pipe_w
                    else:
                        if 'pipe_n' in locals() and pipe_n:
                            result = self.combine_canvas(pipe_n, result) if result else pipe_n
                        if 'pipe_s' in locals() and pipe_s:
                            result = self.combine_canvas(pipe_s, result) if result else pipe_s

                    if result:
                        self.save_canvas(f"{entity}_{direction}.png", result)

                    # Shadow
                    if len(base_layers) > 2 and len(folded_layers) > 2:
                        base_shadow = self.process_picture(base_layers[2])
                        folded_shadow = self.process_picture(folded_layers[2])

                        shadow = base_shadow
                        if folded_shadow:
                            shadow = self.combine_canvas(shadow, folded_shadow) if shadow else folded_shadow

                        if shadow:
                            self.save_canvas(f"{entity}_{direction}_shadow.png", shadow)

    def normal_turret(self, entity: str, data: Dict):
        """Extract normal turret sprites"""
        base = None
        folded = None
        shadow = None

        if 'base_picture' in data and 'layers' in data['base_picture']:
            base = self.process_picture(data['base_picture']['layers'][0])

        if 'folded_animation' in data and 'layers' in data['folded_animation']:
            folded = self.process_picture(data['folded_animation']['layers'][0])
            # Try to find shadow in different positions
            if len(data['folded_animation']['layers']) > 1:
                shadow = self.process_picture(data['folded_animation']['layers'][1])
            if not shadow and len(data['folded_animation']['layers']) > 2:
                shadow = self.process_picture(data['folded_animation']['layers'][2])

        result = base
        if folded:
            result = self.combine_canvas(result, folded) if result else folded

        if result:
            self.save_canvas(f"{entity}.png", result)

        if shadow:
            self.save_canvas(f"{entity}_shadow.png", shadow)

    def pumpjack(self, entity: str, data: Dict):
        """Extract pumpjack sprites"""
        base_sheet = data.get('base_picture', {}).get('sheet')
        animations = data.get('animations', {}).get('north')

        if base_sheet and animations:
            for i, direction in enumerate(self.directions):
                base = self.process_picture(base_sheet, i * base_sheet.get('width', 0), 0)
                anim = self.process_picture(animations)

                if base and anim:
                    result = self.combine_canvas(base, anim)
                    self.save_canvas(f"{entity}_{direction}.png", result)

    def straight_rail(self, entity: str, data: Dict):
        """Extract straight rail sprites"""
        pics = data.get('pictures', {})

        # Horizontal rails
        h_rail = pics.get('straight_rail_horizontal', {})
        for i, component in enumerate(['stone_path_background', 'stone_path', 'ties', 'backplates', 'metals']):
            if component in h_rail and 'sheet' in h_rail[component]:
                img = self.process_picture(h_rail[component]['sheet'])
                if img:
                    self.save_canvas(f"{entity}_horizontal_pass_{i + 1}.png", img)

        # Vertical rails
        v_rail = pics.get('straight_rail_vertical', {})
        for i, component in enumerate(['stone_path_background', 'stone_path', 'ties', 'backplates', 'metals']):
            if component in v_rail and 'sheet' in v_rail[component]:
                img = self.process_picture(v_rail[component]['sheet'])
                if img:
                    self.save_canvas(f"{entity}_vertical_pass_{i + 1}.png", img)

        # Diagonal rails
        for diagonal in ['diagonal_left_bottom', 'diagonal_right_bottom', 'diagonal_left_top', 'diagonal_right_top']:
            d_rail = pics.get(f'straight_rail_{diagonal}', {})
            for i, component in enumerate(['stone_path_background', 'stone_path', 'ties', 'backplates', 'metals']):
                if component in d_rail and 'sheet' in d_rail[component]:
                    img = self.process_picture(d_rail[component]['sheet'])
                    if img:
                        self.save_canvas(f"{entity}_{diagonal}_pass_{i + 1}.png", img)

    def curved_rail(self, entity: str, data: Dict):
        """Extract curved rail sprites"""
        pics = data.get('pictures', {})

        # All curved rail variants
        variants = [
            'vertical_left_top', 'vertical_left_bottom', 'vertical_right_top', 'vertical_right_bottom',
            'horizontal_left_top', 'horizontal_left_bottom', 'horizontal_right_top', 'horizontal_right_bottom'
        ]

        for variant in variants:
            rail = pics.get(f'curved_rail_{variant}', {})
            for i, component in enumerate(['stone_path_background', 'stone_path', 'ties', 'backplates', 'metals']):
                if component in rail and 'sheet' in rail[component]:
                    img = self.process_picture(rail[component]['sheet'])
                    if img:
                        self.save_canvas(f"{entity}_{variant}_pass_{i + 1}.png", img)

    def rail_signal(self, entity: str, data: Dict):
        """Extract rail signal sprites"""
        animation = data.get('animation')
        rail_piece = data.get('rail_piece')

        if animation:
            for i in range(8):
                img = self.process_picture(animation, 0, i * animation.get('height', 0))
                if img:
                    self.save_canvas(f"{entity}_{i}.png", img)

        if rail_piece:
            for i in range(8):
                img = self.process_picture(rail_piece, i * rail_piece.get('width', 0), 0)
                if img:
                    self.save_canvas(f"{entity}_rail_{i}.png", img)

    def rail_chain_signal(self, entity: str, data: Dict):
        """Extract rail chain signal sprites"""
        anim = data.get('animation')
        rail = data.get('rail_piece')

        # Different orientations with extensions
        extensions = [
            (0, 0, 0, 64),  # 0
            (64, 0, 0, 64),  # 1
            (64, 0, 0, 0),  # 2
            (64, 64, 0, 0),  # 3
            (0, 128, 0, 0),  # 4
            (0, 64, 64, 0),  # 5
            (0, 0, 128, 0),  # 6
            (0, 0, 64, 64)  # 7
        ]

        for i, (up, right, down, left) in enumerate(extensions):
            if anim:
                img = self.process_picture(anim, 0, i * anim.get('height', 0))
                if img:
                    img = self.extend_canvas(img, up, right, down, left)
                    self.save_canvas(f"{entity}_{i}.png", img)

            if rail:
                img = self.process_picture(rail, i * rail.get('width', 0), 0)
                if img:
                    img = self.extend_canvas(img, up, right, down, left)
                    self.save_canvas(f"{entity}_rail_{i}.png", img)

    def extract_entity(self, entity_name: str):
        """Extract sprites for a specific entity"""
        # Special handlers
        special_handlers = {
            "curved-rail": self.curved_rail,
            "straight-rail": self.straight_rail,
            "beacon": self.beacon,
            "centrifuge": self.centrifuge,
            "pumpjack": self.pumpjack,
            "rocket-silo": self.rocket_silo,
            "underground-belt": self.underground_belt,
            "fast-underground-belt": self.underground_belt,
            "express-underground-belt": self.underground_belt,
            "transport-belt": self.transport_belt,
            "fast-transport-belt": self.transport_belt,
            "express-transport-belt": self.transport_belt,
            "splitter": self.splitter,
            "fast-splitter": self.splitter,
            "express-splitter": self.splitter,
            "inserter": self.inserter,
            "stack-inserter": self.inserter,
            "filter-inserter": self.inserter,
            "burner-inserter": self.inserter,
            "fast-inserter": self.inserter,
            "stack-filter-inserter": self.inserter,
            "long-handed-inserter": self.long_handed_inserter,
            "roboport": self.roboport,
            "heat-pipe": self.heat_pipe,
            "stone-wall": self.stone_wall,
            "nuclear-reactor": self.nuclear_reactor,
            "assembling-machine-2": self.assembling_machine,
            "assembling-machine-3": self.assembling_machine,
            "storage-tank": self.storage_tank,
            "flamethrower-turret": self.flamethrower_turret,
            "laser-turret": self.normal_turret,
            "gun-turret": self.normal_turret,
            "rail-signal": self.rail_signal,
            "rail-chain-signal": self.rail_chain_signal,
            "pipe-to-ground": self.pipe_to_ground  # Added missing handler
        }

        # Find entity data
        entity_data = None
        # for key, category in self.data.items():
        #     if isinstance(category, dict) and entity_name in category:
        #         entity_data = category[entity_name]
        #         break
        entity_data = self.data[entity_name]

        if not entity_data:
            print(f"Entity not found: {entity_name}")
            return

        # Use special handler if available
        if entity_name in special_handlers:
            special_handlers[entity_name](entity_name, entity_data)
            return

        # Generic extraction
        sprite_properties = [
            'picture', 'pictures', 'idle_animation', 'animation',
            'animations', 'structure', 'off_animation',
            'vertical_animation', 'horizontal_animation',
            'picture_off', 'power_on_animation', 'sprite',
            'sprites', 'connection_sprites'
        ]

        extracted = False
        for prop in sprite_properties:
            if prop in entity_data:
                if prop == 'vertical_animation' and 'horizontal_animation' in entity_data:
                    self.extract_from_picture(entity_name, entity_data['vertical_animation'], "_vertical")
                    self.extract_from_picture(entity_name, entity_data['horizontal_animation'], "_horizontal")
                else:
                    self.extract_from_picture(entity_name, entity_data[prop])
                extracted = True
                break

        if not extracted:
            print(f"TODO: {entity_name}")
        else:
            pass

    def extract_all(self):
        """Extract all entities"""
        # Complete skip categories list to match JavaScript
        skip_categories = [
            'technology', 'item-subgroup', 'tutorial', 'simple-entity',
            'unit', 'simple-entity-with-force', 'rail-remnants', 'item-group',
            'particle', 'car', 'font', 'character-corpse', 'cargo-wagon',
            'ammo-category', 'ambient-sound', 'smoke', 'tree', 'corpse'
        ]

        # for category_name, category_data in self.data.items():
        #     if category_name in skip_categories or category_name.endswith('achievement'):
        #         continue
        #
        #     if not isinstance(category_data, dict):
        #         continue

        for entity_name, entity_data in self.data.items():
            if not isinstance(entity_data, dict):
                continue

            # Skip hidden entities
            flags = entity_data.get('flags', [])
            if flags and 'hidden' in flags:
                continue

            # Extract icon
            if 'icon' in entity_data:
                try:
                    icon = self.get_file(entity_data['icon'])
                    self.save_canvas(f"icon_{entity_name}.png", icon)
                except Exception:
                    pass

            # Skip recipes and items for sprite extraction
            # if category_name in ['recipe', 'item']:
            #     continue

            # Check flags more strictly to match JavaScript
            if flags and ('player-creation' not in flags or 'placeable-off-grid' in flags):
                continue

            print(f"Processing {entity_name}...")
            try:
                self.extract_entity(entity_name)
            except Exception as e:
                print(f"Error processing {entity_name}: {e}")
                # Don't re-raise, continue processing

        # Extract combinator displays
        self.combinator_displays()


def main():
    """Main entry point"""
    import sys

    # if len(sys.argv) < 2:
    #     print("Usage: python spritesheet_extractor.py <data_path> [output_dir]")
    #     print("\nExample:")
    #     print("  python spritesheet_extractor.py data/rendering images")
    #     sys.exit(1)
    #
    # data_path = sys.argv[1]
    # output_dir = sys.argv[2] if len(sys.argv) > 2 else "images"
    data_path = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/rendering"
    output_dir = "/data/sprites/spritemaps"

    extractor = EntitySpritesheetExtractor(data_path, output_dir)
    extractor.extract_all()


if __name__ == "__main__":
    main()