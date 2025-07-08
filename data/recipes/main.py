import json
from slpp import slpp as lua


# Convert Lua table to Python dictionary
def lua_table_to_dict(lua_table):
    if not isinstance(lua_table, (dict, list)):
        return lua_table
    if isinstance(lua_table, list):
        return [lua_table_to_dict(v) for v in lua_table]
    return {k: lua_table_to_dict(v) for k, v in lua_table.items()}


# Create a dictionary of all recipes
recipes = []
recipe_dict = {}
with open("recipes.lua", "r") as luafile:
    # Parse the Lua data
    data = luafile.read()
    recipes = lua.decode(data)


for recipe in recipes:
    recipe_name = recipe[0]
    recipe_ingredients = recipe[1]
    recipe_dict[recipe_name] = recipe_ingredients


# Function to build the nested ingredient tree
def build_ingredient_tree(recipe_name, graph, visited=None):
    if visited is None:
        visited = set()
    if recipe_name not in graph:
        return {"name": recipe_name, "ingredients": []}
    if recipe_name in visited:
        return {
            "name": recipe_name,
            "ingredients": [],
        }  # Handle cycles or already visited

    visited.add(recipe_name)
    recipe = graph[recipe_name]
    ingredient_tree = {"name": recipe_name, "ingredients": []}

    for ingredient in recipe:
        sub_tree = build_ingredient_tree(ingredient["name"], graph, visited)
        sub_tree["amount"] = ingredient["amount"]
        sub_tree["type"] = ingredient["type"]
        ingredient_tree["ingredients"].append(sub_tree)

    visited.remove(recipe_name)
    return ingredient_tree


# Create the DAG of recipes
graph = {}
for recipe_name, recipe_data in recipe_dict.items():
    graph[recipe_name] = recipe_data[0]

# Create and write the JSONL file
with open("recipes.jsonl", "w") as outfile:
    for recipe_name in graph.keys():
        nested_tree = build_ingredient_tree(recipe_name, graph)
        json_line = json.dumps(nested_tree)
        outfile.write(json_line + "\n")

# Print the content of the JSONL file
with open("recipes.jsonl", "r") as infile:
    for line in infile:
        print(line)
