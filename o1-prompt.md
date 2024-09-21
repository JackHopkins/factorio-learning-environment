You have access to the following API.

Types:
```
import enum

from factorio_entities import *


class PrototypeName(enum.Enum):
    AssemblingMachine = "assembling-machine-1"
    BurnerInserter = "burner-inserter"
    BurnerMiningDrill = "burner-mining-drill"
    ElectricMiningDrill = "electric-mining-drill"
    StoneFurnace = "stone-furnace"
    TransportBelt = "transport-belt"
    OffshorePump = "offshore-pump"
    Boiler = "boiler"
    SteamEngine = "steam-engine"
    Pipe = "pipe"
    SmallElectricPole = "small-electric-pole"
    IronChest = "iron-chest"

class ResourceName(enum.Enum):
    Coal = "coal"
    IronOre = "iron-ore"
    CopperOre = "copper-ore"
    Stone = "stone"
    Water = "water"
    CrudeOil = "crude-oil"
    UraniumOre = "uranium-ore"


class Prototype(enum.Enum):
    AssemblingMachine1 = "assembling-machine-1", AssemblingMachine1
    BurnerInserter = "burner-inserter", BurnerInserter
    BurnerMiningDrill = "burner-mining-drill", BurnerMiningDrill
    ElectricMiningDrill = "electric-mining-drill", MiningDrill
    StoneFurnace = "stone-furnace", Furnace
    TransportBelt = "transport-belt", TransportBelt
    OffshorePump = "offshore-pump", OffshorePump
    Boiler = "boiler", Boiler
    #Generator = "generator", Generator
    SteamEngine = "steam-engine", Generator
    Pipe = "pipe", Entity
    IronChest = "iron-chest", Entity
    WoodenChest = "wooden-chest", Entity
    IronGearWheel = "iron-gear-wheel", Entity
    Coal = "coal", None
    IronPlate = "iron-plate", None
    CopperPlate = "copper-plate", None
    SmallElectricPole = "small-electric-pole", Entity
    IronOre = "iron-ore", None
    CopperOre = "copper-ore", None
    Stone = "stone", None
    CopperCable = "copper-cable", None


class Resource:
    Coal = "coal", ResourcePatch
    IronOre = "iron-ore", ResourcePatch
    CopperOre = "copper-ore", ResourcePatch
    Stone = "stone", ResourcePatch
    Water = "water", ResourcePatch
    CrudeOil = "crude-oil", ResourcePatch
    UraniumOre = "uranium-ore", ResourcePatch
    Wood = "tree-01", ResourcePatch
```

Entities:
```
from typing import Tuple, Any, Union, Dict
from typing import List, Optional

from pydantic import BaseModel, PrivateAttr



class Inventory(BaseModel):
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__()
        self.__dict__.update(data)

    def __getitem__(self, key, default=None):
        try:
            if hasattr(key, 'value'):
                name, _ = key.value
            elif isinstance(key, tuple):
                name = key[0]
            else:
                name = key
        except Exception as e:
            pass
        return self.__dict__[name] if name in self.__dict__ else 0

    def get(self, key, default=0):
        try:
            if hasattr(key, 'value'):
                name, _ = key.value
            else:
                name = key
        except Exception as e:
            pass

        item = self.__getitem__(name)
        return item if item else default

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    #def get(self, key):
    #    return self.__getitem__(key) #getattr(self, key, default)

class Position(BaseModel):
    x: float
    y: float

    def __add__(self, other):
        return Position(x=self.x + other.x, y=self.y + other.y)

    def is_close(self, a: 'Position', tolerance: float = 0.1):
        return abs(self.x - a.x) < tolerance and abs(self.y - a.y) < tolerance


class BoundingBox(BaseModel):
    left_top: Position
    right_bottom: Position
    center: Position


class ResourcePatch(BaseModel):
    name: str
    size: int
    bounding_box: BoundingBox


class Dimensions(BaseModel):
    width: float
    height: float


class TileDimensions(BaseModel):
    tile_width: float
    tile_height: float


class Ingredient(BaseModel):
    name: str
    count: int


class Recipe(BaseModel):
    name: str
    ingredients: List[Ingredient]


class BurnerType(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    fuel_inventory: Union[Inventory, List[Dict[str, Any]]]
    remaining_fuel: Optional[float] = 0


class Entity(BaseModel):
    name: str
    position: Position
    direction: int
    energy: float
    type: str
    dimensions: Dimensions
    tile_dimensions: TileDimensions
    prototype: Any  # Prototype
    health: float


class TransportBelt(Entity):
    input_position: Position
    output_position: Position


class Inserter(Entity):
    pickup_position: Position
    drop_position: Position


class MiningDrill(Entity):
    drop_position: Position


class BurnerInserter(Inserter, BurnerType):
    pass


class BurnerMiningDrill(MiningDrill, BurnerType):
    pass


class AssemblingMachine1(Entity):
    recipe: Optional[Recipe] = None  # Prototype


class FluidHandler(Entity):
    connection_points: List[Position]


class Boiler(FluidHandler):
    steam_output_point: Position


class Generator(FluidHandler):
    pass


class OffshorePump(FluidHandler):
    fluid_box: Optional[dict] = {}


class Furnace(Entity, BurnerType):
    input_inventory: Union[Inventory, List[Dict[str, Any]]]
```

