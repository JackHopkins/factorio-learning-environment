from env.src.entities import Position, BoundingBox
from pydantic import BaseModel, Field

class Camera(BaseModel):
    centroid: Position
    raw_centroid: Position
    entity_count: int
    bounds: BoundingBox
    zoom: float
    position: Position