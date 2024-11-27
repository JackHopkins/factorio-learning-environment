from dataclasses import dataclass
from typing import List


@dataclass
class Trace:
    programs: List[int]  # List of program IDs in order
    value: float        # Final accumulated value
    text: str          # Concatenated text for vectorization