import os


def extract_skills_from_test(test_file):
    # split by \ndef 
    test_files = test_file.split("\ndef ")[1:]
    # get the initial inv from first one
    game_def = test_files[0]
    if "instance.initial_inventory" not in game_def:
        initial_inv = {}
    else:
        # get the index of the initial inv
        initial_inv_index = game_def.index("instance.initial_inventory")
        # get the first { after the initial inv
        initial_inv_start = game_def.index("{", initial_inv_index)
        # get the last } after the initial inv
        initial_inv_end = game_def.index("}", initial_inv_start)
        # get the initial inv
        initial_inv = game_def[initial_inv_start:initial_inv_end + 1]
        initial_inv = initial_inv.replace(" ", "").replace("\n", "")
        # make it a dict
        initial_inv = eval(initial_inv)
    skills = []
    skill_defs = test_files[1:]
    for skill_def in skill_defs:
        function_parts = skill_def.split("\n")
        function_name = function_parts[0]
        function_name = function_name.split("(")[0]
        function_parts = function_parts[1:]
        for part_idx, function_part in enumerate(function_parts):
            if "    " not in function_part:
                continue
            function_part.replace("game.", "")
            function_part = function_part[4:]
            function_parts[part_idx] = function_part
        function_parts = "\n".join(function_parts)
        skills.append(function_parts)
    return skills


def get_skills_from_func_tests(func_test_folder):
    """
    Get the skills from the functional tests.
    :param func_test_folder: The folder containing the functional tests.
    :return: A list of skills.
    """
    skills = []
    for file in os.listdir(func_test_folder):
        if file.endswith(".py"):
            with open(os.path.join(func_test_folder, file)) as f:
                content = f.read()
                skills += extract_skills_from_test(content)

    return skills

if __name__ == "__main__":
    folder_path = r"tests\functional"
    skills = get_skills_from_func_tests(folder_path)