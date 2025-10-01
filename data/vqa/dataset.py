import copy
import json
from typing import List

from inspect_ai.dataset import MemoryDataset, Sample

from data.vqa.blueprint_subchunks import SubchunkConfig, generate_subchunks
from data.vqa.utils import find_blueprints_dir

from inspect_ai.dataset import Dataset
from data.vqa.blueprint_transforms import (
    generate_flipped_blueprints,
    update_metadata_for_flip,
    FlipType,
    detect_direction_system,
)


def create_flip_augmented_dataset(
    base_dataset: Dataset, include_flips: List[str] = None
) -> MemoryDataset:
    """
    Create a flip-augmented dataset from a base dataset.

    Args:
        base_dataset: The original dataset
        include_flips: List of flip type names to include (e.g., ["none", "horizontal", "vertical", "both"])
                      If None, includes all flip types

    Returns:
        MemoryDataset with flipped variations
    """
    if include_flips is None:
        flip_types = list(FlipType)
    else:
        flip_map = {f.value: f for f in FlipType}
        # Also support shorthand names
        shorthand_map = {
            "h": FlipType.HORIZONTAL,
            "v": FlipType.VERTICAL,
            "hv": FlipType.BOTH,
            "original": FlipType.NONE,
            "h_flip": FlipType.HORIZONTAL,
            "v_flip": FlipType.VERTICAL,
            "hv_flip": FlipType.BOTH,
        }

        flip_types = []
        for name in include_flips:
            name_lower = name.lower()
            if name_lower in flip_map:
                flip_types.append(flip_map[name_lower])
            elif name_lower in shorthand_map:
                flip_types.append(shorthand_map[name_lower])

    augmented_samples = []

    for original_sample in base_dataset:
        blueprint = original_sample.metadata.get("blueprint", {})

        if not blueprint:
            # If no blueprint, just keep original
            augmented_samples.append(original_sample)
            continue

        # Detect direction system for this blueprint
        direction_system = detect_direction_system(blueprint)

        # Generate flipped blueprints
        flipped_blueprints = generate_flipped_blueprints(blueprint, direction_system)

        for flip_type in flip_types:
            flipped_blueprint = flipped_blueprints[flip_type]

            # Create new sample with flipped blueprint
            new_metadata = update_metadata_for_flip(
                original_sample.metadata, flip_type, direction_system
            )
            new_metadata["blueprint"] = flipped_blueprint
            new_metadata["original_filename"] = original_sample.metadata.get(
                "filename", ""
            )

            # Create unique ID for the flipped sample
            flip_suffix = {
                FlipType.NONE: "original",
                FlipType.HORIZONTAL: "h_flip",
                FlipType.VERTICAL: "v_flip",
                FlipType.BOTH: "hv_flip",
            }[flip_type]

            new_sample = Sample(
                input=original_sample.input,
                target=original_sample.target,
                metadata=new_metadata,
                id=f"{original_sample.id}_{flip_suffix}"
                if original_sample.id
                else None,
                files=original_sample.files,
            )

            augmented_samples.append(new_sample)

    return MemoryDataset(samples=augmented_samples)


def create_single_flip_dataset(base_dataset: Dataset, flip: str) -> MemoryDataset:
    """
    Create a dataset with only a single flip type applied.

    Args:
        base_dataset: The original dataset
        flip: Flip type name ("none", "horizontal", "vertical", "both")
              or shorthand ("h", "v", "hv", "original")

    Returns:
        MemoryDataset with single flip type
    """
    return create_flip_augmented_dataset(base_dataset, [flip])


def create_all_flips_dataset(base_dataset: Dataset) -> MemoryDataset:
    """
    Create a dataset with all possible flips (4x augmentation).

    Args:
        base_dataset: The original dataset

    Returns:
        MemoryDataset with all flip variations
    """
    return create_flip_augmented_dataset(base_dataset, None)


def raw_test_dataset() -> MemoryDataset:
    blueprint = {
        "icons": [{"signal": {"type": "item", "name": "transport-belt"}, "index": 1}],
        "entities": [
            {
                "name": "transport-belt",
                "position": {"x": -0.5, "y": -0.5},
                "direction": 12,
                "entity_number": 1,
            },
            {
                "name": "transport-belt",
                "position": {"x": 0.5, "y": -0.5},
                "direction": 8,
                "entity_number": 1,
            },
        ],
        "item": "blueprint",
        "version": 281479274299391,
        "label": "Blueprint",
    }
    dataset = MemoryDataset(
        samples=[
            Sample(
                input="dummpy",
                metadata={"filename": "dummy", "blueprint": blueprint},
            )
        ]
    )
    return dataset


