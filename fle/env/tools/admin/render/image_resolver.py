"""Image resolution and caching functionality."""

from typing import Optional, Dict
from PIL import Image

from .utils import find_fle_sprites_dir
from .profiler import profiler, profile_method


class ImageResolver:
    """Resolve image paths and load images (simple PNG-based resolver)."""

    def __init__(self, images_dir: str = ".fle/sprites"):
        """Initialize image resolver.

        Args:
            images_dir: Directory containing sprite images
        """
        self.images_dir = find_fle_sprites_dir()
        self.cache: Dict[str, Optional[Image.Image]] = {}

    @profile_method(include_args=True)
    def __call__(self, name: str, shadow: bool = False) -> Optional[Image.Image]:
        """Load and cache an image.

        Args:
            name: Name of the sprite (without extension)
            shadow: Whether to load shadow variant

        Returns:
            PIL Image if found, None otherwise
        """
        filename = f"{name}_shadow" if shadow else name

        if filename in self.cache and self.cache[filename]:
            profiler.increment_counter("image_cache_hits")
            return self.cache[filename]

        profiler.increment_counter("image_cache_misses")
        path = self.images_dir / f"{filename}.png"
        if not path.exists():
            self.cache[filename] = None
            profiler.increment_counter("image_not_found")
            return None

        try:
            with profiler.timer("image_load_from_disk"):
                image = Image.open(path).convert("RGBA")
            self.cache[filename] = image
            profiler.increment_counter("images_loaded")
            return image
        except Exception:
            self.cache[filename] = None
            profiler.increment_counter("image_load_errors")
            return None
