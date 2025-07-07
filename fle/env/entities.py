import math
from typing import Tuple, Any, Union, Dict, Literal
from typing import List, Optional
from enum import Enum, IntFlag
from pydantic import BaseModel, model_validator


class Layer(IntFlag):
    """Enum representing different layers that can be rendered on the map"""

    NONE = 0
    GRID = 1 << 0  # Grid lines
    WATER = 1 << 1  # Water tiles
    RESOURCES = 1 << 2  # Resource patches (iron, copper, coal, etc.)
    TREES = 1 << 3  # Trees
    ROCKS = 1 << 4  # Rocks
    ENTITIES = 1 << 5  # Player-built entities
    CONNECTIONS = 1 << 6  # Underground belt/pipe connections
    ORIGIN = 1 << 7  # Origin marker (0,0)
    PLAYER = 1 << 8  # Player position marker
    LABELS = 1 << 9  # Entity labels
    ELECTRICITY = 1 << 10  # New layer for electricity networks

    # Convenience combinations
    NATURAL = TREES | ROCKS  # All natural elements

    # Use this explicit definition instead of ~0 to ensure we only include defined flags
    ALL = (
        GRID
        | WATER
        | RESOURCES
        | TREES
        | ROCKS
        | ENTITIES
        | CONNECTIONS
        | ORIGIN
        | PLAYER
        | LABELS
        | ELECTRICITY
    )