Methods:
```
set_entity_recipe(entity: Entity, prototype: Prototype) -> bool
"""
Sets the recipe of an given entity.
:param entity: Entity to set recipe
:param recipe: Recipe to set
:return: True if recipe was set successfully
"""

place_entity_next_to(entity: Prototype, reference_position: Position = Position(x=0.0, y=0.0), direction: Direction = 1, spacing: int = 0) -> Entity
"""
Places an entity next to an existing entity, with an optional space in-between (0 space means adjacent).
In order to place something with a gap, you must increase the spacing parameter.
:param entity: Entity to place
:param reference_position: Position of existing entity or position to place entity next to
:param direction: Direction to place entity from reference_position
:param spacing: Space between entity and reference_position
:example: place_entity_next_to(Prototype.WoodenChest, Position(x=0, y=0), direction=Direction.UP, spacing=1)
:return: Entity placed (with position of x=0, y=-1)
"""

pickup_entity(entity: Entity, position: Position) -> bool
"""
The agent picks up an given entity prototype e at position (x, y) if it exists on the world.
:param entity: Entity prototype to pickup, e.g Prototype.IronPlate
:param position: Position to pickup entity
:example: pickup_entity(Prototype.IronPlate, stone_furnace.position)
:return:
"""

craft_item(entity: Prototype, quantity: int = 1) -> bool
"""
Craft an item from a Prototype if the ingredients exist in your inventory.
:param entity: Entity to craft
:param quantity: Quantity to craft
:example craft_item(Prototype.Pipe, 1)
:return: True if crafting was successful
"""

can_place_entity(entity: Prototype, direction: Direction = <Direction.UP: 0>, position: Position = Position(x=0.0, y=0.0)) -> bool
"""
Tests to see if an entity e can be placed at local position (x, y).
:param entity: Entity to place from inventory
:param direction: Cardinal direction to place entity
:param position: Position to place entity
:param exact: If True, place entity at exact position, else place entity at nearest possible position
:example stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
:return: Entity object
"""

get_entity(entity: Prototype, position: Position) -> Entity
"""
Get a given entity prototype at position (x, y) if it exists on the world.
:param entity: Entity prototype to get, e.g Prototype.IronPlate
:param position: Position to get entity
:example stone_furnace = get_entity(Prototype.StoneFurnace, nearest(Prototype.StoneFurnace))
:return: Entity object
"""

inspect_inventory(entity=None) -> Inventory
"""
Inspects the inventory of the given entity. If no entity is given, this inspects your own inventory.
:param entity: Entity to inspect
:example: iron_chest_inventory = inspect_inventory(nearest(Prototype.IronChest))
:return: Inventory of the given entity
"""

get_path(path_handle: int, max_attempts: int = 10) -> List[Position]
"""
Retrieve a path requested from the game, using backoff polling.
"""

place_entity(entity: Prototype, direction: Direction = <Direction.UP: 0>, position: Position = Position(x=0.0, y=0.0), exact: bool = False) -> Entity
"""
Places an entity e at local position (x, y) if the agent has enough resources.
:param entity: Entity to place from inventory
:param direction: Cardinal direction to place entity
:param position: Position to place entity
:param exact: If True, place entity at exact position, else place entity at nearest possible position
:example stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
:return: Entity object
"""

move_to(position: Position, laying: Prototype = None, leading: Prototype = None) -> bool
"""
Move to a position.
:param position: Position to move to.
:param laying: Entity to lay down behind you as you move. e.g. 'Prototype.TransportBelt', facing away from you.
:param leading: Entity to lay down in front of you as you move. e.g. 'Prototype.TransportBelt', facing towards you.
:example move_to(nearest(Prototype.StoneFurnace), laying=Prototype.TransportBelt)
:return:
"""

print(*args) -> bool
"""
Recursively print the
:param args:
:return:
"""

connect_entities(source: Union[Position, Entity], target: Union[Position, Entity], connection_type: Prototype = <Prototype.Pipe: ('pipe', <class 'Entity'>)>) -> List[Entity]
"""
Connect two entities or positions.
:param source: First entity or position
:param target: Second entity or position
:param connection_type: a Pipe, TransportBelt or ElectricPole
:example connect_entities(source=boiler, target=generator, connection_type=Prototype.Pipe)
:example connect_entities(source=miner, target=stone_furnace, connection_type=Prototype.TransportBelt)
:return: List of entities that were created
"""

get_resource_patch(resource: Resource, position: Position) -> ResourcePatch
"""
Get the resource patch at position (x, y) if it exists on the world.
:param resource: Resource to get, e.g Resource.Coal
:param position: Position to get resource patch
:example coal_patch_at_origin = get_resource_patch(Resource.Coal, Position(x=0, y=0))
:return: ResourcePatch
"""

harvest_resource(position: Position, quantity=1) -> None
"""
Harvest a resource at position (x, y) if it exists on the world.
:param position: Position to harvest resource
:param quantity: Quantity to harvest
:example harvest_resource(nearest(Resource.Coal), 5)
:example harvest_resource(nearest(Resource.Stone), 5)
:return: True if harvest was successful
"""

sleep(seconds: int) -> bool
"""
Sleep for up to 15 seconds before continuing. Useful for waiting for actions to complete.
:param seconds: Number of seconds to sleep.
:return: True if sleep was successful.
"""

insert_item(entity: Prototype, target: Entity, quantity=5) -> int
"""
The agent inserts an item into an target entity's inventory
:param entity: Entity type to insert from inventory
:param target: Entity to insert into
:param quantity: Quantity to insert
:example: insert_item(Prototype.IronPlate, nearest(Prototype.IronChest), 5)
:return: The entity inserted into
"""

extract_item(entity: Prototype, position: Position, quantity=5) -> bool
"""
Extract an item from an entity's inventory at position (x, y) if it exists on the world.
:param entity: Entity prototype to extract, e.g Prototype.IronPlate
:param source_position: Position to extract entity
:param quantity: Quantity to extract
:example extract_item(Prototype.IronPlate, stone_furnace.position, 5)
:example extract_item(Prototype.CopperWire, Position(x=0, y=0), 5)
:return True if extraction was successful
"""

get_prototype_recipe(prototype: Union[Prototype, str]) -> Recipe
"""
Get the recipe of the given entity prototype.
:param prototype: Prototype to get recipe from
:return: Recipe of the given prototype
"""

inspect_entities(position: Position = None, radius=10) -> List[Dict[str, Any]]
"""
Inspect entities in a given radius around your position.
:param radius: The radius to inspect
:param position: The position to inspect (if None, use your position)
:example: entities_around_origin = inspect_entities(10, Position(x=0, y=0))
:return: A list of entities
"""

request_path(start: Position, finish: Position, max_attempts: int = 10) -> int
"""
Asynchronously request a path from start to finish from the game.
"""

rotate_entity(entity: Entity, direction: Direction = <Direction.UP: 0>) -> bool
"""
Rotate an entity at position (x, y) if it exists on the world.
:param entity: Entity to rotate
:param direction: Direction to rotate
:example rotate_entity(iron_chest, Direction.UP)
:return: True if rotation was successful
"""

nearest(type: Union[Prototype, Resource]) -> Position
"""
Find the nearest typed entity or resource to the player.
:param type: Entity or resource type to find
:return: Position of nearest entity or resource
:example nearest(Prototype.TransportBelt)
:example nearest(Resource.Coal)
"""
``` 

Tests:
```
Project Path: /Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests

Source Tree:

```
tests
├── test_utils.py
├── conftest.py
├── test_actions.py
├── test_typing.py
├── test_observations.py
├── actions
│   ├── test_inspect_entities.py
│   ├── test_request_path.py
│   ├── test_can_place.py
│   ├── test_rotate.py
│   ├── test_get_prototype_recipe.py
│   ├── test_get_resource_patch.py
│   ├── test_harvest_resource.py
│   ├── test_skill.py
│   ├── test_save_load.py
│   ├── test_set_entity_recipe.py
│   ├── test_place.py
│   ├── test_craft.py
│   ├── test_place_entity_next_to.py
│   ├── test_move_to.py
│   ├── test_nearest.py
│   └── test_inspect_inventory.py
└── functional
    ├── test_connect.py
    ├── test_objectives.py
    ├── test_electricity_unit.py
    ├── test_place_next_to_and_rotate.py
    ├── test_auto_refilling_coal.py
    ├── test_small_iron_factory.py
    ├── test_blueprints.py
    └── test_factory_unit.py

```

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/test_utils.py`:

```````py
import unittest
from typing import Tuple

import numpy as np
from numpy import ndarray, zeros

from client.utils import roll, stitch


class TestUtils(unittest.TestCase):

    def setUp(self) -> None:
        bounding_box = 3
        self.grid_world = np.array([[1,2,3],[4,5,6], [7,8,9]], np.int32)

        self.movement_vectors = np.array([(0, 0), (1, 0), (-1, 0), (0, -1), (0, 1)])

        self.rolled_down_fixture = np.array([[7, 8, 9], [1, 2, 3], [4, 5, 6]])
        self.rolled_up_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])
        self.rolled_left_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])
        self.rolled_right_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])

        self.stitched_up_fixture = np.array([[0, 0, 0,], [1, 2, 3,], [4, 5, 6]])
        self.stitched_down_fixture = np.array([[4, 5, 6], [7, 8, 9], [0, 0, 0]])
        self.stitched_left_fixture = np.array([[0, 1, 2], [0, 4, 5], [0, 7, 8]])
        self.stitched_right_fixture = np.array([[2, 3, 0], [5, 6, 0], [8, 9, 0]])
        self.new_field_up = (0, -1)
        self.new_field_down = (0, 1)
        self.new_field_left = (-1, 0)
        self.new_field_right = (1, 0)

        self.new_line = zeros((3, 1))


    def test_row_stitching(self):
        #self.assertEqual(stitch(roll(self.grid_world, self.new_field_up), self.new_line,  self.new_field_up).all(), self.rolled_up_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_up).all(), self.stitched_up_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_down).all(), self.stitched_down_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_left).all(), self.stitched_left_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_right).all(), self.stitched_right_fixture.all())

    def test_movement_vectors(self):
        self.assertEqual(roll(self.grid_world, self.new_field_up).all(), self.rolled_up_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_down).all(), self.rolled_down_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_left).all(), self.rolled_left_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_right).all(), self.rolled_right_fixture.all())

    def test_rolling(self):
        roll_down = np.roll(self.grid_world, 1, 0)#self.new_field_left)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_up = np.roll(self.grid_world, -1, 0)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_right = np.roll(self.grid_world, 1, 1)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_left = np.roll(self.grid_world, -1, 1)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())

if __name__ == '__main__':
    unittest.main()

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/conftest.py`:

```````py
import pytest
from functional.test_connect import test_place_and_connect_entities_in_grid

@pytest.fixture(scope="session")
def instance():
    from src.factorio_instance import FactorioInstance
    try:
        instance = FactorioInstance(address='localhost',
                                    bounding_box=200,
                                    tcp_port=27015,
                                    inventory={
                                        'coal': 50,
                                        'copper-plate': 50,
                                        'iron-plate': 50,
                                        'iron-chest': 2,
                                        'burner-mining-drill': 3,
                                        'electric-mining-drill': 1,
                                        'assembling-machine-1': 1,
                                        'stone-furnace': 9,
                                        'transport-belt': 50,
                                        'boiler': 1,
                                        'burner-inserter': 32,
                                        'pipe': 15,
                                        'steam-engine': 1,
                                        'small-electric-pole': 10
                                })
        yield instance
    except Exception as e:
        raise e


```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/test_actions.py`:

```````py
from typing import List

import pytest

from client.factorio_types import Prototype, Resource
from factorio_entities import Entity, Position



```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/test_typing.py`:

