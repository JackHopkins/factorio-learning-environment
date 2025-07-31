"""Position utilities for VQA tasks."""

import re
from typing import Union, Tuple, Dict, Any


def format_position(x: Union[int, float], y: Union[int, float]) -> str:
    """
    Format a position as Position(x={x}, y={y}).
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        Formatted position string
    """
    return f"Position(x={x}, y={y})"


def format_position_from_dict(position: Dict[str, Union[int, float]]) -> str:
    """
    Format a position dictionary as Position(x={x}, y={y}).
    
    Args:
        position: Dictionary with 'x' and 'y' keys
        
    Returns:
        Formatted position string
    """
    x = position.get('x', 0)
    y = position.get('y', 0)
    return format_position(x, y)


def convert_coordinate_format_in_text(text: str) -> str:
    """
    Convert coordinate references in text from (x, y) format to Position(x={x}, y={y}) format.
    
    Args:
        text: Text containing coordinate references
        
    Returns:
        Text with updated coordinate format
    """
    # Pattern to match coordinates in (x, y) format
    coordinate_pattern = r'\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)'
    
    def replace_coordinate(match):
        x = match.group(1)
        y = match.group(2)
        return f"Position(x={x}, y={y})"
    
    return re.sub(coordinate_pattern, replace_coordinate, text)


def extract_position_from_text(text: str) -> Tuple[float, float]:
    """
    Extract position coordinates from Position(x={x}, y={y}) format.
    
    Args:
        text: Text containing position reference
        
    Returns:
        Tuple of (x, y) coordinates, or (0, 0) if not found
    """
    pattern = r'Position\(x=(-?\d+(?:\.\d+)?),\s*y=(-?\d+(?:\.\d+)?)\)'
    match = re.search(pattern, text)
    
    if match:
        x = float(match.group(1))
        y = float(match.group(2))
        return (x, y)
    
    return (0.0, 0.0)


def normalize_position_references_in_qa(qa_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize position references in a QA pair to use Position(x={x}, y={y}) format.
    
    Args:
        qa_data: QA pair dictionary containing 'question' and 'answer' keys
        
    Returns:
        Updated QA pair with normalized position format
    """
    updated_qa = qa_data.copy()
    
    if 'question' in updated_qa:
        updated_qa['question'] = convert_coordinate_format_in_text(updated_qa['question'])
    
    if 'answer' in updated_qa:
        updated_qa['answer'] = convert_coordinate_format_in_text(updated_qa['answer'])
    
    return updated_qa