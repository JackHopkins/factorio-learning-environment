import json

from inspect_ai.dataset import MemoryDataset, Sample

from data.vqa.utils import find_blueprints_dir

def raw_blueprint_dataset() -> MemoryDataset:
    # Load blueprints from directory
    blueprint_dir = find_blueprints_dir()
    samples = []

    for blueprint_path in blueprint_dir.glob("*.json"):
        with open(blueprint_path, 'r') as f:
            blueprint_json = f.read()

        blueprint = json.loads(blueprint_json)
        sample = Sample(
            input=blueprint['label'] if 'label' in blueprint else blueprint_path.name,
            metadata={"filename": blueprint_path.name, "blueprint": blueprint},
        )
        samples.append(sample)

    # Create dataset
    dataset = MemoryDataset(samples=samples)
    return dataset