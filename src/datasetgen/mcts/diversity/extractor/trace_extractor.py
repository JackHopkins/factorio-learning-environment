from abc import ABC, abstractmethod
from typing import List


class TraceExtractor(ABC):
    def __init__(self, programs):
        self.programs = programs

    @abstractmethod
    def extract_from_trace(self, trace: List[int]) -> str:
        """Convert trace to string for encoding"""
        pass