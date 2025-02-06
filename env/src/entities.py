import math
from typing import Tuple, Any, Union, Dict, Set
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, PrivateAttr, root_validator


# This should really live in `types`, but it's here to prevent a circular import
class EntityStatus(Enum):
    WORKING = "working"
    NORMAL = "normal"
    NO_POWER = "no_power"
    LOW_POWER = "low_power"
    NO_FUEL = "no_fuel"
    EMPTY = "empty"
    #DISABLED_BY_CONTROL_BEHAVIOR = "disabled_by_control_behavior"
    #OPENED_BY_CIRCUIT_NETWORK = "opened_by_circuit_network"
    #CLOSED_BY_CIRCUIT_NETWORK = "closed_by_circuit_network"
    #DISABLED_BY_SCRIPT = "disabled_by_script"
    #MARKED_FOR_DECONSTRUCTION = "marked_for_deconstruction"
    NOT_PLUGGED_IN_ELECTRIC_NETWORK = "not_plugged_in_electric_network"
    #NETWORKS_CONNECTED = "networks_connected"
    #NETWORKS_DISCONNECTED = "networks_disconnected"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULLY_CHARGED = "fully_charged"
    #OUT_OF_LOGISTIC_NETWORK = "out_of_logistic_network"
    NO_RECIPE = "no_recipe"
    NO_INGREDIENTS = "no_ingredients"
    NOT_CONNECTED = "not_connected"
    NO_INPUT_FLUID = "no_input_fluid"
    NO_RESEARCH_IN_PROGRESS = "no_research_in_progress"
    NO_MINABLE_RESOURCES = "no_minable_resources"
    LOW_INPUT_FLUID = "low_input_fluid"
    FLUID_INGREDIENT_SHORTAGE = "fluid_ingredient_shortage"
    FULL_OUTPUT = "full_output"
    FULL_BURNT_RESULT_OUTPUT = "full_burnt_result_output"
    ITEM_INGREDIENT_SHORTAGE = "item_ingredient_shortage"
    MISSING_REQUIRED_FLUID = "missing_required_fluid"
    MISSING_SCIENCE_PACKS = "missing_science_packs"
    WAITING_FOR_SOURCE_ITEMS = "waiting_for_source_items"
    WAITING_FOR_SPACE_IN_DESTINATION = "waiting_for_space_in_destination"
    #PREPARING_ROCKET_FOR_LAUNCH = "preparing_rocket_for_launch"
    #WAITING_TO_LAUNCH_ROCKET = "waiting_to_launch_rocket"
    #LAUNCHING_ROCKET = "launching_rocket"
    #NO_MODULES_TO_TRANSMIT = "no_modules_to_transmit"
    #RECHARGING_AFTER_POWER_OUTAGE = "recharging_after_power_outage"
    #WAITING_FOR_TARGET_TO_BE_BUILT = "waiting_for_target_to_be_built"
    #WAITING_FOR_TRAIN = "waiting_for_train"
    NO_AMMO = "no_ammo"
    LOW_TEMPERATURE = "low_temperature"
    #DISABLED = "disabled"
    #TURNED_OFF_DURING_DAYTIME = "turned_off_during_daytime"
    NOT_CONNECTED_TO_RAIL = "not_connected_to_rail"
    #CANT_DIVIDE_SEGMENTS = "cant_divide_segments"

    def __repr__(self):
        return f"EntityStatus.{self.name}"

    @classmethod
    def from_string(cls, status_string):
        for status in cls:
            if status.value == status_string:
                return status
        return None

    @classmethod
    def from_int(cls, status_int):
        for index, status in enumerate(cls):
            if index == status_int:
                return status
        return None


