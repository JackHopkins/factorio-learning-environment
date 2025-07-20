"""
Blueprint rendering functionality using the FLE environment.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
import asyncio

from fle.env import Direction
from fle.env.instance import FactorioInstance
from fle.env.entities import Position, Layer
from fle.env.game_types import Prototype, prototype_by_name
from fle.eval.algorithms.independent import create_factorio_instance
from vqa_dataset.blueprint_loader import Blueprint, Entity


class BlueprintRenderer:
    """Renders Factorio blueprints to images using the FLE environment."""
    
    def __init__(self, output_dir: str = "vqa_dataset/rendered_images"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.instance = None
        
    def _get_prototype_from_name(self, entity_name: str) -> Optional[Prototype]:
        """Convert entity name to Prototype enum."""
        # Mapping of entity names to Prototype enums
        entity_mapping = {
            'electric-mining-drill': Prototype.ElectricMiningDrill,
            'burner-mining-drill': Prototype.BurnerMiningDrill,
            'assembling-machine-1': Prototype.AssemblingMachine1,
            'assembling-machine-2': Prototype.AssemblingMachine2,
            'assembling-machine-3': Prototype.AssemblingMachine3,
            'stone-furnace': Prototype.StoneFurnace,
            'steel-furnace': Prototype.SteelFurnace,
            'electric-furnace': Prototype.ElectricFurnace,
            'transport-belt': Prototype.TransportBelt,
            'fast-transport-belt': Prototype.FastTransportBelt,
            'express-transport-belt': Prototype.ExpressTransportBelt,
            'inserter': Prototype.Inserter,
            'fast-inserter': Prototype.FastInserter,
            'stack-inserter': Prototype.StackInserter,
            'filter-inserter': Prototype.FilterInserter,
            'long-handed-inserter': Prototype.LongHandedInserter,
            'stack-filter-inserter': Prototype.StackFilterInserter,
            'splitter': Prototype.Splitter,
            'fast-splitter': Prototype.FastSplitter,
            'express-splitter': Prototype.ExpressSplitter,
            'underground-belt': Prototype.UndergroundBelt,
            'fast-underground-belt': Prototype.FastUndergroundBelt,
            'express-underground-belt': Prototype.ExpressUndergroundBelt,
            'small-electric-pole': Prototype.SmallElectricPole,
            'medium-electric-pole': Prototype.MediumElectricPole,
            'big-electric-pole': Prototype.BigElectricPole,
            'substation': Prototype.Substation,
            'wooden-chest': Prototype.WoodenChest,
            'iron-chest': Prototype.IronChest,
            'steel-chest': Prototype.SteelChest,
            'gun-turret': Prototype.GunTurret,
            'laser-turret': Prototype.LaserTurret,
            'pipe': Prototype.Pipe,
            'pipe-to-ground': Prototype.PipeToGround,
            'steam-engine': Prototype.SteamEngine,
            'boiler': Prototype.Boiler,
            'offshore-pump': Prototype.OffshorePump,
            'chemical-plant': Prototype.ChemicalPlant,
            'oil-refinery': Prototype.OilRefinery,
            'pumpjack': Prototype.Pumpjack,
            'lab': Prototype.Lab,
            'radar': Prototype.Radar,
            'roboport': Prototype.Roboport,
            'solar-panel': Prototype.SolarPanel,
            'accumulator': Prototype.Accumulator,
            'beacon': Prototype.Beacon,
            'storage-tank': Prototype.StorageTank,
            'pump': Prototype.Pump,
            'wall': Prototype.Wall,
            'gate': Prototype.Gate,
        }
        
        return entity_mapping.get(entity_name)
    
    async def _setup_instance(self):
        """Setup the FLE instance for rendering."""
        if self.instance is None:
            self.instance: FactorioInstance = await create_factorio_instance(0)
            # Set up initial inventory with all possible items
            self.instance.initial_inventory = {
                "electric-mining-drill": 10,
                "burner-mining-drill": 10,
                "assembling-machine-1": 10,
                "assembling-machine-2": 10,
                "assembling-machine-3": 10,
                "stone-furnace": 10,
                "steel-furnace": 10,
                "electric-furnace": 10,
                "transport-belt": 100,
                "fast-transport-belt": 100,
                "express-transport-belt": 100,
                "inserter": 20,
                "fast-inserter": 20,
                "stack-inserter": 20,
                "filter-inserter": 20,
                "long-handed-inserter": 20,
                "stack-filter-inserter": 20,
                "splitter": 10,
                "fast-splitter": 10,
                "express-splitter": 10,
                "underground-belt": 20,
                "fast-underground-belt": 20,
                "express-underground-belt": 20,
                "small-electric-pole": 20,
                "medium-electric-pole": 10,
                "big-electric-pole": 10,
                "substation": 50,
                "wooden-chest": 10,
                "iron-chest": 10,
                "steel-chest": 10,
                "gun-turret": 10,
                "laser-turret": 10,
                "pipe": 50,
                "pipe-to-ground": 20,
                "steam-engine": 5,
                "boiler": 5,
                "offshore-pump": 5,
                "chemical-plant": 5,
                "oil-refinery": 5,
            }
            self.instance._reset([self.instance.initial_inventory])
            #self.instance.namespace.reset()
    
    async def render_blueprint(
        self, 
        blueprint: Blueprint, 
        output_filename: str,
        padding: int = -5,
        center_view: bool = True
    ) -> str:
        """Render a blueprint to an image file."""
        await self._setup_instance()
        
        game = self.instance.namespace

        # Place all entities from the blueprint
        placed_entities = []
        for entity in blueprint.entities:
            prototype = prototype_by_name[entity.name]
            if prototype is None:
                print(f"Warning: Unknown entity type '{entity.name}', skipping")
                continue
                
            try:
                position = Position(x=entity.position['x'], y=entity.position['y'])
                
                # Handle direction if specified
                if entity.direction is not None:
                    # Place with direction
                    placed_entity = game.place_entity(
                        prototype, 
                        position=position, 
                        direction=Direction(entity.direction)
                    )
                else:
                    # Place without direction
                    placed_entity = game.place_entity(prototype, direction=Direction.UP, position=position)
                    
                if placed_entity:
                    placed_entities.append(placed_entity)
                    
            except Exception as e:
                print(f"Failed to place entity {entity.name} at {position}: {e}")
        
        # Calculate bounding box for rendering
        min_x, min_y, max_x, max_y = blueprint.get_bounding_box()
        
        # Add padding
        render_min_x = min_x - padding
        render_min_y = min_y - padding
        render_max_x = max_x + padding
        render_max_y = max_y + padding
        
        # Calculate center position
        center_x = (render_min_x + render_max_x) / 2
        center_y = (render_min_y + render_max_y) / 2
        
        # Render the blueprint
        try:
            image = game._render(
                position=Position(x=center_x, y=center_y),
                layers=Layer.ALL
            )
            
            # Save the image
            output_path = self.output_dir / output_filename
            image.save(output_path)
            
            return str(output_path)
            
        except Exception as e:
            print(f"Failed to render blueprint: {e}")
            return None
    
    async def render_blueprints_batch(
        self, 
        blueprints: Dict[str, Blueprint],
        max_blueprints: Optional[int] = None
    ) -> Dict[str, str]:
        """Render multiple blueprints in batch."""
        rendered_paths = {}
        
        blueprint_items = list(blueprints.items())
        if max_blueprints:
            blueprint_items = blueprint_items[:max_blueprints]
        
        for i, (name, blueprint) in enumerate(blueprint_items):
            print(f"Rendering blueprint {i+1}/{len(blueprint_items)}: {name}")
            
            # Create safe filename
            safe_name = name.replace('/', '_').replace('.json', '.png')
            
            try:
                output_path = await self.render_blueprint(blueprint, safe_name)
                if output_path:
                    rendered_paths[name] = output_path
                    print(f"Successfully rendered: {output_path}")
                else:
                    print(f"Failed to render: {name}")
            except Exception as e:
                print(f"Error rendering {name}: {e}")
        
        return rendered_paths
    
    def cleanup(self):
        """Clean up the instance."""
        # if self.instance:
        #     self.instance.close()
        #     self.instance = None
        pass


# Utility function for quick rendering
async def render_blueprint_file(blueprint_path: str, output_path: str) -> str:
    """Quick utility to render a single blueprint file."""
    from vqa_dataset.blueprint_loader import BlueprintLoader
    
    loader = BlueprintLoader("")
    blueprint = loader.load_blueprint(blueprint_path)
    
    renderer = BlueprintRenderer()
    try:
        result = await renderer.render_blueprint(blueprint, output_path)
        return result
    finally:
        renderer.cleanup()


# Example usage and testing
if __name__ == "__main__":
    async def _test_renderer():
        from vqa_dataset.blueprint_loader import BlueprintLoader
        
        # Load some blueprints
        loader = BlueprintLoader("../fle/agents/data/blueprints_to_policies/blueprints")
        blueprints = loader.load_all_blueprints(['example', 'other'])
        
        # Filter to smaller blueprints for testing
        blueprints = loader.filter_blueprints_by_complexity(blueprints, max_entities=50)
        
        print(f"Loaded {len(blueprints)} blueprints for testing")
        
        # Render a few blueprints
        renderer = BlueprintRenderer()
        try:
            rendered = await renderer.render_blueprints_batch(blueprints, max_blueprints=5)
            print(f"Successfully rendered {len(rendered)} blueprints")
            for name, path in rendered.items():
                print(f"  {name} -> {path}")
        finally:
            renderer.cleanup()
    
    # Uncomment to test
    asyncio.run(_test_renderer())