```````py
import unittest

from factorio_entities import Position, BurnerMiningDrill, AssemblingMachine
from factorio_types import Prototype


class TestActions(unittest.TestCase):
    def test_fuel(self):
        lua_response = {
            "name": "assembling-machine-1",
            "position": {"x": 0, "y": 0},
            "direction": 0,
            "energy": 0,
            "type": "assembling-machine",
            "dimensions": {"x": 0, "y": 0},
            "tile_dimensions": {"x": 0, "y": 0},
            "recipe": {
                "name": "iron-plate",
                "ingredients": [{"name": "iron-ore", "count": 1}],
            }
        }
        assembling_machine: AssemblingMachine = AssemblingMachine(**lua_response)
        from controllers.get_entity import GetEntity
        get_entity = GetEntity(None, None)

        get_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
        burner_mining_drill = BurnerMiningDrill(**lua_response)

        print(burner_mining_drill.json())
        print(burner_mining_drill.drop_position)


if __name__ == '__main__':
    unittest.main()

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/test_observations.py`:

```````py
import unittest


class TestObservations(unittest.TestCase):
    def test_get_environment(self):
        self.assertEqual(True, False)

    def test_get_inventory(self):
        self.assertEqual(True, False)

    def test_get_position(self):
        self.assertEqual(True, False)

    def test_get_resources(self):
        self.assertEqual(True, False)

if __name__ == '__main__':
    unittest.main()

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_inspect_entities.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_inspect_entities(game):
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    inspected = game.inspect_entities(radius=1, position=Position(x=chest.position.x, y=chest.position.y))

    assert len(inspected) == 2
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_request_path.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_path(game):
    """
    Get a path from (0, 0) to (10, 0)
    :param game:
    :return:
    """
    path = game.request_path(Position(x=0, y=0), Position(x=10, y=0))

    assert path
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_can_place.py`:

```````py
import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_can_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Pipe]
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place == True
    game.place_entity(Prototype.Pipe, position=(5, 0))
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place == False


```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_rotate.py`:

```````py
import pytest

from factorio_instance import Direction
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_rotate_boiler(game):
    # place the boiler next to the offshore pump
    from factorio_entities import Position
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=Position(x=0, y=0),
                                       direction=Direction.RIGHT,
                                       spacing=2)
    # orthogonal direction to the boiler
    orthogonal_direction = Direction.UP

    # rotate the boiler to face the offshore pump
    boiler = game.rotate_entity(boiler, orthogonal_direction)

    # assert that the boiler is facing the offshore pump
    assert boiler.direction == orthogonal_direction.value

def test_rotate_transport_belt(game):
    # Place a transport belt
    transport_belt = game.place_entity(Prototype.TransportBelt, position=(0, 0), direction=Direction.UP)
    rotate_entity(game, transport_belt)


def test_rotate_inserter(game):
    # Place a burner inserter
    inserter = game.place_entity(Prototype.BurnerInserter, position=(0, 0), direction=Direction.UP)
    rotate_entity(game, inserter)

def rotate_entity(game, entity):
    # Rotate the transport belt right
    entity = game.rotate_entity(entity, direction=Direction.RIGHT)

    # Assert that the direction of the transport belt has been updated
    assert entity.direction == Direction.RIGHT.value

    entity = game.rotate_entity(entity, direction=Direction.LEFT)

    assert entity.direction == Direction.LEFT.value

    entity = game.rotate_entity(entity, direction=Direction.DOWN)

    assert entity.direction == Direction.DOWN.value

    entity = game.rotate_entity(entity, direction=Direction.UP)

    assert entity.direction == Direction.UP.value

    game.reset()
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_get_prototype_recipe.py`:

```````py
import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'assembling-machine-1': 1}
    instance.reset()
    yield instance

def test_get_recipe(game):

    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)

    assert recipe.ingredients[0].name == 'iron-plate'
    assert recipe.ingredients[0].count == 2
    game.reset()
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_get_resource_patch.py`:

```````py
import pytest

from factorio_entities import ResourcePatch
from factorio_instance import FactorioInstance
from factorio_types import Resource

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_get_resource_patch(game: FactorioInstance):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    resource_patch: ResourcePatch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    assert resource_patch.name == Resource.Coal[0]
    assert resource_patch.size > 0
    assert resource_patch.bounding_box.left_top.x
    assert resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y
    assert resource_patch.bounding_box.right_bottom.y
    assert resource_patch.bounding_box.left_top.x < resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y < resource_patch.bounding_box.right_bottom.y
    assert resource_patch.bounding_box.left_top.x < resource_patch.bounding_box.right_bottom.x
    assert resource_patch.bounding_box.left_top.y < resource_patch.bounding_box.right_bottom.y

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_harvest_resource.py`:

```````py
import pytest

from factorio_types import Resource

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_harvest_resource(game):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    inventory = game.inspect_inventory()
    # Check initial inventory
    initial_coal = inventory[Resource.Coal]
    # Find nearest coal resource
    nearest_coal = game.nearest(Resource.Coal)
    # Move to the coal resource
    game.move_to(nearest_coal)
    # Harvest coal
    game.harvest_resource(nearest_coal, quantity=5)  # Assuming there is a coal resource at (10, 10)
    # Check the inventory after harvesting
    final_coal = game.inspect_inventory()[Resource.Coal]
    # Assert that the coal has been added to the inventory
    assert 5 == final_coal - initial_coal
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_skill.py`:

```````py
import pytest
from contextlib import contextmanager

from factorio_types import Prototype

class SkillExample:
    def __init__(self, instance):
        self.instance = instance

    def setup(self):
        # Add any setup logic here
        self.instance.reset()
        # For example, you might want to add some initial items to the inventory
        self.instance.add_to_inventory(Prototype.IronPlate, 50)
        self.instance.add_to_inventory(Prototype.CopperPlate, 50)

    def teardown(self):
        self.instance.reset()

@pytest.fixture()
def game(instance):
    test_setup = GameTestSetup(instance)

    @contextmanager
    def game_context():
        test_setup.setup()
        try:
            yield test_setup.instance
        finally:
            test_setup.teardown()

    return game_context()

def test_craft_item(game):
    """
    Craft an iron chest and assert that the iron plate has been deducted and the iron chest has been added.
    :param game:
    :return:
    """

    # Check initial inventory
    initial_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    initial_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Craft an iron chest
    game.craft_item(Prototype.IronChest, quantity=1)

    # Check the inventory after crafting
    final_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    final_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Assert that the iron plate has been deducted and the iron chest has been added
    assert initial_iron_plate - 8 == final_iron_plate
    assert initial_iron_chest + 1 == final_iron_chest
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_save_load.py`:

```````py


import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_save_load(game):

    game._send("/c game.server_save('test')")
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)
    game._send("/c game.server_load('test')")
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_set_entity_recipe.py`:

```````py
import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    game.initial_inventory = {'assembling-machine-1': 1}
    instance.reset()
    yield instance

def test_set_entity_recipe(game):
    # Place an assembling machine
    assembling_machine = game.place_entity(Prototype.AssemblingMachine1, position=(0, 0))

    # Set a recipe for the assembling machine
    assembling_machine = game.set_entity_recipe(assembling_machine, Prototype.IronGearWheel)

    # Assert that the recipe of the assembling machine has been updated
    prototype_name, _ = Prototype.IronGearWheel.value

    assert assembling_machine.recipe == prototype_name

    game.reset()
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_place.py`:

```````py
import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] - 1

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_craft.py`:

```````py
import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_craft_item(game):
    """
    Craft an iron chest and assert that the iron plate has been deducted and the iron chest has been added.
    :param game:
    :return:
    """

    # Check initial inventory
    initial_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    initial_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Craft an iron chest
    game.craft_item(Prototype.IronChest, quantity=1)

    # Check the inventory after crafting
    final_iron_plate = game.inspect_inventory()[Prototype.IronPlate]
    final_iron_chest = game.inspect_inventory()[Prototype.IronChest]

    # Assert that the iron plate has been deducted and the iron chest has been added
    assert initial_iron_plate - 8 == final_iron_plate
    assert initial_iron_chest + 1 == final_iron_chest

    game.reset()
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_place_entity_next_to.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'boiler': 1,
        'transport-belt': 1,
        'stone-furnace': 1,
        'burner-mining-drill': 1,
        'burner-inserter': 2,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'steam-engine': 1,
        'pipe': 1,
        'offshore-pump': 1,
    }
    instance.reset()
    yield instance

@pytest.fixture
def entity_prototype():
    return Prototype.Boiler

@pytest.fixture
def surrounding_entity_prototype():
    return Prototype.TransportBelt


