from fle.env.game_types import Prototype


class EntityCategoriser:
    """Handles the categorisation of Factorio entities based on their types"""

    @staticmethod
    def get_entity_category(entity) -> str:
        """
        Determine category for an entity based on its class hierarchy or Prototype

        Args:
            entity: An Entity instance, a dictionary with 'name' key, or a Prototype enum

        Returns:
            String representing the entity category
        """
        from fle.env import (
            TransportBelt,
            Splitter,
            UndergroundBelt,
            BeltGroup,  # Belt category
            Inserter,
            FilterInserter,
            BurnerInserter,  # Inserter category
            ElectricalProducer,
            ElectricityPole,
            Accumulator,
            Generator,
            ElectricityGroup,  # Power category
            FluidHandler,
            MultiFluidHandler,
            Pipe,
            PipeGroup,
            OffshorePump,
            Pump,
            StorageTank,
            Boiler,  # Fluid category
            AssemblingMachine,
            AdvancedAssemblingMachine,
            ChemicalPlant,
            OilRefinery,
            Furnace,
            ElectricFurnace,
            Lab,
            RocketSilo,  # Production category
            Chest,  # Logistics category
            GunTurret,
            WallGroup,  # Defense category
            MiningDrill,
            ElectricMiningDrill,
            BurnerMiningDrill,
            PumpJack,  # Mining category
        )

        # Check if this is a Prototype enum
        if isinstance(entity, Prototype):
            prototype_name = entity.prototype_name
            entity_class = entity.entity_class

            # Resource types
            if prototype_name in [
                "iron-ore",
                "copper-ore",
                "coal",
                "stone",
                "uranium-ore",
                "crude-oil",
            ]:
                return prototype_name

            # Check entity class for category
            if entity_class is None:
                # Handle items/resources with no entity class
                if (
                    "ore" in prototype_name
                    or prototype_name == "coal"
                    or prototype_name == "stone"
                ):
                    return "resource"
                return "item"  # Default for items

            # Check entity class for category
            if issubclass(
                entity_class, (TransportBelt, Splitter, UndergroundBelt, BeltGroup)
            ):
                return "belt"
            elif issubclass(entity_class, (Inserter, FilterInserter, BurnerInserter)):
                return "inserter"
            elif issubclass(
                entity_class,
                (
                    ElectricalProducer,
                    ElectricityPole,
                    Accumulator,
                    Generator,
                    ElectricityGroup,
                ),
            ):
                return "power"
            elif issubclass(entity_class, (Pipe, PipeGroup)):
                return "pipe"
            elif issubclass(
                entity_class,
                (
                    FluidHandler,
                    MultiFluidHandler,
                    OffshorePump,
                    Pump,
                    StorageTank,
                    Boiler,
                ),
            ):
                return "fluid"
            elif issubclass(
                entity_class,
                (
                    AssemblingMachine,
                    AdvancedAssemblingMachine,
                    ChemicalPlant,
                    OilRefinery,
                    Furnace,
                    ElectricFurnace,
                    Lab,
                    RocketSilo,
                ),
            ):
                return "production"
            elif issubclass(entity_class, Chest):
                return "logistics"
            elif issubclass(entity_class, (GunTurret, WallGroup)):
                return "defense"
            elif issubclass(
                entity_class,
                (MiningDrill, ElectricMiningDrill, BurnerMiningDrill, PumpJack),
            ):
                return "mining"

            # Default - use the class name
            return entity_class.__name__.lower()

        # Check if this is a resource entity from map data
        if isinstance(entity, dict) and "name" in entity:
            resource_name = entity.get("name")
            if resource_name in [
                "iron-ore",
                "copper-ore",
                "coal",
                "stone",
                "uranium-ore",
                "crude-oil",
            ]:
                return (
                    resource_name  # Return the specific resource name as the category
                )

            # Check if this is a water tile from map data
            if "water" in resource_name:
                return "water"

            # For entity name strings, try to match with known categories
            lower_name = resource_name.lower()

            if any(
                belt_type in lower_name
                for belt_type in ["transport-belt", "splitter", "underground-belt"]
            ):
                return "belt"
            elif "inserter" in lower_name:
                return "inserter"
            elif any(
                power_type in lower_name
                for power_type in ["electric-pole", "accumulator", "engine", "solar"]
            ):
                return "power"
            elif any(
                fluid_type in lower_name
                for fluid_type in ["pipe", "pump", "tank", "boiler"]
            ):
                return "fluid"
            elif any(
                prod_type in lower_name
                for prod_type in [
                    "assembling",
                    "furnace",
                    "chemical",
                    "refinery",
                    "lab",
                ]
            ):
                return "production"
            elif "chest" in lower_name:
                return "logistics"
            elif any(defense_type in lower_name for defense_type in ["turret", "wall"]):
                return "defense"
            elif any(
                mining_type in lower_name
                for mining_type in ["mining-drill", "pumpjack"]
            ):
                return "mining"

            # If no match was found, return a general category
            return "entity"

        # Resource types have a primitive prototype without a complex class hierarchy
        if hasattr(entity, "prototype") and entity.prototype is not None:
            if isinstance(entity.prototype, Prototype):
                # Use the prototype's category
                return EntityCategoriser.get_entity_category(entity.prototype)

            proto_name = (
                entity.prototype.value[0] if hasattr(entity.prototype, "value") else ""
            )
            if any(
                resource in proto_name
                for resource in ["ore", "coal", "stone", "crude-oil"]
            ):
                return "resource"

        # Original instance checks
        if isinstance(entity, (TransportBelt, Splitter, UndergroundBelt, BeltGroup)):
            return "belt"
        elif isinstance(entity, (Inserter, FilterInserter, BurnerInserter)):
            return "inserter"
        elif isinstance(
            entity,
            (
                ElectricalProducer,
                ElectricityPole,
                Accumulator,
                Generator,
                ElectricityGroup,
            ),
        ):
            return "power"
        elif isinstance(entity, (Pipe, PipeGroup)):
            return "pipe"
        elif isinstance(
            entity,
            (
                FluidHandler,
                MultiFluidHandler,
                Pipe,
                PipeGroup,
                OffshorePump,
                Pump,
                StorageTank,
                Boiler,
            ),
        ):
            return "fluid"
        elif isinstance(
            entity,
            (
                AssemblingMachine,
                AdvancedAssemblingMachine,
                ChemicalPlant,
                OilRefinery,
                Furnace,
                ElectricFurnace,
                Lab,
                RocketSilo,
            ),
        ):
            return "production"
        elif isinstance(entity, Chest):
            return "logistics"
        elif isinstance(entity, (GunTurret, WallGroup)):
            return "defense"
        elif isinstance(
            entity, (MiningDrill, ElectricMiningDrill, BurnerMiningDrill, PumpJack)
        ):
            return "mining"

        # Default - use the class name to derive a category
        if hasattr(entity, "__class__"):
            class_name = type(entity).__name__
            return class_name.lower()

        # Final fallback
        return "unknown"
