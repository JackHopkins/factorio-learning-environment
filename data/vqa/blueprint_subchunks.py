# Add this to blueprint_transforms.py or create a new file blueprint_subchunks.py

import copy
import math
from typing import Dict, Any, Tuple
from typing import List

from inspect_ai.dataset import Dataset, Sample, MemoryDataset

from data.vqa.blueprint_transforms import get_blueprint_bounds


class SubchunkConfig:
    """Configuration for subchunk extraction."""

    def __init__(
        self,
        chunk_size: Tuple[int, int],
        step_size: Tuple[int, int],
        min_entities: int = 3,
        padding: float = 1.0,
    ):
        """
        Args:
            chunk_size: (width, height) of each chunk
            step_size: (x_step, y_step) for sliding window
            min_entities: Minimum entities required in a chunk to keep it
            padding: Extra padding around chunk boundaries
        """
        self.chunk_size = chunk_size
        self.step_size = step_size
        self.min_entities = min_entities
        self.padding = padding


def get_entities_in_region(
    entities: List[Dict[str, Any]],
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> List[Dict[str, Any]]:
    """
    Get all entities within a rectangular region.

    Args:
        entities: List of blueprint entities
        min_x, min_y, max_x, max_y: Region boundaries

    Returns:
        List of entities within the region
    """
    entities_in_region = []

    for entity in entities:
        pos = entity.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)

        if min_x <= x <= max_x and min_y <= y <= max_y:
            entities_in_region.append(entity)

    return entities_in_region


def extract_subchunk(
    blueprint: Dict[str, Any],
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    normalize: bool = True,
) -> Dict[str, Any]:
    """
    Extract a subchunk from a blueprint.

    Args:
        blueprint: Original blueprint
        min_x, min_y, max_x, max_y: Chunk boundaries
        normalize: Whether to normalize positions to start near (0, 0)

    Returns:
        New blueprint containing only entities in the chunk
    """
    chunk_blueprint = copy.deepcopy(blueprint)

    # Get entities in the region
    original_entities = blueprint.get("entities", [])
    chunk_entities = get_entities_in_region(
        original_entities, min_x, min_y, max_x, max_y
    )

    if normalize:
        # Normalize positions so chunk starts near (0, 0)
        normalized_entities = []
        for entity in chunk_entities:
            new_entity = copy.deepcopy(entity)
            pos = new_entity.get("position", {})
            new_entity["position"] = {
                "x": pos.get("x", 0) - min_x,
                "y": pos.get("y", 0) - min_y,
            }
            normalized_entities.append(new_entity)
        chunk_entities = normalized_entities

    chunk_blueprint["entities"] = chunk_entities

    # Update metadata
    if "metadata" not in chunk_blueprint:
        chunk_blueprint["metadata"] = {}

    chunk_blueprint["metadata"]["subchunk"] = {
        "original_bounds": {
            "min_x": min_x,
            "min_y": min_y,
            "max_x": max_x,
            "max_y": max_y,
        },
        "chunk_size": {"width": max_x - min_x, "height": max_y - min_y},
        "entity_count": len(chunk_entities),
        "normalized": normalize,
    }

    # Update label if present
    if "label" in chunk_blueprint:
        chunk_blueprint["label"] = f"{chunk_blueprint['label']} (chunk)"

    return chunk_blueprint


def generate_subchunks(
    blueprint: Dict[str, Any], config: SubchunkConfig
) -> List[Dict[str, Any]]:
    """
    Generate all subchunks from a blueprint using sliding window.

    Args:
        blueprint: Original blueprint
        config: Subchunk configuration

    Returns:
        List of subchunk blueprints
    """
    entities = blueprint.get("entities", [])
    if not entities:
        return []

    # Get blueprint bounds
    min_x, min_y, max_x, max_y = get_blueprint_bounds(entities)

    # Calculate blueprint dimensions

    chunk_width, chunk_height = config.chunk_size
    step_x, step_y = config.step_size

    subchunks = []

    # Generate chunks using sliding window
    y = min_y
    chunk_id = 0

    while y + chunk_height <= max_y + config.padding:
        x = min_x
        while x + chunk_width <= max_x + config.padding:
            # Extract chunk
            chunk_min_x = x - config.padding
            chunk_min_y = y - config.padding
            chunk_max_x = x + chunk_width + config.padding
            chunk_max_y = y + chunk_height + config.padding

            chunk = extract_subchunk(
                blueprint,
                chunk_min_x,
                chunk_min_y,
                chunk_max_x,
                chunk_max_y,
                normalize=True,
            )

            # Only keep chunks with enough entities
            if len(chunk["entities"]) >= config.min_entities:
                # Add chunk position info
                chunk["metadata"]["subchunk"]["id"] = chunk_id
                chunk["metadata"]["subchunk"]["grid_position"] = {
                    "x": int((x - min_x) / step_x),
                    "y": int((y - min_y) / step_y),
                }
                subchunks.append(chunk)
                chunk_id += 1

            x += step_x
        y += step_y

    return subchunks