def calculate_expected_position(ref_pos, direction, spacing, ref_entity, entity_to_place):
    ref_dimensions = ref_entity.tile_dimensions
    entity_dimensions = entity_to_place.tile_dimensions

    def align_to_grid(pos):
        return Position(x=round(pos.x * 2) / 2, y=round(pos.y * 2) / 2)

    def should_have_y_offset(entity):
        return entity.tile_dimensions.tile_width % 2 == 1

    y_offset = 0.5 if should_have_y_offset(entity_to_place) else 0

    if direction == Direction.RIGHT:
        return align_to_grid(Position(x=ref_pos.x + ref_dimensions.tile_width / 2 + entity_dimensions.tile_width / 2 + spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.DOWN:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y + ref_dimensions.tile_height / 2 + entity_dimensions.tile_height / 2 + spacing + y_offset))
    elif direction == Direction.LEFT:
        return align_to_grid(Position(x=ref_pos.x - ref_dimensions.tile_width / 2 - entity_dimensions.tile_width / 2 - spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.UP:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y - ref_dimensions.tile_height / 2 - entity_dimensions.tile_height / 2 - spacing + y_offset))


def test_place_entities_of_different_sizes(game):
    entity_pairs = [
        (Prototype.SteamEngine, Prototype.Pipe),
        (Prototype.AssemblingMachine1, Prototype.BurnerInserter),
        (Prototype.Boiler, Prototype.TransportBelt),
        (Prototype.Boiler, Prototype.AssemblingMachine1),
        (Prototype.ElectricMiningDrill, Prototype.StoneFurnace),
    ]

    for ref_proto, placed_proto in entity_pairs:

        if ref_proto != Prototype.OffshorePump:
            starting_position = game.nearest(Resource.IronOre)
        else:
            starting_position = game.nearest(Resource.Water)
        nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
        game.move_to(nearby_position)

        for direction in [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]:

            for spacing in range(3):
                ref_entity = game.place_entity(ref_proto, position=starting_position)
                placed_entity = game.place_entity_next_to(placed_proto, ref_entity.position, direction, spacing)

                expected_position = calculate_expected_position(ref_entity.position, direction, spacing, ref_entity,
                                                                placed_entity)
                assert placed_entity.position.is_close(expected_position, tolerance=1), \
                    f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, " \
                    f"Direction: {direction}, Spacing: {spacing}, " \
                    f"Expected: {expected_position}, Got: {placed_entity.position}"

                # Check direction unless we are dealing with a pipe, which has no direction
                if placed_proto != Prototype.Pipe:
                    assert placed_entity.direction == direction.value, f"Expected direction {direction}, got {placed_entity.direction}"

                game.reset()
                game.move_to(nearby_position)


def test_place_pipe_next_to_offshore_pump(game):
    ref_proto = Prototype.OffshorePump
    placed_proto = Prototype.Pipe

    starting_position = game.nearest(Resource.Water)
    nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
    game.move_to(nearby_position)

    for direction in [Direction.RIGHT, Direction.DOWN, Direction.UP]:

        for spacing in range(3):
            ref_entity = game.place_entity(ref_proto, position=starting_position)
            placed_entity = game.place_entity_next_to(placed_proto, ref_entity.position, direction, spacing)

            expected_position = calculate_expected_position(ref_entity.position, direction, spacing, ref_entity,
                                                            placed_entity)
            assert placed_entity.position.is_close(expected_position, tolerance=1), \
                f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, " \
                f"Direction: {direction}, Spacing: {spacing}, " \
                f"Expected: {expected_position}, Got: {placed_entity.position}"

            # Check direction unless we are dealing with a pipe, which has no direction
            if placed_proto != Prototype.Pipe:
                assert placed_entity.direction == direction.value, f"Expected direction {direction}, got {placed_entity.direction}"

            game.reset()
            game.move_to(nearby_position)

def test_place_drill_and_furnace_next_to_iron_ore(game):
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)
    entity = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)
    print(f"Burner Mining Drill position: {entity.position}")
    print(f"Burner Mining Drill dimensions: {entity.tile_dimensions}")

    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=entity.position,
                                        direction=Direction.DOWN)
    print(f"Stone Furnace position: {furnace.position}")

    expected_position = calculate_expected_position(entity.position, Direction.DOWN, 0, entity, furnace)
    print(f"Expected position: {expected_position}")

    assert furnace.position == expected_position, f"Expected {expected_position}, got {furnace.position}"
    game.reset()


def test_place_entity_next_to(game, entity_prototype, surrounding_entity_prototype):
    for spacing in range(0, 3):  # Test with spacings 0, 1, and 2
        entity = game.place_entity(entity_prototype, position=Position(x=0, y=0))
        assert entity
        print(f"\nReference entity: {entity_prototype.value[0]}")
        print(f"Reference entity position: {entity.position}")
        print(f"Reference entity dimensions: {entity.tile_dimensions}")

        directions = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        tolerance = 0.5

        for direction in directions:
            surrounding_entity = game.place_entity_next_to(surrounding_entity_prototype,
                                                           reference_position=entity.position,
                                                           direction=direction,
                                                           spacing=spacing)
            assert surrounding_entity, f"Failed to place entity in direction {direction} with spacing {spacing}"
            print(f"\nDirection: {direction}, Spacing: {spacing}")
            print(f"Placed entity: {surrounding_entity_prototype.value[0]}")
            print(f"Placed entity position: {surrounding_entity.position}")
            print(f"Placed entity dimensions: {surrounding_entity.tile_dimensions}")

            expected_position = calculate_expected_position(entity.position, direction, spacing,
                                                            entity, surrounding_entity)
            print(f"Expected position: {expected_position}")
            x_diff = surrounding_entity.position.x - expected_position.x
            y_diff = surrounding_entity.position.y - expected_position.y
            print(f"Difference: x={x_diff}, y={y_diff}")

            try:
                assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, \
                    f"Entity not in expected position for direction {direction} with spacing {spacing}. " \
                    f"Expected {expected_position}, got {surrounding_entity.position}. " \
                    f"Difference: x={x_diff}, y={y_diff}"
            except AssertionError as e:
                print(f"Assertion failed: {str(e)}")
                print(f"Calculated position details:")
                print(f"  Direction: {direction}")
                print(f"  Spacing: {spacing}")
                raise

        game.reset()

    # Specific test for boiler and transport belt
    boiler = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    print(f"\nBoiler position: {boiler.position}")
    print(f"Boiler dimensions: {boiler.tile_dimensions}")

    belt = game.place_entity_next_to(Prototype.TransportBelt, reference_position=boiler.position,
                                     direction=Direction.RIGHT, spacing=0)
    print(f"Transport belt position: {belt.position}")
    print(f"Transport belt dimensions: {belt.tile_dimensions}")

    expected_belt_position = calculate_expected_position(boiler.position, Direction.RIGHT, 0, boiler, belt)
    print(f"Expected belt position: {expected_belt_position}")
    x_diff = belt.position.x - expected_belt_position.x
    y_diff = belt.position.y - expected_belt_position.y
    print(f"Difference: x={x_diff}, y={y_diff}")

    assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, \
        f"Transport belt not in expected position. Expected {expected_belt_position}, got {belt.position}. " \
        f"Difference: x={x_diff}, y={y_diff}"
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_move_to.py`:

```````py
from time import sleep

import pytest

from factorio_entities import Position
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance


def test_move_to(game):
    """
    Move to the nearest coal patch
    Move to the nearest iron patch
    :param game:
    :return:
    """
    size = 5

    # north
    game.move_to(Position(x=0, y=-size*3), leading=Prototype.TransportBelt)
    # northeast
    game.move_to(Position(x=size, y=-size*2), leading=Prototype.TransportBelt)
    # east
    game.move_to(Position(x=size*2, y=-size*2), leading=Prototype.TransportBelt)
    # southeast
    game.move_to(Position(x=size, y=-size), leading=Prototype.TransportBelt)

    game.move_to(Position(x=size*2, y=0), leading=Prototype.TransportBelt)

    entities = game.inspect_entities(Position(x=size, y=size), radius=20)

    print(entities)
    # # north
    # game.move_to(Position(x=0, y=-size), laying=Prototype.TransportBelt)
    # # northeast
    # game.move_to(Position(x=size, y=-size*2), laying=Prototype.TransportBelt)
    # # east
    # game.move_to(Position(x=size*2, y=-size*2), laying=Prototype.TransportBelt)
    # # southeast
    # game.move_to(Position(x=size*3, y=-size), laying=Prototype.TransportBelt)
    # # south
    # game.move_to(Position(x=size*3, y=0), laying=Prototype.TransportBelt)
    # # southwest
    # game.move_to(Position(x=size*2, y=size), laying=Prototype.TransportBelt)
    # # west
    # game.move_to(Position(x=size, y=size), laying=Prototype.TransportBelt)
    # # northwest
    # game.move_to(Position(x=0, y=0), laying=Prototype.TransportBelt)


    # resources = [Resource.Coal, Resource.IronOre, Resource.CopperOre, Resource.Stone]
    #
    # for i in range(10):
    #     for resource in resources:
    #         game.move_to(game.nearest(resource), laying=Prototype.TransportBelt)





