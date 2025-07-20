"""Renderer management and caching."""

from typing import Dict, Optional, Tuple, Any

from .constants import RENDERERS


class RendererManager:
    """Manages renderer modules and caching."""
    
    def __init__(self):
        """Initialize renderer manager."""
        self._renderer_cache: Dict[str, Any] = {}
    
    def get_renderer(self, entity_name: str) -> Optional[Any]:
        """Get renderer module for entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Renderer module if available, None otherwise
        """
        renderer_name = RENDERERS.get(entity_name)
        if not renderer_name:
            return None

        if renderer_name not in self._renderer_cache:
            self._load_renderer(renderer_name)

        return self._renderer_cache.get(renderer_name)
    
    def _load_renderer(self, renderer_name: str) -> None:
        """Load renderer module dynamically.
        
        Args:
            renderer_name: Name of the renderer to load
        """
        try:
            module_name = renderer_name.replace("-", "_")
            module = __import__(f'fle.env.tools.admin.render.renderers.{module_name}', fromlist=[''])
            self._renderer_cache[renderer_name] = module
        except ImportError as e:
            print(f"Warning: Could not import renderer for {renderer_name}: {e}")
            self._renderer_cache[renderer_name] = None
    
    def get_entity_size(self, entity: Dict) -> Tuple[float, float]:
        """Get entity size.
        
        Args:
            entity: Entity dictionary
            
        Returns:
            Tuple of (width, height) in tiles
        """
        renderer = self.get_renderer(entity['name'])
        if renderer and hasattr(renderer, 'get_size'):
            return renderer.get_size(entity)
        return (1.0, 1.0)


# Global renderer manager instance
renderer_manager = RendererManager()