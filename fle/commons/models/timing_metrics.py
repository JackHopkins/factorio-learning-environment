import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimingMetrics(BaseModel):
    """Stores timing metrics for a single operation"""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    children: List["TimingMetrics"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def total_duration(self) -> float:
        """Get total duration including children"""
        if not self.children:
            return self.duration
        return sum(child.total_duration for child in self.children)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format"""
        return {
            "operation": self.operation_name,
            "duration": self.duration,
            "total_duration": self.total_duration,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
        }