class Inventory(BaseModel):
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__()
        self.__dict__.update(data)

    def __getitem__(self, key: 'Prototype', default=None) -> int:
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

    def get(self, key: 'Prototype', default=0) -> int:
        try:
            if hasattr(key, 'value'):
                name, _ = key.value
            else:
                name = key
        except Exception as e:
            pass

        item = self.__getitem__(name)
        return item if item else default

    def __setitem__(self, key: 'Prototype', value: int) -> None:
        self.__dict__[key] = value

    def items(self):
        return self.__dict__.items()

    def __repr__(self) -> str:
        return f"Inventory({str(self.__dict__)})"

    def __str__(self) -> str:
        return str(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()


class Direction(Enum):
    UP = NORTH = 0
    RIGHT = EAST = 2
    DOWN = SOUTH = 4
    LEFT = WEST = 6

    def __repr__(self):
        return f"Direction.{self.name}"

    @classmethod
    def from_string(cls, direction_string):
        for status in cls:
            if status.value == direction_string:
                return status
        return None


class Position(BaseModel):
    x: float
    y: float

    @classmethod
    def _parse_positional_args(cls, v):
        if isinstance(v, tuple) and len(v) == 2:
            return {'x': v[0], 'y': v[1]}
        return v

    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Cannot mix positional and keyword arguments")

        if args:
            if len(args) != 2:
                raise ValueError("Position requires exactly 2 positional arguments")
            kwargs = {'x': args[0], 'y': args[1]}

        super().__init__(**kwargs)

    @root_validator(pre=True)
    def parse_args(cls, values):
        if isinstance(values, tuple):
            if len(values) != 2:
                raise ValueError("Position requires exactly 2 positional arguments when not using keywords")
            return {'x': values[0], 'y': values[1]}
        return values

    def __add__(self, other) -> 'Position':
        return Position(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other) -> 'Position':
        return Position(x=self.x - other.x, y=self.y - other.y)

    def is_close(self, a: 'Position', tolerance: float = 0.5) -> bool:
        return abs(self.x - a.x) < tolerance and abs(self.y - a.y) < tolerance

    def distance(self, a: 'Position') -> float:
        # calculates the euclidean distance between two points
        return ((self.x - a.x) ** 2 + (self.y - a.y) ** 2) ** 0.5
    
    def _modifier(self, args=1):
        if isinstance(args, int) and args > 0:
            return args
        if len(args) > 0 and isinstance(args[0], int):
            return args[0]
        return 1
    def above(self, *args) -> 'Position':
        return Position(x=self.x, y=self.y - self._modifier(*args))
    def up(self, *args) -> 'Position':
        return self.above(args)
    def below(self, *args) -> 'Position':
        return Position(x=self.x, y=self.y + self._modifier(*args))
    def down(self, *args) -> 'Position':
        return self.below(args)
    def left(self, *args) -> 'Position':
        return Position(x=self.x - self._modifier(*args), y=self.y)
    def right(self, *args) -> 'Position':
        return Position(x=self.x + self._modifier(*args), y=self.y)

    def to_bounding_box(self, other: 'Position') -> 'BoundingBox':
        min_x = min(self.x, other.x)
        max_x = max(self.x, other.x)
        min_y = min(self.y, other.y)
        max_y = max(self.y, other.y)

        return BoundingBox(
            left_top=Position(min_x, min_y),
            right_bottom=Position(max_x, max_y),
            left_bottom=Position(min_x, max_y),
            right_top=Position(max_x, min_y)
        )
    def __eq__(self, other) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.is_close(other, tolerance=1)


class EntityInfo(BaseModel):
    name: str
    direction: int
    position: Position
    start_position: Optional[Position] = None
    end_position: Optional[Position] = None
    quantity: Optional[int] = None
    warning: Optional[str] = None
    contents: Dict[str, int] = {}
    status: EntityStatus = EntityStatus.NORMAL


class InspectionResults(BaseModel):
    entities: List[EntityInfo]
    player_position: Tuple[float, float] = (0, 0)
    radius: float = 10
    time_elapsed: float = 0

    def get_entity(self, prototype: 'Prototype') -> Optional[EntityInfo]:
        name = prototype.value[0]
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None

    def get_entities(self, prototype: 'Prototype') -> List[EntityInfo]:
        name = prototype.value[0]
        return [entity for entity in self.entities if entity.name == name]


class BoundingBox(BaseModel):
    left_top: Position
    right_bottom: Position
    left_bottom: Position
    right_top: Position

    def center(self) -> Position:
        return Position(
            x=(self.left_top.x + self.right_bottom.x)/2,
            y=(self.left_top.y + self.right_bottom.y)/2
        )

    def width(self) -> float:
        """
        Calculate the width of the bounding box.

        Returns:
            float: The absolute difference between right and left x-coordinates
        """
        return abs(self.right_bottom.x - self.left_top.x)

    def height(self) -> float:
        """
        Calculate the height of the bounding box.

        Returns:
            float: The absolute difference between bottom and top y-coordinates
        """
        return abs(self.right_bottom.y - self.left_top.y)

class BuildingBox(BaseModel):
    height: int
    width: int


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
    count: Optional[int] = 1
    type: Optional[str] = None

class Product(Ingredient):
    probability: Optional[float] = 1

class Recipe(BaseModel):
    name: Optional[str]
    ingredients: Optional[List[Ingredient]] = []
    products: Optional[List[Product]] = []
    energy: Optional[float] = 0
    category: Optional[str] = None
    enabled: bool = False


class BurnerType(BaseModel):
    class Config:
        arbitrary_types_allowed = True
    fuel: Inventory = Inventory()

class EntityCore(BaseModel):
    #id: Optional[str] = None
    name: str
    direction: Direction
    position: Position
    def __repr__(self):
        return f"Entity(name='{self.name}', direction={self.direction.name}, position=Position({self.position})"

class Entity(EntityCore):

    energy: float
    type: Optional[str] = None
    dimensions: Dimensions
    tile_dimensions: TileDimensions
    prototype: Any  # Prototype
    health: float
    warnings: List[str] = []
    status: EntityStatus = EntityStatus.NORMAL
    game: Optional[Any] = None # RCON connection for refreshing attributes

    def __repr__(self) -> str:
        # Only includes the fields we want to present to the agent
        # Get all instance attributes
        all_fields = self.__dict__

        # Filter out private attributes and excluded fields
        excluded_fields = {'dimensions', 'prototype', 'type', 'health', 'game'}
        rename_fields = {}
        repr_dict = {}

        for key, value in all_fields.items():
            # Remove the '_' prefix that pydantic adds to fields
            clean_key = key.lstrip('_')
            if clean_key not in excluded_fields and not clean_key.startswith('__'):
                if clean_key in rename_fields.keys():
                    clean_key = rename_fields[clean_key]
                # Handle enum values specially
                if isinstance(value, Enum):
                    repr_dict[clean_key] = value
                else:
                    if (clean_key == 'warnings' and value) or clean_key != 'warnings': # Don't show empty warnings list
                        repr_dict[clean_key] = value


        # Convert to string format
        items = [f"{k}={v!r}" for k, v in repr_dict.items()]
        return f"\n\t{self.__class__.__name__}({', '.join(items)})"
    def _get_prototype(self):
        return self.prototype

class StaticEntity(Entity):
    neighbours: Optional[Union[Dict, List[EntityCore]]] = []

class Splitter(Entity):
    input_positions: List[Position]
    output_positions: List[Position]
    inventory: List[Inventory] = []

class TransportBelt(Entity):
    input_position: Position
    output_position: Position
    inventory: Inventory = Inventory()
    is_terminus: bool = False
    is_source: bool = False

    def __repr__(self):
        return f"Belt(({self.input_position}) -> ({self.output_position}), direction={self.direction})"

    def __hash__(self):
        return hash((self.position.x, self.position.y))

    def __eq__(self, other):
        if not isinstance(other, TransportBelt):
            return False
        return (self.position.x, self.position.y) == (other.position.x, other.position.y)

class Electric(BaseModel):
    electrical_id: Optional[int] = None

class EnergySource(BaseModel):
    buffer_capacity: str
    input_flow_limit: str
    output_flow_limit: str
    drain: str

class Accumulator(StaticEntity, Electric):
    energy_source: Optional[EnergySource] = None

class Inserter(StaticEntity, Electric):
    pickup_position: Optional[Position] = None
    drop_position: Position

class UndergroundBelt(Entity):
    type: str

class MiningDrill(StaticEntity):
    drop_position: Position
    resources: List[Ingredient]

class ElectricMiningDrill(MiningDrill, Electric):
    pass

class BurnerInserter(Inserter, BurnerType):
    pass

class BurnerMiningDrill(MiningDrill, BurnerType):
    pass

class Ammo(BaseModel):
    name: str
    magazine_size: Optional[int] = 0
    reload_time: Optional[float] = 0

class GunTurret(StaticEntity):
    turret_ammo: Inventory = Inventory()

class AssemblingMachine(StaticEntity, Electric):
    recipe: Optional[Recipe] = None  # Prototype
    assembling_machine_input: Inventory = Inventory()
    assembling_machine_output: Inventory = Inventory()
    assembling_machine_modules: Inventory = Inventory()

class FluidHandler(StaticEntity):
    connection_points: List[Position] = []
    fluid_box: Optional[Union[dict, list]] = []
    fluid_systems: Optional[Union[dict, list]] = []

class MultiFluidHandler(StaticEntity):
    input_connection_points: List[Position] = []
    output_connection_points: List[Position] = []
    fluid_box: Optional[Union[dict, list]] = []
    fluid_systems: Optional[Union[dict, list]] = []

class ChemicalPlant(MultiFluidHandler, AssemblingMachine):
    pass

class OilRefinery(MultiFluidHandler, Electric):
    pass

class PumpJack(MiningDrill, FluidHandler, Electric):
    pass

class Boiler(FluidHandler, BurnerType):
    steam_output_point: Optional[Position] = None

class Generator(FluidHandler, Electric):
    pass


class OffshorePump(FluidHandler):
    pass
    #fluid_box: Optional[Union[dict,list]] = []

class ElectricityPole(Entity, Electric):
    flow_rate: float

    def __hash__(self):
        return self.electrical_id

class Furnace(Entity, BurnerType):
    furnace_source: Inventory = Inventory()
    furnace_result: Inventory = Inventory()

class Chest(Entity):
    inventory: Inventory = Inventory()

class Lab(Entity, Electric):
    lab_input: Inventory = Inventory()
    lab_modules: Inventory = Inventory()
    research: Optional[Any] = None # Technology

    def __repr__(self) -> str:
        from game_types import technology_by_name
        research_string = ""
        if self.research and self.research in technology_by_name:
            research_string=f"research={self.research}, "
        return f"\n\tLab(lab_input={self.lab_input}, status={self.status}, {research_string}electrical_id={self.electrical_id})"

class Pipe(Entity):
    fluidbox_id: int
    flow_rate: float
    contents: float
    fluid: Optional[str] = None

class EntityGroup(BaseModel):
    id: int
    status: EntityStatus = EntityStatus.NORMAL
    position: Position
    name: str = "entity-group"

class BeltGroup(EntityGroup):
    belts: List[TransportBelt]
    inputs: List[Entity]
    outputs: List[Entity]
    inventory: Inventory = Inventory()
    name: str = 'belt-group'

    def __repr__(self) -> str:
        belt_summary = f"[{len(self.belts)} belts]"
        return f"\n\tBeltGroup(inputs={self.inputs}, outputs={self.outputs}, inventory={self.inventory}, status={self.status}, belts={belt_summary})"

class PipeGroup(EntityGroup):
    pipes: List[Pipe]
    name: str = 'pipe-group'

    def __repr__(self) -> str:
        pipe_summary = f"[{len(self.pipes)} pipes]"
        fluid_suffix = ""
        if self.pipes and self.pipes[0].fluid is not None and self.pipes[0].fluid != "":
            fluid_suffix = f"fluid={self.pipes[0].fluid} "
        positions = [f"(x={p.position.x},y={p.position.y})" for p in self.pipes]
        if len(positions) > 6:
            positions = positions[:3] + ['...'] + positions[-3:]
        pipe_summary = f"[{','.join(positions)}]"

        return f"\n\tPipeGroup(fluid_system={self.id}, {fluid_suffix}position={self.position}, status={self.status}, pipes={pipe_summary})"

class ElectricityGroup(EntityGroup):
    name: str = 'electricity-group'
    poles: List[ElectricityPole]

    def __repr__(self) -> str:
        positions = [f"(x={p.position.x},y={p.position.y})" for p in self.poles]
        max_flow_rate = math.floor(max([p.flow_rate for p in self.poles]))
        if len(positions) > 6:
            positions = positions[:3] + ['...'] + positions[-3:]
        pole_summary = f"[{','.join(positions)}]"
        return f"\tElectricityGroup(id={self.id}, poles={pole_summary}, voltage={max_flow_rate})"

    def __hash__(self):
        return self.name+str(self.id)