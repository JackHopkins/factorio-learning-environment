from pydantic import BaseModel
from fle.env.entities import Position, BoundingBox


class Camera(BaseModel):
    centroid: Position
    raw_centroid: Position
    entity_count: int
    bounds: BoundingBox
    zoom: float
    position: Position
