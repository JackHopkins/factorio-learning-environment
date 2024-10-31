import os


def load_schema(folder_path: str) -> str:
    entity_operations = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                entity_operations.append(file[:-3])
    return entity_operations