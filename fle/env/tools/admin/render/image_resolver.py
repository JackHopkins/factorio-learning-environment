"""Image resolution and caching functionality."""

from pathlib import Path
from typing import Optional, Dict
from PIL import Image

from .utils import find_fle_sprites_dir


class ImageResolver:
    """Resolve image paths and load images (simple PNG-based resolver)."""

    def __init__(self, images_dir: str = ".fle/sprites"):
        """Initialize image resolver.
        
        Args:
            images_dir: Directory containing sprite images
        """
        self.images_dir = find_fle_sprites_dir()
        self.cache: Dict[str, Optional[Image.Image]] = {}

    def __call__(self, name: str, shadow: bool = False) -> Optional[Image.Image]:
        """Load and cache an image.
        
        Args:
            name: Name of the sprite (without extension)
            shadow: Whether to load shadow variant
            
        Returns:
            PIL Image if found, None otherwise
        """
        filename = f"{name}_shadow" if shadow else name

        if filename in self.cache:
            return self.cache[filename]

        path = self.images_dir / f"{filename}.png"
        if not path.exists():
            self.cache[filename] = None
            return None

        try:
            image = Image.open(path).convert('RGBA')
            self.cache[filename] = image
            return image
        except Exception:
            self.cache[filename] = None
            return None