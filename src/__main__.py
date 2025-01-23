import os
import random
import time
from glob import glob
from pathlib import Path
from typing import List
from timeit import default_timer as timer
from rcon import factorio_rcon
from itertools import chain

from dotenv import load_dotenv

load_dotenv()

try:
    client = factorio_rcon.RCONClient('localhost', 27000, "factorio")
    print("Connected to local client.")
except:
    client = factorio_rcon.RCONClient(os.getenv("REMOTE_ADDRESS"), 27000, "eSei2keed0aegai")
    print("Connected to remote client.")

character = "players[1]"


def load_scripts(directory: str):
    script_dict = {}
    script_files = list(chain.from_iterable(glob(os.path.join(x[0], '*.lua')) for x in os.walk(directory)))
    for filename in script_files:
        with open(filename, "r") as file:
            script_string = "".join(file.readlines())
            pruned = Path(filename).name[:-4]
            script_dict[pruned] = script_string
    return script_dict


script_dict = {**load_scripts('actions'), **load_scripts('init')}


def get_command(file, parameters=[], measured=True):
    prefix = "/c " if not measured else '/measured-command '
    script = prefix + script_dict[file]
    for index in range(len(parameters)):
        script = script.replace(f"arg{index + 1}", str(parameters[index]))

    return script


def execute_script(command, parameters=[], measured=False) -> List[str]:
    script = get_command(command, parameters=parameters, measured=measured)
    start = timer()
    response = client.send_command(script)
    print("\n")
    print(command, parameters, response)
    if response:
        return response.split("\n")
    end = timer()
    diff = (end - start)
    return response, diff


# response = client.send_command(get_command('give_item', parameters=["iron-plate", 1000]))
# send('prototypes/fatcontroller')
# send('clear_map', parameters=[100])

player_name = '1'  # '\"noddybear\"'

# send('players1', parameters=[player_name])
# send('inventory', parameters=[player_name])

# send('create_character', parameters=['2'])
# send('get_associated_characters', parameters=[player_name])
# send('remove_cliffs')
# send('teleport', parameters=[player_name, 10, 20])
# send('reveal_map', parameters=[player_name])
# send('day_time', parameters=[player_name])


start = timer()
x, y = random.randrange(1, 100), random.randrange(1, 100)
cardinals = ['north', 'south', 'east', 'west']

execute_script('set_controller', parameters=[player_name, 'god'])
execute_script('give_item', parameters=[player_name, 'iron-chest', 100])

exit(0)

for i in range(1000):
    direction = cardinals[random.randrange(1, len(cardinals))]
    if random.randrange(1, 100) < 50:
        execute_script('move', parameters=[player_name, direction, 'true'])
        execute_script('move', parameters=[player_name, direction, 'false'])
    # count_all = send('count_all', parameters=[player_name])
    #execute_script('give_item', parameters=[player_name, 'coal', 10])
    #execute_script('give_item', parameters=[player_name, 'stone', 10])
    #execute_script('give_item', parameters=[player_name, 'iron-plate', 10])
    count = execute_script('count', parameters=[player_name, 'coal'])
    print(count)
    # time.sleep(1)

execute_script('reset')
execute_script('random_map', parameters=[player_name, 50, 30])
# send('teleport', parameters=[player_name, x, y])
# send('create_ore', parameters=[player_name, 10, 10, "coal"])
# send('give_item', parameters=[player_name, 'iron-plate', 10])


# send('create_ore', parameters=[1])
# send('count_entities', parameters=[1, 'iron-plate'])
# send('give_item', parameters=['iron-plate', 10])
# send('count', parameters=['noddybear', 'iron-plate'])
# send('position', parameters=[player_name])
# send('count', parameters=[1, 'iron-plate'])
# send('clear_map', parameters=["noddybear", 100])
# send('give_item', parameters=[player_name, "iron-plate", 1000])
# send('give_item', parameters=["dummy1", "iron-plate", 1000])
# send('random_map', parameters=[50, 10])


# response = client.send_command(get_command('random_map', parameters=[50, 10]))
# response = client.send_command(get_command('random_map', parameters=["iron-plate"]))
