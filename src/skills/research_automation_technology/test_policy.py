from factorio_instance import *
from factorio_instance import *
from controllers import *
def test_research_automation_technology():
    # Check if a lab exists
    lab_position = nearest(Prototype.Lab)
    if lab_position is None:
        print("No lab found. Research cannot be conducted.")
        return False

    lab = get_entity(Prototype.Lab, lab_position)
    if lab is None:
        print("Failed to get lab entity.")
        return False

    # Check if the lab has power
    if not lab.is_powered():
        print("Lab is not powered. Research cannot be conducted.")
        return False

    # Check if red science packs are in the lab
    lab_inventory = inspect_inventory(lab)
    if Prototype.AutomationSciencePack not in lab_inventory or lab_inventory[Prototype.AutomationSciencePack] == 0:
        print("No Automation Science Packs found in the lab.")
        return False

    # Check if the Automation technology has been researched
    player_force = get_player_force()
    if player_force.technologies["automation"].researched:
        print("Automation technology has been successfully researched!")
        return True
    else:
        print("Automation technology has not been researched yet.")
        return False

    # Note: The following functions are assumed to exist in the game API:
    # - get_player_force(): Returns the player's force object
    # - force.technologies: A dictionary-like object containing all technologies
    # - technology.researched: A boolean indicating if the technology has been researched