# This should really live in `types`, but it's here to prevent a circular import
class EntityStatus(Enum):
    WORKING = "working"
    NORMAL = "normal"
    NO_POWER = "no_power"
    LOW_POWER = "low_power"
    NO_FUEL = "no_fuel"
    EMPTY = "empty"
    # DISABLED_BY_CONTROL_BEHAVIOR = "disabled_by_control_behavior"
    # OPENED_BY_CIRCUIT_NETWORK = "opened_by_circuit_network"
    # CLOSED_BY_CIRCUIT_NETWORK = "closed_by_circuit_network"
    # DISABLED_BY_SCRIPT = "disabled_by_script"
    # MARKED_FOR_DECONSTRUCTION = "marked_for_deconstruction"
    NOT_PLUGGED_IN_ELECTRIC_NETWORK = "not_plugged_in_electric_network"
    # NETWORKS_CONNECTED = "networks_connected"
    # NETWORKS_DISCONNECTED = "networks_disconnected"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULLY_CHARGED = "fully_charged"
    # OUT_OF_LOGISTIC_NETWORK = "out_of_logistic_network"
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

    PREPARING_ROCKET_FOR_LAUNCH = "preparing_rocket_for_launch"
    WAITING_TO_LAUNCH_ROCKET = "waiting_to_launch_rocket"
    LAUNCHING_ROCKET = "launching_rocket"
    # NO_MODULES_TO_TRANSMIT = "no_modules_to_transmit"
    # RECHARGING_AFTER_POWER_OUTAGE = "recharging_after_power_outage"
    # WAITING_FOR_TARGET_TO_BE_BUILT = "waiting_for_target_to_be_built"
    # WAITING_FOR_TRAIN = "waiting_for_train"
    NO_AMMO = "no_ammo"
    LOW_TEMPERATURE = "low_temperature"
    # DISABLED = "disabled"
    # TURNED_OFF_DURING_DAYTIME = "turned_off_during_daytime"
    NOT_CONNECTED_TO_RAIL = "not_connected_to_rail"
    # CANT_DIVIDE_SEGMENTS = "cant_divide_segments"

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
        populate_by_name = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__()
        self.__dict__.update(data)

    def __getitem__(self, key: "Prototype", default=None) -> int:  # noqa
        try:
            if hasattr(key, "value"):
                name, _ = key.value
            elif isinstance(key, tuple):
                name = key[0]
            else:
                name = key
        except Exception:
            pass
        return self.__dict__[name] if name in self.__dict__ else 0

    def get(self, key: "Prototype", default=0) -> int:  # noqa
        try:
            if hasattr(key, "value"):
                name, _ = key.value
            else:
                name = key
        except Exception:
            pass

        item = self.__getitem__(name)
        return item if item else default

    def __setitem__(self, key: "Prototype", value: int) -> None:  # noqa
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
            return {"x": v[0], "y": v[1]}
        return v

    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise ValueError("Cannot mix positional and keyword arguments")

        if args:
            if len(args) != 2:
                raise ValueError("Position requires exactly 2 positional arguments")
            kwargs = {"x": args[0], "y": args[1]}

        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def parse_args(cls, values):
        if isinstance(values, tuple):
            if len(values) != 2:
                raise ValueError(
                    "Position requires exactly 2 positional arguments when not using keywords"
                )
            return {"x": values[0], "y": values[1]}
        return values

    def __hash__(self):
        return hash(f"{self.x},{self.y}")

    def __add__(self, other) -> "Position":
        return Position(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other) -> "Position":
        return Position(x=self.x - other.x, y=self.y - other.y)

    def is_close(self, a: "Position", tolerance: float = 0.5) -> bool:
        return abs(self.x - a.x) < tolerance and abs(self.y - a.y) < tolerance

    def distance(self, a: "Position") -> float:
        # calculates the euclidean distance between two points
        return ((self.x - a.x) ** 2 + (self.y - a.y) ** 2) ** 0.5

    def _modifier(self, args=1):
        if isinstance(args, (float, int)):
            return args
        if len(args) > 0 and isinstance(args[0], (float, int)):
            return args[0]
        return 1

    def above(self, *args) -> "Position":
        return Position(x=self.x, y=self.y - self._modifier(*args))

    def up(self, *args) -> "Position":
        return self.above(args)

    def below(self, *args) -> "Position":
        return Position(x=self.x, y=self.y + self._modifier(*args))

    def down(self, *args) -> "Position":
        return self.below(args)

    def left(self, *args) -> "Position":
        return Position(x=self.x - self._modifier(*args), y=self.y)

    def right(self, *args) -> "Position":
        return Position(x=self.x + self._modifier(*args), y=self.y)

    def to_bounding_box(self, other: "Position") -> "BoundingBox":
        min_x = min(self.x, other.x)
        max_x = max(self.x, other.x)
        min_y = min(self.y, other.y)
        max_y = max(self.y, other.y)

        return BoundingBox(
            left_top=Position(min_x, min_y),
            right_bottom=Position(max_x, max_y),
            left_bottom=Position(min_x, max_y),
            right_top=Position(max_x, min_y),
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.is_close(other, tolerance=1)


class IndexedPosition(Position):
    type: str

    def __new__(cls, *args, **kwargs):
        # Handle both positional and keyword arguments
        if args and not kwargs:
            if len(args) == 3:  # x, y, type
                kwargs = {"x": args[0], "y": args[1], "type": args[2]}
            elif len(args) == 2:  # x, y only
                kwargs = {"x": args[0], "y": args[1]}

        # If this is being called from a parent class method (like above(), left(), etc.)
        # we need to preserve the type from the original instance
        if not kwargs.get("type") and hasattr(cls, "_current_type"):
            kwargs["type"] = cls._current_type

        instance = super().__new__(cls)

        # Store the type at class level temporarily for child instances
        if "type" in kwargs:
            cls._current_type = kwargs["type"]

        return instance

    def __init__(self, *args, **kwargs):
        if args and not kwargs:
            if len(args) == 3:  # x, y, type
                kwargs = {"x": args[0], "y": args[1], "type": args[2]}
            elif len(args) == 2:  # x, y only
                kwargs = {"x": args[0], "y": args[1]}
        super().__init__(**kwargs)

    def __hash__(self):
        return hash(f"{self.x},{self.y},{self.type}")


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

    def get_entity(self, prototype: "Prototype") -> Optional[EntityInfo]:  # noqa
        name = prototype.value[0]
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None

    def get_entities(self, prototype: "Prototype") -> List[EntityInfo]:  # noqa
        name = prototype.value[0]
        return [entity for entity in self.entities if entity.name == name]


class BoundingBox(BaseModel):
    left_top: Position
    right_bottom: Position
    left_bottom: Position
    right_top: Position

    @property
    def center(self) -> Position:
        return Position(
            x=(self.left_top.x + self.right_bottom.x) / 2,
            y=(self.left_top.y + self.right_bottom.y) / 2,
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
    type: Optional[Literal["fluid", "item"]] = None


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
    """Type of entity that burns fuel"""

    class Config:
        arbitrary_types_allowed = True

    fuel: Inventory = Inventory()  # Use this to check the fuel levels of the entity


class EntityCore(BaseModel):
    # id: Optional[str] = None
    name: str
    direction: Direction
    position: Position

    def __repr__(self):
        return f"Entity(name='{self.name}', direction={self.direction.name}, position=Position({self.position})"


class Entity(EntityCore):
    """Base class for all entities in the game."""

    id: Optional[int] = None
    energy: float
    type: Optional[str] = None
    dimensions: Dimensions
    tile_dimensions: TileDimensions
    prototype: Any  # Prototype
    health: float
    warnings: List[str] = []
    status: EntityStatus = EntityStatus.NORMAL
    # game: Optional[Any] = None # RCON connection for refreshing attributes

    def __repr__(self) -> str:
        # Only includes the fields we want to present to the agent
        # Get all instance attributes
        all_fields = self.__dict__

        # Filter out private attributes and excluded fields
        excluded_fields = {
            "dimensions",
            "prototype",
            "type",
            "health",
            "game",
            "id",
            "tile_dimensions",
        }
        rename_fields = {}
        repr_dict = {}

        for key, value in all_fields.items():
            # Remove the '_' prefix that pydantic adds to fields
            clean_key = key.lstrip("_")
            if clean_key not in excluded_fields and not clean_key.startswith("__"):
                if clean_key in rename_fields.keys():
                    clean_key = rename_fields[clean_key]
                # Handle enum values specially
                if isinstance(value, Enum):
                    repr_dict[clean_key] = value
                else:
                    if (
                        clean_key == "warnings" and value
                    ) or clean_key != "warnings":  # Don't show empty warnings list
                        repr_dict[clean_key] = value

        repr_dict["height"] = self.tile_dimensions.tile_height
        repr_dict["width"] = self.tile_dimensions.tile_width

        # Convert to string format
        items = [f"{k}={v!r}" for k, v in repr_dict.items()]
        return f"\n\t{self.__class__.__name__}({', '.join(items)})"

    def _get_prototype(self):
        return self.prototype

    @classmethod
    @property
    def width(cls):
        return cls._width

    @classmethod
    @property
    def height(cls):
        return cls._height


class StaticEntity(Entity):
    """A static (non-moving) entity in the game."""

    neighbours: Optional[Union[Dict, List[EntityCore]]] = []


class Rail(Entity):
    """Railway track for trains."""

    _height: float = 1
    _width: float = 1


class Splitter(Entity):
    """A belt splitter that divides item flow between outputs."""

    input_positions: List[Position]
    output_positions: List[Position]
    inventory: List[Inventory] = []
    _height: float = 1
    _width: float = 2


class TransportBelt(Entity):
    """A conveyor belt for moving items."""

    input_position: Position
    output_position: Position
    inventory: Inventory = Inventory()
    is_terminus: bool = False
    is_source: bool = False
    _height: float = 1
    _width: float = 1

    def __repr__(self):
        return f"Belt(({self.position})->, direction={self.direction})"

    def __hash__(self):
        return hash((self.position.x, self.position.y))

    def __eq__(self, other):
        if not isinstance(other, TransportBelt):
            return False
        return (self.position.x, self.position.y) == (
            other.position.x,
            other.position.y,
        )


class Electric(BaseModel):
    """Base class for entities that interact with the power grid."""

    electrical_id: Optional[int] = None


class ElectricalProducer(Electric, Entity):
    """An entity that generates electrical power."""

    production: Optional[Any] = {}
    energy_source: Optional[Any] = {}
    electric_output_flow_limit: Optional[float] = 0


class EnergySource(BaseModel):
    buffer_capacity: str
    input_flow_limit: str
    output_flow_limit: str
    drain: str


class Accumulator(StaticEntity, Electric):
    """Represents an energy storage device"""

    energy_source: Optional[EnergySource] = None
    _height: float = 2
    _width: float = 2


class Inserter(StaticEntity, Electric):
    """Represents an inserter that moves items between entities.
    Requires electricity to power"""

    pickup_position: Optional[Position] = None
    drop_position: Position
    _width: float = 1
    _height: float = 1


class Filtered(BaseModel):
    filter: Optional[Any] = None


class UndergroundBelt(TransportBelt):
    """An underground section of transport belt."""

    is_input: bool
    connected_to: Optional[int] = None
    _height: float = 1
    _width: float = 1


class MiningDrill(StaticEntity):
    """Base class for mining drills that extract resources.
    The direction of the drill is where the drop_position is oriented towards"""

    drop_position: Position
    resources: List[Ingredient]


class ElectricMiningDrill(MiningDrill, Electric):
    """An electrically-powered mining drill."""

    _height: float = 3
    _width: float = 3
    pass


class BurnerInserter(Inserter, BurnerType):
    """An inserter powered by burnable fuel."""

    _height: float = 1
    _width: float = 1
    pass


class BurnerMiningDrill(MiningDrill, BurnerType):
    """A mining drill powered by burnable fuel."""

    _width = 2
    _height = 2


class Ammo(BaseModel):
    name: str
    magazine_size: Optional[int] = 0
    reload_time: Optional[float] = 0


class GunTurret(StaticEntity):
    turret_ammo: Inventory = Inventory()
    _height: float = 2
    _width: float = 2
    kills: Optional[int] = 0


class AssemblingMachine(StaticEntity, Electric):
    """A machine that crafts items from ingredients.
    Requires power to operate"""

    recipe: Optional[Recipe] = None  # Prototype
    assembling_machine_input: Inventory = Inventory()
    assembling_machine_output: Inventory = Inventory()
    assembling_machine_modules: Inventory = Inventory()
    _height: float = 3
    _width: float = 3


class FluidHandler(StaticEntity):
    """Base class for entities that handle fluids"""

    connection_points: List[Position] = []
    fluid_box: Optional[Union[dict, list]] = []
    fluid_systems: Optional[Union[dict, list]] = []


class AdvancedAssemblingMachine(FluidHandler, AssemblingMachine):
    """A second and third tier assembling machine that can handle fluids.
    Requires power to operate
    A recipe first needs to be set and then the input fluid source can be connected with pipes"""

    _height: float = 3
    _width: float = 3


class MultiFluidHandler(StaticEntity):
    """Base class for entities that handle multiple fluid types."""

    input_fluids: List[str] = []
    output_fluids: List[str] = []
    input_connection_points: List[IndexedPosition] = []
    output_connection_points: List[IndexedPosition] = []
    fluid_box: Optional[Union[dict, list]] = []
    fluid_systems: Optional[Union[dict, list]] = []


class FilterInserter(Inserter, Filtered):
    """A inserter that only moves specific items"""

    _height: float = 1
    _width: float = 1


class ChemicalPlant(MultiFluidHandler, AssemblingMachine):
    """Represents a chemical plant that processes fluid recipes.
    Requires powering and accepts input fluids (from storage tanks etc) and solids (with inserters)
    Outputs either:
        solids (battery, plastic) that need to be extracted with inserters
        fluids (sulfuric acid, oil) that need to be extracted with pipes
    IMPORTANT: First a recipe needs to be set and then the fluid sources can be connected to the plant"""

    _height: float = 3
    _width: float = 3
    pass


class OilRefinery(MultiFluidHandler, AssemblingMachine):
    """An oil refinery for processing crude oil into products.
    Requires powering and accepts input fluids (from pumpjacks, storage tanks etc) and solids
    First a recipe needs to be set and then the fluid sources can be connected to the refinery"""

    _height: float = 5
    _width: float = 5


class PumpJack(MiningDrill, FluidHandler, Electric):
    """A pump jack for extracting crude oil. Requires electricity.
    This needs to be placed on crude oil and oil needs to be extracted with pipes
    Oil can be sent to a storage tank, oil refinery or a chemical plant
    Oil can also be sent to assmbling machine to be made into oil barrels
    Important: The PumpJack needs to be placed on exact crude oil tiles
    """

    _height: float = 3
    _width: float = 3
    pass


class SolarPanel(ElectricalProducer):
    """A solar panel for generating power from sunlight.
    This entity generated power during the day
    Thus it can be directly connected to a entity to power it"""

    _height: float = 3
    _width: float = 3


class Boiler(FluidHandler, BurnerType):
    """A boiler that heats water into steam."""

    steam_output_point: Optional[Position] = None
    _height: float = 2
    _width: float = 3


class HeatExchanger(Boiler):
    """A nuclear heat exchanger that converts water to steam."""


class Generator(FluidHandler, StaticEntity):
    """A steam generator that produces electricity."""

    _height: float = 3
    _width: float = 5


class Pump(FluidHandler, Electric):
    """An electrically-powered fluid pump."""

    _height: float = 1
    _width: float = 2
    pass


class OffshorePump(FluidHandler):
    """A pump that extracts water from water tiles.
    Can be used in power generation setups and to supply water to chemical plants and oil refineries."""

    _height: float = 1
    _width: float = 2
    pass


class ElectricityPole(Entity, Electric):
    """A power pole for electricity distribution."""

    flow_rate: float
    _height: float = 1
    _width: float = 1

    def __hash__(self):
        return self.electrical_id


class Furnace(Entity, BurnerType):
    """A furnace for smelting items"""

    furnace_source: Inventory = Inventory()
    furnace_result: Inventory = Inventory()
    _height: float = 2
    _width: float = 2


class ElectricFurnace(Entity, Electric):
    """An electrically-powered furnace."""

    furnace_source: Inventory = Inventory()
    furnace_result: Inventory = Inventory()
    _height: float = 3
    _width: float = 3


class Chest(Entity):
    """A storage chest."""

    inventory: Inventory = Inventory()
    _height: float = 1
    _width: float = 1


class StorageTank(FluidHandler):
    """A tank for storing fluids.
    Can be used for inputs and outputs of chemical plants and refineries.
    Also can store water from offshore pumps."""

    _height: float = 3
    _width: float = 3


class RocketSilo(StaticEntity, Electric):
    """A rocket silo that can build and launch rockets."""

    rocket_parts: int = 0  # Number of rocket parts currently assembled
    rocket_inventory: Inventory = Inventory()  # Holds satellite or other payload
    rocket_progress: float = 0.0  # Progress of current rocket construction (0-100)
    launch_count: int = 0  # Number of successful launches
    _width: float = 9
    _height: float = 9

    def __repr__(self) -> str:
        return (
            f"\n\tRocketSilo(position={self.position}, status={self.status}, "
            f"rocket_parts={self.rocket_parts}, rocket_progress={self.rocket_progress:.1f}%, "
            f"launch_count={self.launch_count})"
        )


class Rocket(Entity):
    """A rocket that can be launched from a silo."""

    payload: Optional[Inventory] = None
    launch_progress: float = 0.0  # Progress of launch sequence (0-100)

    def __repr__(self) -> str:
        payload_str = f", payload={self.payload}" if self.payload else ""
        return f"\n\tRocket(status={self.status}, launch_progress={self.launch_progress:.1f}%{payload_str})"


class Lab(Entity, Electric):
    """A research laboratory."""

    lab_input: Inventory = Inventory()
    lab_modules: Inventory = Inventory()
    research: Optional[Any] = None  # Technology
    _height: float = 3
    _width: float = 3

    def __repr__(self) -> str:
        from fle.env.game_types import technology_by_name

        research_string = ""
        if self.research and self.research in technology_by_name:
            research_string = f"research={self.research}, "
        return f"\n\tLab(lab_input={self.lab_input}, status={self.status}, {research_string}electrical_id={self.electrical_id})"


class Pipe(Entity):
    """A pipe for fluid transport"""

    fluidbox_id: int
    flow_rate: float
    contents: float
    fluid: Optional[str] = None
    _height: float = 1
    _width: float = 1


class Reactor(StaticEntity):
    """A nuclear reactor"""

    _height: float = 5
    _width: float = 5


class EntityGroup(BaseModel):
    id: int
    status: EntityStatus = EntityStatus.NORMAL
    position: Position
    name: str = "entity-group"


class WallGroup(EntityGroup):
    """A wall"""

    name: str = "wall-group"
    entities: List[Entity]


class BeltGroup(EntityGroup):
    """A connected group of transport belts."""

    belts: List[TransportBelt]
    inputs: List[Entity]
    outputs: List[Entity]
    inventory: Inventory = Inventory()
    name: str = "belt-group"

    def __repr__(self) -> str:
        belt_summary = f"[{len(self.belts)} belts]"
        return f"\n\tBeltGroup(inputs={self.inputs}, outputs={self.outputs}, inventory={self.inventory}, status={self.status}, belts={belt_summary})"

    def __str__(self):
        return self.__repr__()


class PipeGroup(EntityGroup):
    """A connected group of pipes."""

    pipes: List[Pipe]
    name: str = "pipe-group"

    def __repr__(self) -> str:
        pipe_summary = f"[{len(self.pipes)} pipes]"
        fluid_suffix = ""
        if self.pipes and self.pipes[0].fluid is not None and self.pipes[0].fluid != "":
            fluid_suffix = f"fluid={self.pipes[0].fluid} "
        positions = [f"(x={p.position.x},y={p.position.y})" for p in self.pipes]
        if len(positions) > 6:
            positions = positions[:3] + ["..."] + positions[-3:]
        pipe_summary = f"[{','.join(positions)}]"

        return f"\n\tPipeGroup(fluid_system={self.id}, {fluid_suffix}position={self.position}, status={self.status}, pipes={pipe_summary})"

    def __str__(self):
        return self.__repr__()


class ElectricityGroup(EntityGroup):
    """Represents a connected power network."""

    name: str = "electricity-group"
    poles: List[ElectricityPole]

    def __repr__(self) -> str:
        positions = [f"(x={p.position.x},y={p.position.y})" for p in self.poles]
        max_flow_rate = math.floor(max([p.flow_rate for p in self.poles]))
        if len(positions) > 6:
            positions = positions[:3] + ["..."] + positions[-3:]
        pole_summary = f"[{','.join(positions)}]"
        return f"\tElectricityGroup(id={self.id}, poles={pole_summary}, voltage={max_flow_rate})"

    def __hash__(self):
        return self.name + str(self.id)

    def __str__(self):
        return self.__repr__()