def create_subchunk_augmented_dataset(
    base_dataset: Dataset,
    chunk_sizes: List[Tuple[int, int]] = None,
    step_sizes: List[Tuple[int, int]] = None,
    min_entities: int = 3,
) -> MemoryDataset:
    """
    Create a subchunk-augmented dataset from a base dataset.

    Args:
        base_dataset: The original dataset
        chunk_sizes: List of (width, height) tuples for chunk sizes
        step_sizes: List of (x_step, y_step) tuples for step sizes
        min_entities: Minimum entities required in a chunk

    Returns:
        MemoryDataset with subchunk variations
    """
    if chunk_sizes is None:
        chunk_sizes = [(10, 10), (15, 15), (20, 20)]

    if step_sizes is None:
        step_sizes = [(5, 5), (10, 10)]

    augmented_samples = []

    for original_sample in base_dataset:
        blueprint = original_sample.metadata.get("blueprint", {})

        if not blueprint:
            augmented_samples.append(original_sample)
            continue

        # Add original
        augmented_samples.append(original_sample)

        # Generate subchunks for each configuration
        for chunk_size in chunk_sizes:
            for step_size in step_sizes:
                config = SubchunkConfig(
                    chunk_size=chunk_size,
                    step_size=step_size,
                    min_entities=min_entities,
                )

                subchunks = generate_subchunks(blueprint, config)

                for i, chunk_blueprint in enumerate(subchunks):
                    # Create new sample
                    new_metadata = copy.deepcopy(original_sample.metadata)
                    new_metadata["blueprint"] = chunk_blueprint
                    new_metadata["original_filename"] = original_sample.metadata.get(
                        "filename", ""
                    )
                    new_metadata["augmentation_type"] = "subchunk"
                    new_metadata["chunk_config"] = {
                        "chunk_size": chunk_size,
                        "step_size": step_size,
                        "chunk_index": i,
                        "total_chunks": len(subchunks),
                    }

                    # Create unique ID
                    chunk_suffix = f"chunk_{chunk_size[0]}x{chunk_size[1]}_step_{step_size[0]}x{step_size[1]}_{i}"

                    new_sample = Sample(
                        input=original_sample.input,
                        target=original_sample.target,
                        metadata=new_metadata,
                        id=f"{original_sample.id}_{chunk_suffix}"
                        if original_sample.id
                        else None,
                        files=original_sample.files,
                    )

                    augmented_samples.append(new_sample)

    return MemoryDataset(samples=augmented_samples)


def create_overlapping_subchunks(
    blueprint: Dict[str, Any], chunk_size: Tuple[int, int], overlap: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Create overlapping subchunks with specified overlap ratio.

    Args:
        blueprint: Original blueprint
        chunk_size: (width, height) of each chunk
        overlap: Overlap ratio (0.5 = 50% overlap)

    Returns:
        List of overlapping subchunk blueprints
    """
    chunk_width, chunk_height = chunk_size
    step_x = int(chunk_width * (1 - overlap))
    step_y = int(chunk_height * (1 - overlap))

    config = SubchunkConfig(
        chunk_size=chunk_size, step_size=(step_x, step_y), min_entities=3
    )

    return generate_subchunks(blueprint, config)


def create_adaptive_subchunks(
    blueprint: Dict[str, Any], target_entities_per_chunk: int = 20, max_chunks: int = 10
) -> List[Dict[str, Any]]:
    """
    Create subchunks with adaptive sizing based on entity density.

    Args:
        blueprint: Original blueprint
        target_entities_per_chunk: Target number of entities per chunk
        max_chunks: Maximum number of chunks to generate

    Returns:
        List of adaptively-sized subchunk blueprints
    """
    entities = blueprint.get("entities", [])
    if not entities:
        return []

    total_entities = len(entities)

    # Calculate ideal chunk count
    ideal_chunks = min(max_chunks, max(1, total_entities // target_entities_per_chunk))

    # Get blueprint bounds
    min_x, min_y, max_x, max_y = get_blueprint_bounds(entities)
    blueprint_width = max_x - min_x
    blueprint_height = max_y - min_y

    # Calculate chunk dimensions
    chunks_per_side = int(math.sqrt(ideal_chunks))
    chunk_width = int(blueprint_width / chunks_per_side)
    chunk_height = int(blueprint_height / chunks_per_side)

    config = SubchunkConfig(
        chunk_size=(chunk_width, chunk_height),
        step_size=(chunk_width, chunk_height),
        min_entities=3,
    )

    return generate_subchunks(blueprint, config)
