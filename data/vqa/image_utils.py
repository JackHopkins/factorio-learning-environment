"""Image utilities for VQA tasks - supports both blueprints and game maps."""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional
from datetime import datetime
from fle.commons.models.rendered_image import RenderedImage
from dotenv import load_dotenv

load_dotenv()


def get_blueprint_name(blueprint: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Get a clean blueprint name for folder structure.

    Args:
        blueprint: Blueprint dictionary
        metadata: Metadata containing filename

    Returns:
        Clean blueprint name suitable for folder name
    """
    # Try to get label first, then fall back to filename
    if "label" in blueprint and blueprint["label"]:
        name = blueprint["label"]
    else:
        # Get filename without extension
        filename = metadata.get("filename", "unknown")
        name = Path(filename).stem

    # Clean the name for filesystem use
    # Remove/replace problematic characters
    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    # Ensure it's not empty and not too long
    if not clean_name or clean_name == "_":
        clean_name = "unknown"

    # Limit length to prevent filesystem issues
    if len(clean_name) > 50:
        clean_name = clean_name[:50]

    return clean_name


def get_map_name(metadata: Dict[str, Any]) -> str:
    """
    Get a clean name for game map folder structure.

    Args:
        metadata: Metadata containing map information

    Returns:
        Clean map name suitable for folder name
    """
    # Try different naming strategies for maps
    if "map_name" in metadata and metadata["map_name"]:
        name = metadata["map_name"]
    elif "location" in metadata and metadata["location"]:
        name = f"map_{metadata['location']}"
    elif "position" in metadata:
        pos = metadata["position"]
        if isinstance(pos, dict) and "x" in pos and "y" in pos:
            name = f"map_{int(pos['x'])}_{int(pos['y'])}"
        else:
            name = f"map_{str(pos).replace(',', '_').replace(' ', '')}"
    elif "x" in metadata and "y" in metadata:
        name = f"map_{int(metadata['x'])}_{int(metadata['y'])}"
    else:
        # Use timestamp as fallback
        name = f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Clean the name for filesystem use
    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    # Ensure it's not empty
    if not clean_name or clean_name == "_":
        clean_name = "map_unknown"

    # Limit length
    if len(clean_name) > 50:
        clean_name = clean_name[:50]

    return clean_name


def generate_variant_hash(
    content: Union[Dict[str, Any], None] = None,
    modification_info: str = "",
    metadata: Dict[str, Any] = None,
    is_map: bool = False,
) -> str:
    """
    Generate a hash representing this specific variant of the blueprint or map.

    Args:
        content: Blueprint dictionary or None for maps
        modification_info: Additional info about modifications (for denoising, etc.)
        metadata: Metadata that may contain rotation info, position, etc.
        is_map: Whether this is a game map render

    Returns:
        Short hash string for this variant
    """
    # Create a string representing this specific variant
    variant_components = []

    if is_map and metadata:
        # For maps, use position, radius, layers, etc.
        variant_components.extend(
            [
                "map_render",
                str(metadata.get("position", "")),
                str(metadata.get("radius", 64)),
                str(metadata.get("layers", "all")),
                str(metadata.get("include_status", False)),
                str(metadata.get("timestamp", "")),
            ]
        )
    elif content:
        # For blueprints
        variant_components.append(str(content))

    variant_components.append(modification_info)

    # Include rotation information if present
    if metadata:
        rotation = metadata.get("rotation", "")
        rotation_degrees = metadata.get("rotation_degrees", "")
        variant_components.extend([rotation, str(rotation_degrees)])

    variant_string = "|".join(variant_components)

    # Generate a shorter, more readable hash
    hash_object = hashlib.md5(variant_string.encode())
    return hash_object.hexdigest()[:12]  # Use first 12 characters


def generate_image_path_and_id(
    content: Union[Dict[str, Any], None] = None,
    metadata: Dict[str, Any] = None,
    modification_info: str = "",
    base_dir: str = "../../../dataset/images",
    is_map: bool = False,
) -> tuple[str, str]:
    """
    Generate the folder structure image path and ID for blueprints or maps.

    Args:
        content: Blueprint dictionary or None for maps
        metadata: Metadata containing filename or map info
        modification_info: Additional info for variants (denoising, etc.)
        base_dir: Base directory for images
        is_map: Whether this is a game map render

    Returns:
        Tuple of (file_path, image_id) where:
        - file_path: Full path where image should be saved
        - image_id: ID to use in metadata (relative path from base_dir)
    """
    if is_map:
        name = get_map_name(metadata or {})
        # Add "maps" subdirectory to separate from blueprints
        folder_path = Path(base_dir) / "maps"  # / name
    else:
        if not content:
            raise ValueError("Blueprint content required when is_map=False")
        name = get_blueprint_name(content, metadata or {})
        folder_path = Path(base_dir) / name

    variant_hash = generate_variant_hash(content, modification_info, metadata, is_map)

    # Add rotation/flip prefix to filename if present
    prefix = ""
    if metadata:
        if "flip_suffix" in metadata:
            prefix = metadata["flip_suffix"] + "_"
        elif is_map and "view_angle" in metadata:
            prefix = f"angle_{metadata['view_angle']}_"

    # Create the image ID (relative path from base_dir for metadata)
    if is_map:
        image_id = f"maps/{name}_{prefix}{variant_hash}"
    else:
        image_id = f"{name}_{prefix}{variant_hash}"

    # Create the full file path with PNG extension for lossless quality
    file_path = folder_path / f"{name}_{prefix}{variant_hash}.png"

    return str(file_path), image_id


# def save_rendered_image(image: RenderedImage,
#                        blueprint: Optional[Dict[str, Any]] = None,
#                        metadata: Optional[Dict[str, Any]] = None,
#                        modification_info: str = "",
#                        base_dir: str = "../../dataset/images",
#                        is_map: bool = False) -> str:
#     """
#     Save a rendered image using the folder structure for blueprints or maps.
#
#     Args:
#         image: RenderedImage to save
#         blueprint: Blueprint dictionary (None for maps)
#         metadata: Metadata containing filename or map info
#         modification_info: Additional info for variants (denoising, etc.)
#         base_dir: Base directory for images
#         is_map: Whether this is a game map render
#
#     Returns:
#         Image ID for use in metadata
#     """
#     # Validate inputs
#     if not is_map and blueprint is None:
#         raise ValueError("Blueprint required when is_map=False")
#
#     if is_map and metadata is None:
#         # Create minimal metadata for map
#         metadata = {"timestamp": datetime.now().isoformat()}
#
#     file_path, image_id = generate_image_path_and_id(
#         content=blueprint,
#         metadata=metadata or {},
#         modification_info=modification_info,
#         base_dir=base_dir,
#         is_map=is_map
#     )
#
#     # Create directory if it doesn't exist
#     Path(file_path).parent.mkdir(parents=True, exist_ok=True)
#
#     # Save the image
#     image.save(file_path)
#
#     return image_id


def save_rendered_image(
    image: RenderedImage,
    blueprint: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    modification_info: Optional[str] = None,
    base_dir: str = os.getenv("VQA_DATASET_DIR"),
    is_map: bool = False,
    is_factory: bool = False,
) -> str:
    """
    Save a rendered image with associated metadata and return its unique ID.

    Args:
        image: The RenderedImage object to save
        blueprint: Optional blueprint data if this is a blueprint image
        metadata: Optional metadata to save with the image
        modification_info: Optional modification info to distinguish denoising variants
        base_dir: Base directory for saving images
        is_map: If True, save in 'terrain' subdirectory
        is_factory: If True, save in 'factory' subdirectory

    Returns:
        Relative path to the image including subdirectory (e.g., "blueprints/abc123.png")
    """
    # Determine subdirectory based on image type
    if is_factory:
        subdirectory = "factory"
        # For factory images, use position as part of the identifier
        position = metadata.get("position", {"x": 0, "y": 0})
        base_identifier = f"factory_x{int(position['x'])}_y{int(position['y'])}"
    elif is_map:
        subdirectory = "terrain"
        # For terrain/map images, use position as part of the identifier
        position = metadata.get("position", {"x": 0, "y": 0})
        base_identifier = f"terrain_x{int(position['x'])}_y{int(position['y'])}"
    elif blueprint is not None:
        subdirectory = "blueprints"
        # For blueprint images, use blueprint hash
        blueprint_str = json.dumps(blueprint, sort_keys=True)
        base_identifier = hashlib.md5(blueprint_str.encode()).hexdigest()[:12]
    else:
        # Default case - no subdirectory
        subdirectory = ""
        base_identifier = hashlib.md5(str(metadata).encode()).hexdigest()[:12]

    # Add modification info if provided (for denoising variants)
    if modification_info:
        identifier = f"{base_identifier}_{modification_info}"
    else:
        identifier = base_identifier

    # Create full path with subdirectory
    if subdirectory:
        save_dir = Path(base_dir) / subdirectory
    else:
        save_dir = Path(base_dir)

    # Ensure directory exists
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save the image
    image_path = save_dir / f"{identifier}.png"
    image.save(str(image_path))

    # Save metadata
    metadata_to_save = metadata.copy() if metadata else {}
    if blueprint:
        metadata_to_save["blueprint"] = blueprint
    metadata_to_save["image_id"] = identifier
    metadata_to_save["image_type"] = subdirectory if subdirectory else "general"
    metadata_to_save["image_filename"] = f"{identifier}.png"
    metadata_to_save["image_path"] = (
        f"{subdirectory}/{identifier}.png" if subdirectory else f"{identifier}.png"
    )

    metadata_path = save_dir / f"{identifier}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata_to_save, f, indent=2)

    # Return the full relative path including subdirectory
    # This is what will be stored in the 'image' field of metadata
    if subdirectory:
        return f"{subdirectory}/{identifier}.png"
    else:
        return f"{identifier}.png"


def load_image_and_metadata(
    image_id: str, base_dir: str = os.getenv("VQA_DATASET_DIR")
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Load an image and its associated metadata by ID.

    Args:
        image_id: The relative path to the image (e.g., "blueprints/abc123.png" or "terrain/terrain_x0_y0.png")
        base_dir: Base directory where images are stored

    Returns:
        Tuple of (full_image_path, metadata_dict) or (None, None) if not found
    """
    # Parse the image_id to handle subdirectories
    id_path = Path(image_id)

    # Construct full paths
    image_path = Path(base_dir) / id_path

    # Extract the base name without extension for metadata file
    base_name = id_path.stem
    metadata_path = image_path.parent / f"{base_name}_metadata.json"

    if not image_path.exists():
        return None, None

    metadata = None
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

    return str(image_path), metadata


def get_image_full_path(
    image_id: str, base_dir: str = os.getenv("VQA_DATASET_DIR")
) -> str:
    """
    Get the full filesystem path for an image given its ID.

    Args:
        image_id: The relative path to the image (e.g., "blueprints/abc123.png")
        base_dir: Base directory where images are stored

    Returns:
        Full filesystem path to the image
    """
    return str(Path(base_dir) / image_id)


def ensure_image_directories(base_dir: str = os.getenv("VQA_DATASET_DIR")) -> None:
    """
    Ensure all required image subdirectories exist.

    Args:
        base_dir: Base directory for images
    """
    directories = [
        Path(base_dir),
        Path(base_dir) / "blueprints",
        Path(base_dir) / "terrain",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def save_map_render(
    image: RenderedImage,
    position: Optional[Dict[str, float]] = None,
    radius: int = 64,
    metadata: Optional[Dict[str, Any]] = None,
    base_dir: str = os.getenv("VQA_DATASET_DIR"),
) -> str:
    """
    Convenience function specifically for saving game map renders.

    Args:
        image: RenderedImage to save
        position: Position dict with x,y coordinates
        radius: Render radius
        metadata: Additional metadata
        base_dir: Base directory for images

    Returns:
        Image ID for use in metadata
    """
    # Build map-specific metadata
    map_metadata = metadata or {}
    map_metadata.update(
        {
            "position": position,
            "radius": radius,
            "timestamp": datetime.now().isoformat(),
        }
    )

    return save_rendered_image(
        image=image,
        blueprint=None,
        metadata=map_metadata,
        modification_info=f"radius_{radius}",
        base_dir=base_dir,
        is_map=True,
    )


def get_legacy_image_id(blueprint: Dict[str, Any]) -> str:
    """
    Generate the old-style hash-based image ID for backwards compatibility.

    Args:
        blueprint: Blueprint dictionary

    Returns:
        Legacy hash-based image ID
    """
    return str(hash(str(blueprint)))
