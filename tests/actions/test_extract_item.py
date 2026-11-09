import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "iron-chest": 1,
            "iron-plate": 10,
            "assembling-machine-1": 1,
            "copper-cable": 3,
            "lab": 1,
            "automation-science-pack": 5,
        }
    )


def test_extract(game):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, quantity=10)
    count = game.extract_item(Prototype.IronPlate, chest.position, quantity=2)
    assert game.inspect_inventory()[Prototype.IronPlate] == 2
    assert count == 2


def test_extract_more_than_available(game):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, quantity=10)
    count = game.extract_item(Prototype.IronPlate, chest, quantity=50)
    assert count == 10
    assert game.inspect_inventory()[Prototype.IronPlate] == 10
    assert game.inspect_inventory(chest).get(Prototype.IronPlate, 0) == 0


# Total durability of automation science packs: in the lab, and in the character
total_pack_durability = """
local function total(inv)
    local t = 0
    for i = 1, #inv do
        local s = inv[i]
        if s.valid_for_read and s.name == "automation-science-pack" then
            t = t + (s.count - 1) + s.durability
        end
    end
    return t
end
local lab = game.surfaces[1].find_entities_filtered{name = "lab"}[1]
rcon.print(string.format("%.2f %.2f",
    total(lab.get_inventory(defines.inventory.lab_input)),
    total(storage.agent_characters[1].get_main_inventory())))
"""

part_use_lab_pack = """
local lab = game.surfaces[1].find_entities_filtered{name = "lab"}[1]
lab.get_inventory(defines.inventory.lab_input).find_item_stack("automation-science-pack").durability = 0.3
"""


def test_extract_part_used_science_pack(game):
    instance = game.instance
    lab = game.place_entity(Prototype.Lab, position=Position(x=0, y=0))
    game.insert_item(Prototype.AutomationSciencePack, lab, quantity=5)
    instance.rcon_client.send_command(f"/sc {part_use_lab_pack}")
    before = instance.rcon_client.send_command(f"/sc {total_pack_durability}")
    assert before.split() == ["4.30", "0.00"]

    count = game.extract_item(Prototype.AutomationSciencePack, lab, quantity=5)
    assert count == 5

    # The part-used pack keeps its durability: no research is created
    after = instance.rcon_client.send_command(f"/sc {total_pack_durability}")
    assert after.split() == ["0.00", "4.30"]


def test_extract_assembler_multi(game):
    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(assembler, Prototype.ElectronicCircuit)
    game.insert_item(Prototype.IronPlate, assembler, quantity=10)
    game.insert_item(Prototype.CopperCable, assembler, quantity=3)
    inventory = game.inspect_inventory(assembler)
    assert inventory[Prototype.IronPlate] == 10
    assert inventory[Prototype.CopperCable] == 3

    count1 = game.extract_item(Prototype.IronPlate, assembler, quantity=2)
    count2 = game.extract_item(Prototype.CopperCable, assembler, quantity=2)
    assert game.inspect_inventory()[Prototype.IronPlate] == 2
    assert game.inspect_inventory()[Prototype.CopperCable] == 2
    assert count1 == 2 and count2 == 2