```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_nearest.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_types import Resource

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_nearest_resource(game):
    """
    Test distance to the nearest coal resource.
    :param game:
    :return:
    """
    coal: Position = game.nearest(Resource.Coal)
    assert coal.y == -4.5
    assert coal.x == -7.5

def test_move_to_nearest(game):
    """
    Test that when the player moves to the nearest water resource, the nearest water resource remains the same.
    :param game:
    :return:
    """
    water: Position = game.nearest(Resource.Water)
    game.move_to(water)
    assert water == game.nearest(Resource.Water)

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/actions/test_inspect_inventory.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_inspect_inventory(game):
    assert game.inspect_inventory().get(Prototype.Coal, 0) == 50
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    chest_inventory = game.inspect_inventory(entity=chest)
    chest_coal_count = chest_inventory[Prototype.Coal]
    assert chest_coal_count == 5

def test_print_inventory(game):
    inventory = game.inspect_inventory()
    game.print(inventory)
    assert True
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_connect.py`:

```````py
from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10))

    try:
        connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        assert False
    except Exception as e:
        print(e)
        assert True
    game.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),

    for offset in offsets:
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset)

        try:
            connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection)

        game.reset()  # Reset the game state after each iteration

def test_place_and_connect_entities_in_grid(game):
    """
    Place a grid of furnaces and connect them with burner inserters.
    :param game:
    :return:
    """
    furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]


    grid_size = 3
    furnaces = [[None for _ in range(grid_size)] for _ in range(grid_size)]

    for i in range(grid_size):
        for j in range(grid_size):
            furnaces[i][j] = game.place_entity(Prototype.StoneFurnace, position=Position(x=1+(i*3), y=1+(j*3)))

    for i in range(grid_size):
        for j in range(grid_size - 1):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i][j+1], connection_type=Prototype.BurnerInserter)
            except Exception as e:
                print(e)
                assert False

    for i in range(grid_size - 1):
        for j in range(grid_size):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i+1][j], connection_type=Prototype.BurnerInserter)
            except Exception as e:
                print(e)
                assert False

    current_furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

    spent_furnaces = (furnaces_in_inventory - current_furnaces_in_inventory)
    spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

    assert spent_furnaces == grid_size * grid_size
    assert spent_inserters == 4 * grid_size * (grid_size - 1)

    game.reset()

def test_basic_connection_between_furnace_and_miner(game):
    """
    Place a furnace with a burner inserter pointing towards it.
    Find the nearest coal and place a burner mining drill on it.
    Connect the burner mining drill to the inserter using a transport belt.
    :param game:
    :return:
    """

    coal: Position = game.nearest(Resource.Coal)
    furnace_position = Position(x=coal.x, y=coal.y - 10)
    game.move_to(furnace_position)
    furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_position)
    inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                         reference_position=furnace.position,
                                         direction=game.RIGHT,
                                         spacing=0.5)
    game.move_to(coal)
    miner = game.place_entity(Prototype.BurnerMiningDrill, position=coal)

    belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    try:
        connection = game.connect_entities(miner, inserter, connection_type=Prototype.TransportBelt)
    except Exception as e:
        pass

    current_belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    spent_belts = (belts_in_inventory - current_belts_in_inventory)
    assert spent_belts == len(connection)


def test_burner_inserter_grid_with_coal_movement(game):
    """
    Create a grid of burner inserters, each passing left and up from the bottom right point.
    Place some coal at the bottom right point and check whether it moves to the top left
    within a reasonable amount of time.
    :param game:
    :return:
    """

    # Define the grid size
    grid_size = 6

    # Check inventory for inserters
    inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

    # Array to keep track of burner inserters in the grid
    inserters = [[None for _ in range(grid_size)] for _ in range(grid_size)]

    for i in range(0, grid_size, 2):
        for j in range(0, grid_size, 2):
            # Place burner inserters with orientation to pass items to the left and up
            # Assuming the orientation is controlled by a parameter in place_entity
            try:
                inserters[i][j] = game.place_entity(Prototype.BurnerInserter,
                                                    position=(i, j),
                                                    direction=game.RIGHT)
            except Exception as e:
                pass

    for i in range(1, grid_size, 2):
        for j in range(1, grid_size, 2):
            # Place burner inserters with orientation to pass items to the left and up
            # Assuming the orientation is controlled by a parameter in place_entity
            try:
                inserters[i][j] = game.place_entity(Prototype.BurnerInserter,
                                                    position=Position(x=i, y=j),
                                                    direction=game.UP)
            except Exception as e:
                pass

    try:
        # Place coal at the bottom right inserter
        source = game.place_entity(Prototype.IronChest, position=inserters[-1][-1].pickup_position)
        target = game.place_entity(Prototype.IronChest, position=inserters[0][0].drop_position)
        game.insert_item(Prototype.Coal, source, 50)
        # Wait for some time to allow coal to move, assuming there's a method to wait in game
        sleep(60)  # Wait for 200 ticks or adjust as needed based on game speed

        # Now check if the coal has reached the top left point (i.e., the first inserter in the grid)
        # Assuming there's a method to inspect the contents of an inserter
        target_inventory = game.inspect_inventory(entity=target)

        current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

        spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

        # Assert the spent inserters and if the coal reached its destination
        assert spent_inserters == 18

        coal_in_final_chest = target_inventory[Prototype.Coal]

        assert coal_in_final_chest > 20
    except Exception as e:
        print(e)
        assert False

    game.reset()  # Reset the game state after each iteration

def test_failure_to_connect_adjacent_furnaces(game):
    """
    Place adjacent furnaces and fail to connect them with transport belts.
    :param game:
    :return:
    """
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.UP)
    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.LEFT, spacing=1)
    game.connect_entities(source=drill, target=furnace, connection_type=Prototype.TransportBelt)

    print()
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_objectives.py`:

```````py
from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position, ResourcePatch, Recipe, BurnerMiningDrill
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'stone-furnace': 1}
    #instance.rcon_client.send_command('game.reset_game_state()')
    #instance.rcon_client.send_command('game.reload_script()')
    instance.reset()
    yield instance


def test_collect_iron_ore(game):
    """
    Collect 10 iron ore
    :param game:
    :return:
    """
    iron_ore = game.nearest(Resource.IronOre)
    # move to the iron ore
    game.move_to(iron_ore)
    game.harvest_resource(iron_ore)

    assert game.inspect_inventory()[Prototype.IronOre] == 10
    game.reset()


def test_place_ore_in_furnace(game):
    """
    Collect 10 iron ore and place it in a furnace
    :param game:
    :return:
    """
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # move to the iron ore
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the coal
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    game.move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the furnace
    game.move_to(furnace.position)
    game.insert_item(Prototype.IronOre, furnace, quantity=10)
    game.insert_item(Prototype.Coal, furnace, quantity=10)

    game.reset()


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10))

    try:
        connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        assert False
    except Exception as e:
        print(e)
        assert True
    game.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),

    for offset in offsets:
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset)

        try:
            connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection)

        game.reset()  # Reset the game state after each iteration


def test_build_iron_gear_factory(game):
    """
    Build a factory that produces iron gears from iron plates.
    :param game:
    :return:
    """
    # move to the iron ore
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 80 iron ore
    while game.inspect_inventory()[Prototype.IronOre] < 80:
        game.harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the stone patch
    stone_patch = game.get_resource_patch(Resource.Stone, game.nearest(Resource.Stone))

    # harvest 10 stone
    game.move_to(stone_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(stone_patch.bounding_box.left_top, quantity=10)

    # move to the coal patch
    coal_patch: ResourcePatch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    game.move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 30 coal
    while game.inspect_inventory()[Prototype.Coal] < 30:
        game.harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the copper patch
    copper_patch: ResourcePatch = game.get_resource_patch(Resource.CopperOre, game.nearest(Resource.CopperOre))
    game.move_to(copper_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 10 copper ore
    while game.inspect_inventory()[Prototype.CopperOre] < 30:
        game.harvest_resource(copper_patch.bounding_box.left_top, quantity=10)

    # move to the origin
    game.move_to(Position(x=0, y=0))

    # place a stone furnace
    stone_furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # insert 20 coal into the stone furnace
    game.insert_item(Prototype.Coal, stone_furnace, quantity=20)

    # insert 80 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=50)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 50:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=50)

    # insert 30 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=30)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 30:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=30)

    # insert 20 copper ore into the stone furnace
    game.insert_item(Prototype.CopperOre, stone_furnace, quantity=20)

    # check if the stone furnace has produced copper plates
    while game.inspect_inventory(stone_furnace)[Prototype.CopperPlate] < 20:
        sleep(5)

    # extract the copper plates from the stone furnace
    game.extract_item(Prototype.CopperPlate, stone_furnace, quantity=20)

    # pick up the stone furnace
    game.pickup_entity(stone_furnace)

    # get recipe for burner mining drill
    recipe: Recipe = game.get_prototype_recipe(Prototype.BurnerMiningDrill)

    # craft any ingredient that is missing
    for ingredient in recipe.ingredients:
        if game.inspect_inventory()[ingredient.name] < ingredient.count:
            game.craft_item(ingredient.name, quantity=ingredient.count)

    # craft a burner mining drill
    game.craft_item(Prototype.BurnerMiningDrill)

    # move to the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # place a burner mining drill
    burner_mining_drill: BurnerMiningDrill = game.place_entity(Prototype.BurnerMiningDrill,
                                                               position=iron_ore_patch.bounding_box.left_top)

    # fuel the burner mining drill
    game.insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

    # place the stone furnace
    stone_furnace = game.place_entity_next_to(Prototype.StoneFurnace,
                                              reference_position=burner_mining_drill.drop_position,
                                              direction=Direction.UP,
                                              spacing=0)

    # place a burner inserter
    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=stone_furnace.position,
                                                direction=Direction.UP,
                                                spacing=1)

    def ensure_ingredients(game, recipe, quantity=1):
        for ingredient in recipe.ingredients:
            required = ingredient.count * quantity
            available = game.inspect_inventory()[ingredient.name]
            if available < required:
                craft_recursive(game, ingredient.name, required - available)

    def craft_recursive(game, item_name, quantity):
        recipe = game.get_prototype_recipe(item_name)
        ensure_ingredients(game, recipe, quantity)
        game.craft_item(item_name, quantity=quantity)

    recipe = game.get_prototype_recipe(Prototype.AssemblingMachine1)
    ensure_ingredients(game, recipe)

    # craft an assembly machine
    game.craft_item(Prototype.AssemblingMachine1)

    # place the assembly machine
    assembly_machine = game.place_entity_next_to(Prototype.AssemblingMachine1,
                                                 reference_position=burner_inserter.drop_position,
                                                 direction=Direction.UP,
                                                 spacing=0)
    # set the recipe for the assembly machine to produce iron gears
    game.set_entity_recipe(assembly_machine, Prototype.IronGearWheel)

    # craft an offshore pump
    recipe = game.get_prototype_recipe(Prototype.OffshorePump)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.OffshorePump)

    # place the offshore pump at nearest water source
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water))

    # craft a boiler
    recipe = game.get_prototype_recipe(Prototype.Boiler)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.Boiler)

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=Direction.RIGHT,
                                       spacing=2)

    # craft a steam engine
    recipe = game.get_prototype_recipe(Prototype.SteamEngine)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.SteamEngine)

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=Direction.RIGHT,
                                             spacing=2)

    # connect the steam engine and assembly machine with power poles

    # harvest nearby trees for wood
    tree_patch = game.get_resource_patch(Resource.Wood, game.nearest(Resource.Wood))
    game.move_to(tree_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(tree_patch.bounding_box.left_top, quantity=10)

    # craft 5 small electric poles
    recipe = game.get_prototype_recipe(Prototype.SmallElectricPole)
    ensure_ingredients(game, recipe, quantity=5)
    game.craft_item(Prototype.SmallElectricPole, quantity=5)

    # place connect the steam engine and assembly machine with power poles
    game.connect_entities(steam_engine, assembly_machine, connection_type=Prototype.SmallElectricPole)

    #game.place_entity(Prototype.OffshorePump, position=water_patch.bounding_box.left_top)


```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_electricity_unit.py`:

```````py
from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position, ResourcePatch, Recipe, BurnerMiningDrill
from factorio_instance import Direction, FactorioInstance
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'stone-furnace': 1, 'boiler': 1, 'steam-engine': 1, 'offshore-pump': 1}
    #instance.rcon_client.send_command('game.reset_game_state()')
    #instance.rcon_client.send_command('game.reload_script()')
    instance.reset()
    yield instance

def test_create_offshore_pump_to_steam_engine(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    # move to the nearest water source
    water_location = game.nearest(Resource.Water)
    game.move_to(water_location)

    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=water_location)
    # Get offshore pump direction
    direction = Direction(offshore_pump.direction)

    # Get orthogonal direction
    opposite_direction = Direction.opposite(direction)

    # pump connection point
    pump_connection_point = offshore_pump.connection_points[0]

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=opposite_direction,
                                       spacing=2)

    # rotate the boiler to face the offshore pump
    boiler = game.rotate_entity(boiler, Direction.next_clockwise(direction))

    # boiler connection point
    boiler_connection_point = boiler.connection_points[0]

    # connect the boiler and offshore pump with a pipe
    game.connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)

    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity_next_to(Prototype.SteamEngine,
                                                     reference_position=boiler.position,
                                                     direction=Direction.RIGHT,
                                                     spacing=2)

    # connect the boiler and steam engine with a pipe
    game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)



def test_build_iron_gear_factory(game):
    """
    Build a factory that produces iron gears from iron plates.
    :param game:
    :return:
    """
    # move to the iron ore
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 80 iron ore
    while game.inspect_inventory()[Prototype.IronOre] < 80:
        game.harvest_resource(iron_ore_patch.bounding_box.left_top, quantity=10)

    # move to the stone patch
    stone_patch = game.get_resource_patch(Resource.Stone, game.nearest(Resource.Stone))

    # harvest 10 stone
    game.move_to(stone_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(stone_patch.bounding_box.left_top, quantity=10)

    # move to the coal patch
    coal_patch: ResourcePatch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))
    game.move_to(coal_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 30 coal
    while game.inspect_inventory()[Prototype.Coal] < 30:
        game.harvest_resource(coal_patch.bounding_box.left_top, quantity=10)

    # move to the copper patch
    copper_patch: ResourcePatch = game.get_resource_patch(Resource.CopperOre, game.nearest(Resource.CopperOre))
    game.move_to(copper_patch.bounding_box.left_top + Position(x=1, y=1))

    # harvest 10 copper ore
    while game.inspect_inventory()[Prototype.CopperOre] < 30:
        game.harvest_resource(copper_patch.bounding_box.left_top, quantity=10)

    # move to the origin
    game.move_to(Position(x=0, y=0))

    # place a stone furnace
    stone_furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

    # insert 20 coal into the stone furnace
    game.insert_item(Prototype.Coal, stone_furnace, quantity=20)

    # insert 80 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=50)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 50:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=50)

    # insert 80 iron ore into the stone furnace
    game.insert_item(Prototype.IronOre, stone_furnace, quantity=30)

    # check if the stone furnace has produced iron plates
    while game.inspect_inventory(stone_furnace)[Prototype.IronPlate] < 30:
        sleep(1)

    # extract the iron plates from the stone furnace
    game.extract_item(Prototype.IronPlate, stone_furnace, quantity=30)

    # insert 20 copper ore into the stone furnace
    game.insert_item(Prototype.CopperOre, stone_furnace, quantity=20)

    # check if the stone furnace has produced copper plates
    while game.inspect_inventory(stone_furnace)[Prototype.CopperPlate] < 20:
        sleep(5)

    # extract the copper plates from the stone furnace
    game.extract_item(Prototype.CopperPlate, stone_furnace, quantity=20)

    # pick up the stone furnace
    game.pickup_entity(stone_furnace)

    # get recipe for burner mining drill
    recipe: Recipe = game.get_prototype_recipe(Prototype.BurnerMiningDrill)

    # craft any ingredient that is missing
    for ingredient in recipe.ingredients:
        if game.inspect_inventory()[ingredient.name] < ingredient.count:
            game.craft_item(ingredient.name, quantity=ingredient.count)

    # craft a burner mining drill
    game.craft_item(Prototype.BurnerMiningDrill)

    # move to the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top + Position(x=1, y=1))

    # place a burner mining drill
    burner_mining_drill: BurnerMiningDrill = game.place_entity(Prototype.BurnerMiningDrill,
                                                               position=iron_ore_patch.bounding_box.left_top)

    # fuel the burner mining drill
    game.insert_item(Prototype.Coal, burner_mining_drill, quantity=5)

    # place the stone furnace
    stone_furnace = game.place_entity_next_to(Prototype.StoneFurnace,
                                              reference_position=burner_mining_drill.drop_position,
                                              direction=Direction.UP,
                                              spacing=0)

    # place a burner inserter
    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=stone_furnace.position,
                                                direction=Direction.UP,
                                                spacing=1)

    def ensure_ingredients(game, recipe, quantity=1):
        for ingredient in recipe.ingredients:
            required = ingredient.count * quantity
            available = game.inspect_inventory()[ingredient.name]
            if available < required:
                craft_recursive(game, ingredient.name, required - available)

    def craft_recursive(game, item_name, quantity):
        recipe = game.get_prototype_recipe(item_name)
        ensure_ingredients(game, recipe, quantity)
        game.craft_item(item_name, quantity=quantity)

    recipe = game.get_prototype_recipe(Prototype.AssemblingMachine1)
    ensure_ingredients(game, recipe)

    # craft an assembly machine
    game.craft_item(Prototype.AssemblingMachine1)

    # place the assembly machine
    assembly_machine = game.place_entity_next_to(Prototype.AssemblingMachine1,
                                                 reference_position=burner_inserter.drop_position,
                                                 direction=Direction.UP,
                                                 spacing=0)
    # set the recipe for the assembly machine to produce iron gears
    game.set_entity_recipe(assembly_machine, Prototype.IronGearWheel)

    # craft an offshore pump
    recipe = game.get_prototype_recipe(Prototype.OffshorePump)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.OffshorePump)

    # place the offshore pump at nearest water source
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water))

    # craft a boiler
    recipe = game.get_prototype_recipe(Prototype.Boiler)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.Boiler)

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=Direction.RIGHT,
                                       spacing=2)

    # craft a steam engine
    recipe = game.get_prototype_recipe(Prototype.SteamEngine)
    ensure_ingredients(game, recipe)
    game.craft_item(Prototype.SteamEngine)

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=Direction.RIGHT,
                                             spacing=2)

    # connect the steam engine and assembly machine with power poles

    # harvest nearby trees for wood
    tree_patch = game.get_resource_patch(Resource.Wood, game.nearest(Resource.Wood))
    game.move_to(tree_patch.bounding_box.left_top + Position(x=1, y=1))
    game.harvest_resource(tree_patch.bounding_box.left_top, quantity=10)

    # craft 5 small electric poles
    recipe = game.get_prototype_recipe(Prototype.SmallElectricPole)
    ensure_ingredients(game, recipe, quantity=5)
    game.craft_item(Prototype.SmallElectricPole, quantity=5)

    # place connect the steam engine and assembly machine with power poles
    game.connect_entities(steam_engine, assembly_machine, connection_type=Prototype.SmallElectricPole)

    #game.place_entity(Prototype.OffshorePump, position=water_patch.bounding_box.left_top)


