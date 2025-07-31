"""Image utilities for VQA tasks."""

import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Union
from fle.commons.models.rendered_image import RenderedImage


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
    if 'label' in blueprint and blueprint['label']:
        name = blueprint['label']
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


def generate_variant_hash(blueprint: Dict[str, Any], modification_info: str = "") -> str:
    """
    Generate a hash representing this specific variant of the blueprint.
    
    Args:
        blueprint: Blueprint dictionary
        modification_info: Additional info about modifications (for denoising, etc.)
        
    Returns:
        Short hash string for this variant
    """
    # Create a string representing this specific variant
    variant_string = str(blueprint) + modification_info
    
    # Generate a shorter, more readable hash
    hash_object = hashlib.md5(variant_string.encode())
    return hash_object.hexdigest()[:12]  # Use first 12 characters


def generate_image_path_and_id(blueprint: Dict[str, Any], metadata: Dict[str, Any], 
                              modification_info: str = "", base_dir: str = "../../dataset/images") -> tuple[str, str]:
    """
    Generate the new folder structure image path and ID.
    
    Args:
        blueprint: Blueprint dictionary
        metadata: Metadata containing filename
        modification_info: Additional info for variants (denoising, etc.)
        base_dir: Base directory for images
        
    Returns:
        Tuple of (file_path, image_id) where:
        - file_path: Full path where image should be saved
        - image_id: ID to use in metadata (relative path from base_dir)
    """
    blueprint_name = get_blueprint_name(blueprint, metadata)
    variant_hash = generate_variant_hash(blueprint, modification_info)
    
    # Create the folder structure
    folder_path = Path(base_dir) / blueprint_name
    
    # Create the image ID (relative path from base_dir for metadata)
    image_id = f"{blueprint_name}/{variant_hash}"
    
    # Create the full file path
    file_path = folder_path / f"{variant_hash}.jpg"
    
    return str(file_path), image_id


def save_rendered_image(image: RenderedImage, blueprint: Dict[str, Any], metadata: Dict[str, Any], 
                       modification_info: str = "", base_dir: str = "../../dataset/images") -> str:
    """
    Save a rendered image using the new folder structure.
    
    Args:
        image: RenderedImage to save
        blueprint: Blueprint dictionary
        metadata: Metadata containing filename
        modification_info: Additional info for variants (denoising, etc.)
        base_dir: Base directory for images
        
    Returns:
        Image ID for use in metadata
    """
    file_path, image_id = generate_image_path_and_id(blueprint, metadata, modification_info, base_dir)
    
    # Create directory if it doesn't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save the image
    image.save(file_path)
    
    return image_id


def get_legacy_image_id(blueprint: Dict[str, Any]) -> str:
    """
    Generate the old-style hash-based image ID for backwards compatibility.
    
    Args:
        blueprint: Blueprint dictionary
        
    Returns:
        Legacy hash-based image ID
    """
    return str(hash(str(blueprint)))