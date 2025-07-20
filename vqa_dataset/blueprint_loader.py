"""
Blueprint loading and parsing utilities for VQA dataset generation.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from fle.env import Entity


@dataclass
class Entity:
    """Represents a single entity in a blueprint."""
    entity_number: int
    name: str
    position: Dict[str, float]
    direction: Optional[int] = None
    items: Optional[List[Dict]] = None
    connections: Optional[Dict] = None
    control_behavior: Optional[Dict] = None
    type: Optional[str] = None
    recipe: Any = None
    filters: Optional[Any] = None
    icons: Optional[str] = None
    description: Optional[str] = None
    input_priority: Optional[int] = None
    output_priority: Optional[int] = None
    filter: Optional[str] = None
    color: Optional[str] = None
    bar: Optional[str] = None
    recipe_quality: Optional[str] = None
    use_filters: Optional[Any] = None


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        return cls(**data)


@dataclass
class Blueprint:
    """Represents a Factorio blueprint with analysis capabilities."""
    entities: List[Entity]
    label: Optional[str] = None
    icons: Optional[List[Dict]] = None
    version: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Blueprint':
        entities = [Entity.from_dict(e) for e in data.get('entities', [])]
        return cls(
            entities=entities,
            label=data.get('label'),
            icons=data.get('icons'),
            version=data.get('version')
        )
    
    def get_entity_counts(self) -> Counter:
        """Count entities by type."""
        return Counter(entity.name for entity in self.entities)
    
    def get_unique_entity_types(self) -> List[str]:
        """Get list of unique entity types in the blueprint."""
        return list(set(entity.name for entity in self.entities))
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.name == entity_type]
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Get bounding box (min_x, min_y, max_x, max_y) of all entities."""
        if not self.entities:
            return (0, 0, 0, 0)
        
        positions = [(e.position['x'], e.position['y']) for e in self.entities]
        min_x = min(pos[0] for pos in positions)
        max_x = max(pos[0] for pos in positions)
        min_y = min(pos[1] for pos in positions)
        max_y = max(pos[1] for pos in positions)
        
        return (min_x, min_y, max_x, max_y)
    
    def get_dimensions(self) -> Tuple[float, float]:
        """Get width and height of the blueprint."""
        min_x, min_y, max_x, max_y = self.get_bounding_box()
        return (max_x - min_x, max_y - min_y)
    
    def has_entity_type(self, entity_type: str) -> bool:
        """Check if blueprint contains a specific entity type."""
        return any(e.name == entity_type for e in self.entities)
    
    def get_total_entity_count(self) -> int:
        """Get total number of entities in the blueprint."""
        return len(self.entities)


class BlueprintLoader:
    """Loads and manages Factorio blueprints for VQA dataset generation."""
    
    def __init__(self, blueprints_dir: str):
        self.blueprints_dir = Path(blueprints_dir)
        
    def load_blueprint(self, blueprint_path: str) -> Blueprint:
        """Load a single blueprint from a JSON file."""
        with open(blueprint_path, 'r') as f:
            data = json.load(f)
        return Blueprint.from_dict(data)
    
    def load_all_blueprints(self, subdirs: Optional[List[str]] = None) -> Dict[str, Blueprint]:
        """Load all blueprints from specified subdirectories."""
        blueprints = {}
        
        if subdirs is None:
            # Default subdirectories
            subdirs = ['balancing', 'other', 'example', 'decoded']
        
        for subdir in subdirs:
            subdir_path = self.blueprints_dir / subdir
            if not subdir_path.exists():
                continue
                
            for file_path in subdir_path.glob('*.json'):
                try:
                    blueprint = self.load_blueprint(file_path)
                    # Use relative path as key
                    key = f"{subdir}/{file_path.name}"
                    blueprints[key] = blueprint
                except Exception as e:
                    print(f"Failed to load {file_path}: {e}")
        
        return blueprints
    
    def filter_blueprints_by_complexity(
        self, 
        blueprints: Dict[str, Blueprint], 
        min_entities: int = 1, 
        max_entities: int = 1000
    ) -> Dict[str, Blueprint]:
        """Filter blueprints by entity count."""
        return {
            name: bp for name, bp in blueprints.items()
            if min_entities <= bp.get_total_entity_count() <= max_entities
        }
    
    def filter_blueprints_by_entity_types(
        self, 
        blueprints: Dict[str, Blueprint], 
        required_types: Optional[List[str]] = None,
        forbidden_types: Optional[List[str]] = None
    ) -> Dict[str, Blueprint]:
        """Filter blueprints by required/forbidden entity types."""
        filtered = {}
        
        for name, bp in blueprints.items():
            entity_types = set(bp.get_unique_entity_types())
            
            # Check required types
            if required_types and not all(req_type in entity_types for req_type in required_types):
                continue
                
            # Check forbidden types
            if forbidden_types and any(forb_type in entity_types for forb_type in forbidden_types):
                continue
                
            filtered[name] = bp
            
        return filtered
    
    def get_blueprint_statistics(self, blueprints: Dict[str, Blueprint]) -> Dict[str, Any]:
        """Get statistics about the loaded blueprints."""
        if not blueprints:
            return {}
        
        total_blueprints = len(blueprints)
        entity_counts = [bp.get_total_entity_count() for bp in blueprints.values()]
        all_entity_types = set()
        for bp in blueprints.values():
            all_entity_types.update(bp.get_unique_entity_types())
        
        stats = {
            'total_blueprints': total_blueprints,
            'min_entities': min(entity_counts),
            'max_entities': max(entity_counts),
            'avg_entities': sum(entity_counts) / total_blueprints,
            'unique_entity_types': len(all_entity_types),
            'entity_types': sorted(all_entity_types)
        }
        
        return stats


# Utility functions for common entity types
COMMON_ENTITY_TYPES = {
    'mining': ['electric-mining-drill', 'burner-mining-drill'],
    'production': ['assembling-machine-1', 'assembling-machine-2', 'assembling-machine-3'],
    'smelting': ['stone-furnace', 'steel-furnace', 'electric-furnace'],
    'transport': ['transport-belt', 'fast-transport-belt', 'express-transport-belt'],
    'insertion': ['inserter', 'fast-inserter', 'stack-inserter', 'filter-inserter'],
    'power': ['steam-engine', 'steam-turbine', 'solar-panel', 'nuclear-reactor'],
    'poles': ['small-electric-pole', 'medium-electric-pole', 'big-electric-pole'],
    'chests': ['wooden-chest', 'iron-chest', 'steel-chest'],
    'defense': ['gun-turret', 'laser-turret', 'artillery-turret'],
    'splitters': ['splitter', 'fast-splitter', 'express-splitter'],
    'underground': ['underground-belt', 'fast-underground-belt', 'express-underground-belt'],
    'pipes': ['pipe', 'pipe-to-ground'],
    'chemical': ['chemical-plant', 'oil-refinery', 'pumpjack'],
    'science': ['lab'],
}


def categorize_entity_type(entity_name: str) -> str:
    """Categorize an entity type into a broader category."""
    for category, entity_types in COMMON_ENTITY_TYPES.items():
        if entity_name in entity_types:
            return category
    return 'other'