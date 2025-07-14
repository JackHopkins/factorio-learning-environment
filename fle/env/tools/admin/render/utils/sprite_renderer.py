import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw
from fle.env.tools.admin.render.utils.basis_transcoder import BasisTranscoder

# # Add the data/rendering directory to the path so we can import the transcoder
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent.parent.parent
data_rendering_dir = project_root / "data" / "rendering"
sys.path.insert(0, str(data_rendering_dir))
#
# try:
#     from basis_transcoder import BasisTranscoder
# except ImportError as e:
#     print(f"Warning: Could not import BasisTranscoder: {e}")
#     BasisTranscoder = None

from fle.env.entities import Direction


class SpriteRenderer:
    """Renders entity sprites instead of geometric shapes"""
    
    def __init__(self, config):
        self.config = config
        self.sprite_cache: Dict[str, Image.Image] = {}
        
        # Initialize the basis transcoder if available
        if BasisTranscoder is not None:
            try:
                self.transcoder = BasisTranscoder(str(data_rendering_dir))
                print("Sprite renderer initialized with basis transcoder")
            except Exception as e:
                print(f"Warning: Could not initialize BasisTranscoder: {e}")
                self.transcoder = None
        else:
            self.transcoder = None
    
    def _get_sprite(self, entity_name: str) -> Optional[Image.Image]:
        """Get sprite for entity, using cache if available"""
        if entity_name in self.sprite_cache:
            return self.sprite_cache[entity_name]
        
        if self.transcoder is None:
            return None
        
        try:
            sprite = self.transcoder.get_entity_sprite(entity_name)
            if sprite:
                # Cache the sprite for future use
                self.sprite_cache[entity_name] = sprite
                return sprite
        except Exception as e:
            print(f"Error loading sprite for {entity_name}: {e}")
        
        return None
    
    def _rotate_sprite(self, sprite: Image.Image, direction: Direction) -> Image.Image:
        """Rotate sprite based on entity direction"""
        if direction == Direction.NORTH:
            return sprite
        elif direction == Direction.EAST:
            return sprite.rotate(-90, expand=True)
        elif direction == Direction.SOUTH:
            return sprite.rotate(180, expand=True)
        elif direction == Direction.WEST:
            return sprite.rotate(90, expand=True)
        else:
            return sprite
    
    def draw_entity_sprite(
        self, 
        draw: ImageDraw.ImageDraw, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        entity_name: str,
        direction: Optional[Direction] = None
    ) -> bool:
        """
        Draw entity sprite at the specified coordinates
        
        Args:
            draw: PIL ImageDraw object
            x1, y1: Top-left coordinates
            x2, y2: Bottom-right coordinates  
            entity_name: Name of the entity
            direction: Entity facing direction
            
        Returns:
            True if sprite was drawn, False if fallback needed
        """
        sprite = self._get_sprite(entity_name)
        if not sprite:
            return False
        
        # Apply rotation if needed
        if direction:
            sprite = self._rotate_sprite(sprite, direction)
        
        # Calculate target size
        target_width = int(x2 - x1)
        target_height = int(y2 - y1)
        
        if target_width <= 0 or target_height <= 0:
            return False
        
        # Resize sprite to fit the target area
        resized_sprite = sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Get the underlying PIL image from the draw context
        #img = draw.im
        img = draw._image

        # Paste the sprite with alpha transparency
        if resized_sprite.mode == 'RGBA':
            img.paste(resized_sprite, (int(x1), int(y1)), resized_sprite)
        else:
            img.paste(resized_sprite, (int(x1), int(y1)))
        
        return True
    
    def draw_shape(
        self, 
        draw: ImageDraw.ImageDraw, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        shape_type: str, 
        color: Tuple[int, int, int, int],
        entity_name: Optional[str] = None,
        direction: Optional[Direction] = None
    ):
        """
        Draw entity sprite if available, otherwise fall back to shape
        
        Args:
            draw: PIL ImageDraw object
            x1, y1: Top-left coordinates
            x2, y2: Bottom-right coordinates
            shape_type: Fallback shape type
            color: Fallback color
            entity_name: Name of the entity for sprite lookup
            direction: Entity facing direction
        """
        # Try to draw sprite first
        if entity_name and self.draw_entity_sprite(draw, x1, y1, x2, y2, entity_name, direction):
            return
        
        # Fall back to shape rendering
        self._draw_fallback_shape(draw, x1, y1, x2, y2, shape_type, color, direction)
    
    def _draw_fallback_shape(
        self, 
        draw: ImageDraw.ImageDraw, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        shape_type: str, 
        color: Tuple[int, int, int, int],
        direction: Optional[Direction] = None
    ):
        """Draw fallback geometric shape when sprite is not available"""
        # Simple fallback shapes
        if shape_type == "rectangle":
            draw.rectangle([x1, y1, x2, y2], fill=color, outline=(0, 0, 0, 255))
        elif shape_type == "circle":
            draw.ellipse([x1, y1, x2, y2], fill=color, outline=(0, 0, 0, 255))
        elif shape_type == "triangle":
            # Simple triangle pointing up
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1
            
            if direction == Direction.EAST:
                points = [(x1, y1), (x2, center_y), (x1, y2)]
            elif direction == Direction.SOUTH:
                points = [(x1, y1), (x2, y1), (center_x, y2)]
            elif direction == Direction.WEST:
                points = [(x2, y1), (x1, center_y), (x2, y2)]
            else:  # NORTH or default
                points = [(center_x, y1), (x2, y2), (x1, y2)]
            
            draw.polygon(points, fill=color, outline=(0, 0, 0, 255))
        else:
            # Default to rectangle
            draw.rectangle([x1, y1, x2, y2], fill=color, outline=(0, 0, 0, 255))
    
    def draw_status_indicator(
        self, 
        draw: ImageDraw.ImageDraw, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        status
    ):
        """Draw status indicator in corner of entity"""
        # Small status indicator in top-right corner
        indicator_size = min(6, (x2 - x1) // 4, (y2 - y1) // 4)
        if indicator_size < 2:
            return
        
        # Status color mapping
        status_colors = {
            "no_power": (255, 0, 0, 255),      # Red
            "no_fuel": (255, 165, 0, 255),     # Orange  
            "no_input": (255, 255, 0, 255),    # Yellow
            "working": (0, 255, 0, 255),       # Green
            "idle": (128, 128, 128, 255),      # Gray
        }
        
        color = status_colors.get(str(status), (255, 0, 255, 255))  # Magenta for unknown
        
        indicator_x1 = x2 - indicator_size
        indicator_y1 = y1
        indicator_x2 = x2
        indicator_y2 = y1 + indicator_size
        
        draw.rectangle([indicator_x1, indicator_y1, indicator_x2, indicator_y2], 
                      fill=color, outline=(0, 0, 0, 255))
    
    def draw_direction_indicator(
        self, 
        draw: ImageDraw.ImageDraw, 
        x1: float, 
        y1: float, 
        x2: float, 
        y2: float, 
        direction: Direction
    ):
        """Draw direction indicator (arrow) for entity"""
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Arrow size
        arrow_size = min(8, (x2 - x1) // 3, (y2 - y1) // 3)
        if arrow_size < 3:
            return
        
        # Direction arrow points
        if direction == Direction.NORTH:
            points = [(center_x, center_y - arrow_size), 
                     (center_x - arrow_size//2, center_y + arrow_size//2),
                     (center_x + arrow_size//2, center_y + arrow_size//2)]
        elif direction == Direction.EAST:
            points = [(center_x + arrow_size, center_y),
                     (center_x - arrow_size//2, center_y - arrow_size//2),
                     (center_x - arrow_size//2, center_y + arrow_size//2)]
        elif direction == Direction.SOUTH:
            points = [(center_x, center_y + arrow_size),
                     (center_x - arrow_size//2, center_y - arrow_size//2),
                     (center_x + arrow_size//2, center_y - arrow_size//2)]
        elif direction == Direction.WEST:
            points = [(center_x - arrow_size, center_y),
                     (center_x + arrow_size//2, center_y - arrow_size//2),
                     (center_x + arrow_size//2, center_y + arrow_size//2)]
        else:
            return
        
        draw.polygon(points, fill=(255, 255, 255, 200), outline=(0, 0, 0, 255))
    
    def preload_common_sprites(self):
        """Preload sprites for commonly used entities"""
        if self.transcoder:
            self.transcoder.preload_common_entities()