"""Compact public API reference injected into model-facing task prompts."""

ACTION_PROFILE_REFERENCE = """\
Inside factorio_execute_program, write ordinary short Python using only the
public FLE API (no host/file/network access). Useful operations:
- inspect_inventory(entity=None), get_entities(set(), position=None, radius=1000)
- nearest(Prototype.X or Resource.X), move_to(Position), harvest_resource(Position, quantity)
- get_prototype_recipe(Prototype.X), craft_item(Prototype.X, quantity)
- place_entity(Prototype.X, direction=Direction.UP, position=Position(x, y))
- place_entity_next_to(Prototype.X, reference_position, direction, spacing=0)
- can_place_entity(...), get_entity(...), pickup_entity(...), rotate_entity(...)
- insert_item(Prototype.X, target, quantity), extract_item(Prototype.X, source, quantity)
- set_entity_recipe(entity, Prototype.X or RecipeName.X)
- connect_entities(source, target, Prototype.TransportBelt/Pipe/SmallElectricPole)
- get_resource_patch(Resource.X, position, radius), nearest_buildable(...)
- set_research(Technology.X), get_research_progress(Technology.X)
- sleep(seconds) (at most 15 seconds per call), print(...) for measured feedback

Names use enums such as Prototype.IronPlate, Resource.IronOre, Technology.Automation,
Direction.UP, and Position(x, y). Inspect recipes, inventories, entities, status,
and production before assuming a plan worked. Re-fetch entities after the world
changes because returned entity objects can become stale. Entity values use
attributes such as entity.name and entity.position, not dictionary indexing.

The character can normally act only within about 10 tiles. Call move_to(target)
before harvesting or placing at a distant target. Use the supplied starting
inventory before mining or crafting, and do not build production chains that
the stated objective does not require.
"""
