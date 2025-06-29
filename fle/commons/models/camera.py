from fle.env.entities import BoundingBox, Position
from pydantic import BaseModel


class Camera(BaseModel):
    centroid: Position
    raw_centroid: Position
    entity_count: int
    bounds: BoundingBox
    zoom: float
    position: Position