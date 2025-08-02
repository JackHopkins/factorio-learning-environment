from inspect_ai.dataset import Dataset, Sample, MemoryDataset

def raw_position_dataset() -> MemoryDataset:
    samples = []
    for x in range(0, 100):
       for y in range(0, 100):
        sample = Sample(
            input=f"Position(x={x}, y={y})",
            metadata={"x": x, "y": y},
        )
        samples.append(sample)

    # Create dataset
    dataset = MemoryDataset(samples=samples)

    #dataset.shuffle()
    return dataset