def raw_blueprint_dataset() -> MemoryDataset:
    # Load blueprints from directory
    blueprint_dir = find_blueprints_dir()
    samples = []

    for blueprint_path in blueprint_dir.glob("*.json"):
        with open(blueprint_path, "r") as f:
            blueprint_json = f.read()

        blueprint = json.loads(blueprint_json)
        sample = Sample(
            input=blueprint["label"] if "label" in blueprint else blueprint_path.name,
            metadata={"filename": blueprint_path.name, "blueprint": blueprint},
        )
        samples.append(sample)

    # Create dataset
    dataset = MemoryDataset(samples=samples)
    return dataset


def augmented_blueprint_dataset() -> MemoryDataset:
    """
    Create an augmented blueprint dataset with rotations.

    Args:
        rotations: List of rotation names to include (e.g., ["north", "east"])
                  If None, includes all 4 rotations

    Returns:
        MemoryDataset with rotated blueprint variations
    """
    base_dataset = raw_blueprint_dataset()
    return create_all_flips_dataset(base_dataset)


def create_combined_augmented_dataset(
    base_dataset: Dataset,
    include_flips: List[str] = None,
    chunk_configs: List[SubchunkConfig] = None,
) -> MemoryDataset:
    """
    Create a dataset with both flip and subchunk augmentations.

    Args:
        base_dataset: The original dataset
        include_flips: List of flip types to include
        chunk_configs: List of SubchunkConfig objects

    Returns:
        MemoryDataset with combined augmentations
    """
    # First apply flip augmentation
    flip_augmented = create_flip_augmented_dataset(base_dataset, include_flips)

    # Then apply subchunk augmentation to the flipped dataset
    if chunk_configs is None:
        chunk_configs = [
            SubchunkConfig((10, 10), (5, 5)),
            SubchunkConfig((15, 15), (10, 10)),
            SubchunkConfig((20, 20), (10, 10)),
        ]

    augmented_samples = []

    for sample in flip_augmented:
        blueprint = sample.metadata.get("blueprint", {})

        if not blueprint:
            augmented_samples.append(sample)
            continue

        # Add the full blueprint
        augmented_samples.append(sample)

        # Generate subchunks for each config
        for config in chunk_configs:
            subchunks = generate_subchunks(blueprint, config)

            for i, chunk_blueprint in enumerate(subchunks):
                # Create new sample with combined metadata
                new_metadata = copy.deepcopy(sample.metadata)
                new_metadata["blueprint"] = chunk_blueprint
                new_metadata["augmentation_type"] = "combined"
                new_metadata["subchunk_config"] = {
                    "chunk_size": config.chunk_size,
                    "step_size": config.step_size,
                    "chunk_index": i,
                }

                # Create unique ID
                flip_part = sample.metadata.get("flip_suffix", "original")
                chunk_part = f"chunk_{config.chunk_size[0]}x{config.chunk_size[1]}_{i}"

                new_sample = Sample(
                    input=sample.input,
                    target=sample.target,
                    metadata=new_metadata,
                    id=f"{sample.input}_{chunk_part}_{flip_part}",
                    files=sample.files,
                )
                print(new_sample.id)

                augmented_samples.append(new_sample)

    return MemoryDataset(samples=augmented_samples)


def augmented_blueprint_dataset_with_chunks() -> MemoryDataset:
    """
    Create an augmented blueprint dataset with both rotations and subchunks.
    """
    base_dataset = raw_blueprint_dataset()
    # base_dataset.samples = base_dataset.samples[0]]
    # Define chunk configurations
    chunk_configs = [
        # SubchunkConfig((10, 10), (5, 5), min_entities=5),
        # SubchunkConfig((15, 15), (7, 7), min_entities=8),
        SubchunkConfig((20, 20), (10, 10), min_entities=10)
    ]

    return create_combined_augmented_dataset(
        base_dataset,
        include_flips=["none", "horizontal", "vertical", "both"],
        chunk_configs=chunk_configs,
    )