```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_place_next_to_and_rotate.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'boiler': 1,
        'transport-belt': 1,
        'stone-furnace': 1,
        'burner-mining-drill': 1,
        'burner-inserter': 2,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'steam-engine': 1,
        'pipe': 1,
        'offshore-pump': 1,
    }
    instance.reset()
    yield instance

def calculate_expected_position(ref_pos, direction, spacing, ref_entity, entity_to_place):
    ref_dimensions = ref_entity.tile_dimensions
    entity_dimensions = entity_to_place.tile_dimensions

    def align_to_grid(pos):
        return Position(x=round(pos.x * 2) / 2, y=round(pos.y * 2) / 2)

    def should_have_y_offset(entity):
        return entity.tile_dimensions.tile_width % 2 == 1

    y_offset = 0.5 if should_have_y_offset(entity_to_place) else 0

    if direction == Direction.RIGHT:
        return align_to_grid(Position(x=ref_pos.x + ref_dimensions.tile_width / 2 + entity_dimensions.tile_width / 2 + spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.DOWN:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y + ref_dimensions.tile_height / 2 + entity_dimensions.tile_height / 2 + spacing + y_offset))
    elif direction == Direction.LEFT:
        return align_to_grid(Position(x=ref_pos.x - ref_dimensions.tile_width / 2 - entity_dimensions.tile_width / 2 - spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.UP:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y - ref_dimensions.tile_height / 2 - entity_dimensions.tile_height / 2 - spacing + y_offset))

def test_place_boiler_next_to_offshore_pump_rotate_and_connect(game):
    # move to the nearest water source
    water_location = game.nearest(Resource.Water)
    game.move_to(water_location)

    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=water_location)
    # Get offshore pump direction
    direction = Direction(offshore_pump.direction)

    # Get orthogonal direction
    opposite_direction = Direction.opposite(direction)

    # pump connection point
    pump_connection_point = offshore_pump.connection_points[0]

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=opposite_direction,
                                       spacing=2)

    # rotate the boiler to face the offshore pump
    boiler = game.rotate_entity(boiler, Direction.next_clockwise(direction))
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_auto_refilling_coal.py`:

```````py
import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'stone-furnace': 1,
                                  'iron-chest': 3,
                                  'burner-inserter': 6,
                                  'coal': 50,
                                  'transport-belt': 50,
                                  'burner-mining-drill': 3}
    instance.reset()
    yield instance

def test_build_auto_refilling_coal_system(game):
    num_drills = 3

    # Start at the origin
    game.move_to(Position(x=0, y=0))

    # Find the nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Move to the center of the coal patch
    game.move_to(coal_patch.bounding_box.left_top)

    # Place the first drill
    drill = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Place a chest next to the first drill to collect coal
    chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, drill.drop_position)

    # Connect the first drill to the chest with an inserter
    inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)
    first_inserter = inserter

    # Place an inserter south of the drill to insert coal into the drill
    drill_bottom_y = drill.position.y + drill.dimensions.height
    drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=drill.position.x, y=drill_bottom_y))
    drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)
    first_drill_inserter = drill_inserter

    # Start the transport belt from the chest
    game.move_to(inserter.drop_position)

    drills = []

    # Place additional drills and connect them to the belt
    for i in range(1, num_drills):
        # Place the next drill
        next_drill = game.place_entity_next_to(Prototype.BurnerMiningDrill, drill.position, Direction.RIGHT, spacing=2)
        next_drill = game.rotate_entity(next_drill, Direction.UP)
        drills.append(next_drill)

        try:
            # Place a chest next to the next drill to collect coal
            chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, next_drill.drop_position)
        except Exception as e:
            print(f"Could not place chest next to drill: {e}")

        # Place an inserter to connect the chest to the transport belt
        next_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)

        # Place an insert underneath the drill to insert coal into the drill
        drill_bottom_y = next_drill.position.y + next_drill.dimensions.height
        drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=next_drill.position.x, y=drill_bottom_y))
        drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)

        # Extend the transport belt to the next drill
        game.connect_entities(inserter.drop_position, next_inserter.drop_position, Prototype.TransportBelt)

        # Update the drill reference for the next iteration
        drill = next_drill
        inserter = next_inserter
        next_drill_inserter = drill_inserter

    # Connect the drop position of the final drill block to the inserter that is loading it with coal
    game.connect_entities(next_inserter.drop_position, next_drill_inserter.pickup_position, Prototype.TransportBelt)

    # Connect that inserter to the inserter that is loading the first drill with coal
    game.connect_entities(next_drill_inserter.pickup_position, first_drill_inserter.pickup_position, Prototype.TransportBelt)

    # Connect the first drill inserter to the drop point of the first inserter
    game.connect_entities(first_drill_inserter.pickup_position, first_inserter.drop_position, Prototype.TransportBelt)

    # Initialize the system by adding some coal to each drill and inserter
    for drill in drills:
        game.insert_item(Prototype.Coal, drill, 5)

    print(f"Auto-refilling coal mining system with {num_drills} drills has been built!")

```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_small_iron_factory.py`:

```````py
import pytest
from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 5,
        'iron-chest': 2,
        'burner-inserter': 12,
        'coal': 100,
        'transport-belt': 100,
        'burner-mining-drill': 2
    }
    instance.reset()
    yield instance


