import base64
import io
from PIL import Image


class RenderedImage:
    """Wrapper for rendered images with display capabilities"""

    def __init__(self, image: Image.Image):
        self.image = image

    def show(self):
        """Display the image (works in IDEs)"""
        self.image.show()

    def save(self, path: str):
        """Save the image to a file"""
        self.image.save(path)

    def to_base64(self):
        """Convert image to base64 string for embedding in HTML/Markdown"""
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def _repr_png_(self):
        """Support for Jupyter notebook display"""
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        return buffer.getvalue()
