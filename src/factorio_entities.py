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