def test_build_iron_plate_factory(game):
    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.left_top)

    # Place an iron check above the drill and insert coal
    chest = game.place_entity_next_to(Prototype.IronChest, miner.position, Direction.UP, spacing=miner.dimensions.height)
    game.insert_item(Prototype.Coal, chest, 50)

    # Place an inserter to insert coal into the drill
    coal_drill_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.DOWN, spacing=0)

    # Place an inserter to insert coal into the coal belt
    coal_belt_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=1)
    game.rotate_entity(coal_belt_inserter, Direction.RIGHT)

    # Place a transport belt form the coal belt inserter to the end of the
    coal_belt_start = game.place_entity_next_to(Prototype.TransportBelt, coal_belt_inserter.drop_position, Direction.RIGHT, spacing=0)

    # Place a transport belt from the miner's output
    iron_belt_start = game.place_entity_next_to(Prototype.TransportBelt, miner.drop_position, Direction.DOWN, spacing=0)

    # Place 5 stone furnaces along the belt
    furnace_line_start = game.place_entity_next_to(Prototype.StoneFurnace, miner.drop_position, Direction.DOWN,
                                                   spacing=3)
    current_furnace = furnace_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT,
                                                    spacing=2)

    # Connect furnaces with transport belt
    above_current_furnace = Position(x=current_furnace.position.x, y=current_furnace.position.y - current_furnace.dimensions.height - 1)
    game.connect_entities(iron_belt_start.position, above_current_furnace, Prototype.TransportBelt)

    next_coal_belt_position = coal_belt_start.position

    # Place 4 more drills
    miners = [miner]
    for i in range(3):
        miner = game.place_entity_next_to(Prototype.BurnerMiningDrill, miner.position, Direction.RIGHT,
                                                     spacing=2)
        miner = game.rotate_entity(miner, Direction.DOWN)
        miners.append(miner)

        # Connect furnaces with coal belt
        above_current_drill = Position(x=miner.position.x, y=miner.position.y - miner.dimensions.height - 1)
        game.connect_entities(next_coal_belt_position, above_current_drill, Prototype.TransportBelt)

        next_coal_belt_position = above_current_drill

    # Place inserters for each furnace
    for i in range(4):
        furnace_pos = Position(x=miners[i].drop_position.x, y=furnace_line_start.position.y + 2)
        game.move_to(furnace_pos)
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - (current_furnace.dimensions.height + 2)))
        game.place_entity(Prototype.BurnerInserter, Direction.DOWN, Position(x=furnace_pos.x, y=furnace_pos.y - 1))

    # Place output belt for iron plates
    output_belt_start = game.place_entity_next_to(furnace_line_start.position, Direction.UP, spacing=2)
    game.connect_entities(output_belt_start.position,
                          Position(x=current_furnace.position.x, y=output_belt_start.position.y),
                          Prototype.TransportBelt)

    # Place a chest at the end of the output belt
    output_chest = game.place_entity_next_to(Prototype.IronChest,
                                             Position(x=current_furnace.position.x, y=output_belt_start.position.y),
                                             Direction.UP, spacing=1)

    # Place an inserter to move plates from belt to chest
    game.place_entity(Prototype.BurnerInserter, Direction.DOWN,
                      Position(x=output_chest.position.x, y=output_chest.position.y - 1))

    # Find nearest coal patch
    coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

    # Place a burner mining drill on the coal patch
    coal_miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

    # Connect coal to furnaces with transport belt
    game.connect_entities(coal_miner.drop_position, furnace_line_start.position, Prototype.TransportBelt)

    # Add some initial coal to get the system started
    game.insert_item(Prototype.Coal, miner, 5)
    game.insert_item(Prototype.Coal, coal_miner, 5)
    for i in range(5):
        furnace_pos = Position(x=furnace_line_start.position.x + i * 2, y=furnace_line_start.position.y)
        inserter_up = game.get_entity(Prototype.BurnerInserter, Position(x=furnace_pos.x, y=furnace_pos.y + 1))
        inserter_down = game.get_entity(Prototype.BurnerInserter, Position(x=furnace_pos.x, y=furnace_pos.y - 1))
        game.insert_item(Prototype.Coal, inserter_up, 1)
        game.insert_item(Prototype.Coal, inserter_down, 1)

    print("Simple iron plate factory has been built!")
```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_blueprints.py`:

```````py
from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_factorio_setup(game):
    """
    Create a test setup in Factorio resembling the provided blueprint.
    :param game:
    :return:
    """

    # Set starting position for placing entities
    coal_position = game.nearest(Resource.Coal)
    game.move_to(coal_position)
    coal_patch = game.get_resource_patch(Resource.Coal, coal_position)
    coal_bounding_box = coal_patch.bounding_box

    coal_center = Position(x=(coal_bounding_box.left_top.x + coal_bounding_box.right_bottom.x) / 2,
                            y=(coal_bounding_box.left_top.y + coal_bounding_box.right_bottom.y) / 2)

    game.move_to(coal_center)

    burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=coal_center, direction=Direction.UP)

    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                spacing=1,
                                                direction=Direction.DOWN)
    mining_drills = [burner_mining_drill]
    inserters = [burner_inserter]

    for i in range(0, 2):
        mining_drills.append(game.place_entity(Prototype.BurnerMiningDrill,
                                                position=Position(x=coal_center.x + mining_drills[-1].tile_dimensions.tile_width * (i + 1),
                                                                  y=coal_center.y),
                                                direction=Direction.UP))
        inserters.append(game.place_entity_next_to(Prototype.BurnerInserter,
                                                    reference_position=mining_drills[-1].position,
                                                    spacing=1,
                                                    direction=Direction.DOWN))

    for last_inserter, inserter in zip(inserters[:-1], inserters[1:]):
        # Connect the pick up position of the new burner inserter to the pick up position of the previous inserter with a belt
        game.connect_entities(last_inserter.pickup_position, inserter.pickup_position, Prototype.TransportBelt)

    game.connect_entities(mining_drills[0].drop_position, inserters[0].pickup_position, Prototype.TransportBelt)

    # Connect the pick up position of the burner inserter to the drop off position of the mining drill with a belt
    game.connect_entities(first_burner_mining_drill.drop_position, first_burner_inserter.pickup_position,
                          Prototype.TransportBelt)







```````

`/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/tests/functional/test_factory_unit.py`:

```````py
import time

import pytest

from factorio_entities import BurnerMiningDrill
from factorio_instance import FactorioInstance
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance


def test_steam_engines(game: FactorioInstance):
    try:
        game.craft_item(Prototype.OffshorePump)
        game.move_to(game.nearest(Resource.Water))
        offshore_pump = game.place_entity(Prototype.OffshorePump,
                                          position=game.nearest(Resource.Water))
        boiler = game.place_entity_next_to(Prototype.Boiler,
                                           reference_position=offshore_pump.position,
                                           direction_from=game.DOWN,
                                           spacing=5)
        water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

        steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                                 reference_position=boiler.position,
                                                 direction_from=game.DOWN,
                                                 spacing=5)
        steam_pipes = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

        coal_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                  reference_position=boiler.position,
                                                  direction_from=game.UP,
                                                  spacing=1)
        game.move_to(game.nearest(Resource.Coal))

        burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal))
        burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                    reference_position=burner_mining_drill.position,
                                                    direction_from=game.DOWN,
                                                    spacing=1)
        assert burner_inserter

        belts = game.connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)

        assert belts

        coal_to_boiler_belts = game.connect_entities(belts[-1], coal_inserter, connection_type=Prototype.TransportBelt)

        assert coal_to_boiler_belts

        assembler = game.place_entity_next_to(Prototype.AssemblingMachine1,
                                              reference_position=steam_engine.position,
                                              direction_from=game.LEFT,
                                              spacing=5)

        steam_engine_to_assembler_poles = game.connect_entities(assembler, steam_engine, connection_type=Prototype.SmallElectricPole)

        assert steam_engine_to_assembler_poles

    except Exception as e:
        print(e)


def test_iron_smelting(game: FactorioInstance):
    """
    Create an auto driller for coal.
    Create a miner for iron ore and a nearby furnace. Connect the miner to the furnace.

    :return:
    """
    game.move_to(game.nearest(Resource.Coal))

    burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal))
    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                direction_from=game.DOWN,
                                                spacing=1)
    assert burner_inserter

    belts = game.connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)
    assert belts

    burner_mining_drill: BurnerMiningDrill = game.insert_item(Prototype.Coal, burner_mining_drill, 5)

    assert burner_mining_drill.remaining_fuel == 5
    nearest_iron_ore = game.nearest(Resource.IronOre)

    game.move_to(nearest_iron_ore)
    try:
        iron_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=nearest_iron_ore)
        stone_furnace = game.place_entity(Prototype.StoneFurnace, position=iron_mining_drill.drop_position)

        coal_to_iron_drill_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                                reference_position=iron_mining_drill.position,
                                                                direction_from=game.DOWN,
                                                                spacing=1)
        coal_to_smelter_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                             reference_position=stone_furnace.position,
                                                             direction_from=game.RIGHT,
                                                             spacing=1)

        coal_to_drill_belt = game.connect_entities(belts[-1], coal_to_iron_drill_inserter.pickup_position,
                                                   connection_type=Prototype.TransportBelt)
        coal_to_smelter_belt = game.connect_entities(coal_to_drill_belt[-1], coal_to_smelter_inserter.pickup_position,
                                                     connection_type=Prototype.TransportBelt)
    except Exception as e:
        print(e)
        assert False


def test_auto_driller(game: FactorioInstance):
    game.move_to(game.nearest(Resource.Coal))
    burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal))
    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                direction_from=game.DOWN,
                                                spacing=1)
    assert burner_inserter

    belts = game.connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)

    assert belts

    game.insert_item(Prototype.Coal, burner_mining_drill, 5)

    start_score = game.score()
    time.sleep(5)
    end_score = game.score()

    assert end_score > start_score
```

Implement a test thats builds an auto-fueling iron smelting factory, using coal, iron, inserters and transporters to create a neverending supply of iron-plates that go into a steel chest.

