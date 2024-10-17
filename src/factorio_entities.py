from typing import Tuple, Any, Union, Dict
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, PrivateAttr


class EntityStatus(Enum):
    WORKING = "working"
    NORMAL = "normal"
    NO_POWER = "no_power"
    LOW_POWER = "low_power"
    NO_FUEL = "no_fuel"
    DISABLED_BY_CONTROL_BEHAVIOR = "disabled_by_control_behavior"
    OPENED_BY_CIRCUIT_NETWORK = "opened_by_circuit_network"
    CLOSED_BY_CIRCUIT_NETWORK = "closed_by_circuit_network"
    DISABLED_BY_SCRIPT = "disabled_by_script"
    MARKED_FOR_DECONSTRUCTION = "marked_for_deconstruction"
    NOT_PLUGGED_IN_ELECTRIC_NETWORK = "not_plugged_in_electric_network"
    NETWORKS_CONNECTED = "networks_connected"
    NETWORKS_DISCONNECTED = "networks_disconnected"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULLY_CHARGED = "fully_charged"
    OUT_OF_LOGISTIC_NETWORK = "out_of_logistic_network"
    NO_RECIPE = "no_recipe"
    NO_INGREDIENTS = "no_ingredients"
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
    PREPARING_ROCKET_FOR_LAUNCH = "preparing_rocket_for_launch"
    WAITING_TO_LAUNCH_ROCKET = "waiting_to_launch_rocket"
    LAUNCHING_ROCKET = "launching_rocket"
    NO_MODULES_TO_TRANSMIT = "no_modules_to_transmit"
    RECHARGING_AFTER_POWER_OUTAGE = "recharging_after_power_outage"
    WAITING_FOR_TARGET_TO_BE_BUILT = "waiting_for_target_to_be_built"
    WAITING_FOR_TRAIN = "waiting_for_train"
    NO_AMMO = "no_ammo"
    LOW_TEMPERATURE = "low_temperature"
    DISABLED = "disabled"
    TURNED_OFF_DURING_DAYTIME = "turned_off_during_daytime"
    NOT_CONNECTED_TO_RAIL = "not_connected_to_rail"
    CANT_DIVIDE_SEGMENTS = "cant_divide_segments"

    @classmethod
    def from_string(cls, status_string):
        for status in cls:
            if status.value == status_string:
                return status
        return None


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


class Direction(Enum):
    UP = NORTH = 0
    RIGHT = EAST = 2
    DOWN = SOUTH = 4
    LEFT = WEST = 6

class Position(BaseModel):
    x: float
    y: float

    def __add__(self, other):
        return Position(x=self.x + other.x, y=self.y + other.y)

    def is_close(self, a: 'Position', tolerance: float = 0.1):
        return abs(self.x - a.x) < tolerance and abs(self.y - a.y) < tolerance


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
    ingredients: Union[List[Ingredient], Dict[str, Any]]
    products: Optional[Union[List[Ingredient], Dict[str, Any]]] = []
    energy: Optional[float] = 0
    category: Optional[str] = None
    enabled: bool = False


class BurnerType(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    fuel: Inventory


class Entity(BaseModel):
    name: str
    position: Position
    direction: Direction
    energy: float
    type: str
    dimensions: Dimensions
    tile_dimensions: TileDimensions
    prototype: Any  # Prototype
    health: float


class TransportBelt(Entity):
    input_position: Position
    output_position: Position
    inventory: Inventory

class EnergySource(BaseModel):
    buffer_capacity: str
    input_flow_limit: str
    output_flow_limit: str
    drain: str

class Accumulator(Entity):
    energy_source: Optional[EnergySource] = None

class Inserter(Entity):
    pickup_position: Optional[Position] = None
    drop_position: Position


class MiningDrill(Entity):
    drop_position: Position


class BurnerInserter(Inserter, BurnerType):
    pass


class BurnerMiningDrill(MiningDrill, BurnerType):
    pass

class Ammo(BaseModel):
    name: str
    magazine_size: Optional[int] = 0
    reload_time: Optional[float] = 0

class GunTurret(Entity):
    turret_ammo: Inventory

class AssemblingMachine1(Entity):
    recipe: Optional[Recipe] = None  # Prototype
    assembling_machine_input: Inventory
    assembling_machine_output: Inventory
    assembling_machine_modules: Inventory

class FluidHandler(Entity):
    connection_points: List[Position]


class Boiler(FluidHandler):
    steam_output_point: Position


class Generator(FluidHandler):
    pass


class OffshorePump(FluidHandler):
    fluid_box: Optional[dict] = {}


class Furnace(Entity, BurnerType):
    furnace_source: Inventory
    furnace_result: Inventory

class Chest(Entity):
    inventory: Inventory

class Lab(Entity):
    lab_input: Inventory
    lab_modules: Inventory