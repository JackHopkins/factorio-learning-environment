"""Utility functions for handling images in Inspect integration."""

from fle.commons.models.rendered_image import RenderedImage


def rendered_image_to_data_url(image: RenderedImage) -> str:
    """
    Convert a RenderedImage to a base64 data URL suitable for Inspect's ContentImage.

    Args:
        image: The RenderedImage instance to convert

    Returns:
        A data URL string in the format "data:image/png;base64,<base64_data>"
    """
    base64_data = image.to_base64()
    return f"data:image/png;base64,{base64_data}"
