from factorio_instance import *
def test_craft_and_place_burner_inserters_for_furnace_automation():
    # Check if 3 burner inserters have been crafted and placed
    inserters = inspect_entities(radius=20)
    burner_inserters = [entity for entity in inserters if entity['name'] == 'burner-inserter']
    
    if len(burner_inserters) < 3:
        print(f"Not enough burner inserters placed. Found {len(burner_inserters)}, expected at least 3.")
        return False
    
    # Check if there are at least 3 stone furnaces
    furnaces = [entity for entity in inserters if entity['name'] == 'stone-furnace']
    if len(furnaces) < 3:
        print(f"Not enough stone furnaces found. Found {len(furnaces)}, expected at least 3.")
        return False
    
    # Check if burner inserters are correctly positioned next to furnaces
    correctly_positioned = 0
    for inserter in burner_inserters:
        for furnace in furnaces:
            if abs(inserter['position']['x'] - furnace['position']['x']) <= 1 and \
               abs(inserter['position']['y'] - furnace['position']['y']) <= 1:
                correctly_positioned += 1
                break
    
    if correctly_positioned < 3:
        print(f"Not all burner inserters are correctly positioned next to furnaces. Found {correctly_positioned} correctly positioned, expected at least 3.")
        return False
    
    # Check if there's a coal supply nearby
    coal_supply = False
    for entity in inserters:
        if entity['name'] in ['wooden-chest', 'iron-chest'] or entity['name'] == 'coal':
            for inserter in burner_inserters:
                if abs(entity['position']['x'] - inserter['position']['x']) <= 3 and \
                   abs(entity['position']['y'] - inserter['position']['y']) <= 3:
                    coal_supply = True
                    break
            if coal_supply:
                break
    
    if not coal_supply:
        print("No coal supply found near the burner inserters.")
        return False
    
    print("Objective complete! 3 burner inserters have been crafted and placed correctly to automate fuel loading for furnaces.")
    return True
