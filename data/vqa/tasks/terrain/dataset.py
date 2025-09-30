from inspect_ai.dataset import Sample, MemoryDataset
from typing import List, Tuple
import math


def generate_spiral_positions(
    max_radius: int = 50, step: int = 1
) -> List[Tuple[int, int]]:
    """
    Generate positions in a spiral pattern starting from origin.

    Args:
        max_radius: Maximum distance from origin to generate
        step: Step size between positions

    Returns:
        List of (x, y) positions in spiral order
    """
    positions = []
    x, y = 0, 0
    dx, dy = 0, -step

    positions.append((x, y))

    while max(abs(x), abs(y)) < max_radius:
        # Check if we need to turn
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
            # Turn 90 degrees clockwise
            dx, dy = -dy, dx

        # Move to next position
        x, y = x + dx, y + dy
        positions.append((x, y))

    return positions


def generate_concentric_spiral_positions(max_radius: int = 50) -> List[Tuple[int, int]]:
    """
    Generate positions in concentric squares expanding from origin.
    This creates a more predictable pattern than a true spiral.

    Args:
        max_radius: Maximum distance from origin

    Returns:
        List of (x, y) positions in concentric order
    """
    positions = [(0, 0)]  # Start at origin

    for radius in range(1, max_radius + 1):
        # Top edge (left to right)
        for x in range(-radius, radius + 1):
            positions.append((x, -radius))

        # Right edge (top to bottom, excluding corners)
        for y in range(-radius + 1, radius):
            positions.append((radius, y))

        # Bottom edge (right to left)
        for x in range(radius, -radius - 1, -1):
            positions.append((x, radius))

        # Left edge (bottom to top, excluding corners)
        for y in range(radius - 1, -radius, -1):
            positions.append((-radius, y))

    return positions


def generate_true_spiral_positions(
    max_positions: int = 10000, spacing: float = 1.0
) -> List[Tuple[int, int]]:
    """
    Generate positions following an Archimedean spiral.

    Args:
        max_positions: Maximum number of positions to generate
        spacing: Distance between spiral arms

    Returns:
        List of (x, y) positions in spiral order
    """
    positions = []
    seen = set()

    theta = 0
    while len(positions) < max_positions:
        # Archimedean spiral: r = a + b * theta
        r = spacing * theta / (2 * math.pi)

        # Convert to Cartesian coordinates
        x = int(round(r * math.cos(theta)))
        y = int(round(r * math.sin(theta)))

        # Only add unique positions
        if (x, y) not in seen:
            positions.append((x, y))
            seen.add((x, y))

        # Increment angle
        theta += 0.1

        # Break if we're too far from origin
        if r > 100:
            break

    return positions


def raw_position_dataset(
    pattern: str = "concentric", limit: int = None
) -> MemoryDataset:
    """
    Generate position dataset with various patterns.

    Args:
        pattern: One of "concentric", "spiral", "true_spiral", or "grid"
        limit: Maximum number of samples (None for all)

    Returns:
        MemoryDataset with position samples
    """
    samples = []

    if pattern == "grid":
        # Original grid pattern
        positions = [(x, y) for x in range(-50, 51) for y in range(-50, 51)]
    elif pattern == "concentric":
        # Concentric squares expanding from origin
        positions = generate_concentric_spiral_positions(max_radius=50)
    elif pattern == "spiral":
        # Simple spiral pattern
        positions = generate_spiral_positions(max_radius=50)
    elif pattern == "true_spiral":
        # Archimedean spiral
        positions = generate_true_spiral_positions(max_positions=10000)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")

    # Apply limit if specified
    if limit:
        positions = positions[:limit]

    # Create samples
    for x, y in positions:
        sample = Sample(
            input=f"Position(x={x}, y={y})",
            metadata={"x": x, "y": y},
        )
        samples.append(sample)

    dataset = MemoryDataset(samples=samples[:10])
    return dataset


def raw_position_dataset_with_priority(
    max_radius: int = 50, inner_radius_priority: int = 10
) -> MemoryDataset:
    """
    Generate position dataset with priority given to positions near origin.

    Args:
        max_radius: Maximum distance from origin
        inner_radius_priority: Positions within this radius are added first

    Returns:
        MemoryDataset with position samples
    """
    samples = []

    # First add all positions within priority radius
    priority_positions = []
    regular_positions = []

    for x in range(-max_radius, max_radius + 1):
        for y in range(-max_radius, max_radius + 1):
            distance = math.sqrt(x * x + y * y)
            if distance <= inner_radius_priority:
                priority_positions.append((x, y, distance))
            elif distance <= max_radius:
                regular_positions.append((x, y, distance))

    # Sort priority positions by distance from origin
    priority_positions.sort(key=lambda p: p[2])

    # Sort regular positions by distance from origin
    regular_positions.sort(key=lambda p: p[2])

    # Create samples - priority positions first
    for x, y, _ in priority_positions:
        sample = Sample(
            input=f"Position(x={x}, y={y})",
            metadata={"x": x, "y": y, "distance_from_origin": math.sqrt(x * x + y * y)},
        )
        samples.append(sample)

    # Then regular positions
    for x, y, _ in regular_positions:
        sample = Sample(
            input=f"Position(x={x}, y={y})",
            metadata={"x": x, "y": y, "distance_from_origin": math.sqrt(x * x + y * y)},
        )
        samples.append(sample)

    dataset = MemoryDataset(samples=samples)
    return dataset


# Update your terrain/dataset.py to use this pattern
def terrain_position_dataset() -> MemoryDataset:
    """
    Generate terrain positions in a concentric spiral pattern.
    This ensures we explore from the origin outward, which is more
    efficient for finding resources and buildable areas.
    """
    return raw_position_dataset(pattern="concentric", limit=None)


# Example usage in your task
if __name__ == "__main__":
    # Test different patterns
    print("Concentric pattern (first 20 positions):")
    dataset = raw_position_dataset(pattern="concentric", limit=20)
    for i, sample in enumerate(dataset.samples[:20]):
        print(f"{i}: x={sample.metadata['x']}, y={sample.metadata['y']}")

    print("\nSpiral pattern (first 20 positions):")
    dataset = raw_position_dataset(pattern="spiral", limit=20)
    for i, sample in enumerate(dataset.samples[:20]):
        print(f"{i}: x={sample.metadata['x']}, y={sample.metadata['y']}")

    print("\nPriority-based pattern (first 20 positions):")
    dataset = raw_position_dataset_with_priority(max_radius=50, inner_radius_priority=5)
    for i, sample in enumerate(dataset.samples[:20]):
        dist = sample.metadata.get("distance_from_origin", 0)
        print(
            f"{i}: x={sample.metadata['x']}, y={sample.metadata['y']}, dist={dist:.2f}"
        )
