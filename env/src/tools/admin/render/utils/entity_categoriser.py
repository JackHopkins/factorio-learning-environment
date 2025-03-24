from entities import Entity


class EntityCategoriser:
    """Handles the categorisation of Factorio entities based on their types"""

    @staticmethod
    def get_entity_category(entity: Entity) -> str:
        """Determine category for an entity based on its class hierarchy"""
        from entities import (
            TransportBelt, Splitter, UndergroundBelt, BeltGroup,  # Belt category
            Inserter, FilterInserter, BurnerInserter,  # Inserter category
            ElectricalProducer, ElectricityPole, Accumulator, Generator, ElectricityGroup,  # Power category
            FluidHandler, MultiFluidHandler, Pipe, PipeGroup, OffshorePump, Pump, StorageTank, Boiler,  # Fluid category
            AssemblingMachine, AdvancedAssemblingMachine, ChemicalPlant, OilRefinery, Furnace, ElectricFurnace, Lab,
            RocketSilo,  # Production category
            Chest,  # Logistics category
            GunTurret, WallGroup,  # Defense category
            MiningDrill, ElectricMiningDrill, BurnerMiningDrill, PumpJack,  # Mining category
        )

        # Resource types have a primitive prototype without a complex class hierarchy
        if hasattr(entity, 'prototype') and entity.prototype is not None:
            proto_name = entity.prototype.value[0] if hasattr(entity.prototype, 'value') else ''
            if any(resource in proto_name for resource in ['ore', 'coal', 'stone', 'crude-oil']):
                return "resource"

        # Check for belt related entities
        if isinstance(entity, (TransportBelt, Splitter, UndergroundBelt, BeltGroup)):
            return "belt"

        # Check for inserters
        if isinstance(entity, (Inserter, FilterInserter, BurnerInserter)):
            return "inserter"

        # Check for power related entities
        if isinstance(entity, (ElectricalProducer, ElectricityPole, Accumulator, Generator, ElectricityGroup)):
            return "power"

        # Check for fluid handling entities
        if isinstance(entity,
                      (FluidHandler, MultiFluidHandler, Pipe, PipeGroup, OffshorePump, Pump, StorageTank, Boiler)):
            return "fluid"

        # Check for production entities
        if isinstance(entity, (AssemblingMachine, AdvancedAssemblingMachine, ChemicalPlant, OilRefinery,
                               Furnace, ElectricFurnace, Lab, RocketSilo)):
            return "production"

        # Check for logistics entities
        if isinstance(entity, Chest):
            return "logistics"

        # Check for defense entities
        if isinstance(entity, (GunTurret, WallGroup)):
            return "defense"

        # Check for mining entities
        if isinstance(entity, (MiningDrill, ElectricMiningDrill, BurnerMiningDrill, PumpJack)):
            return "mining"

        # Default - use the class name to derive a category
        class_name = type(entity).__name__
        return class_name.lower()