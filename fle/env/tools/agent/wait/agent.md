# wait

Advance the live Factorio simulation for up to a specified number of ticks.
Machines, belts, research, power, and customer deliveries continue normally.

```python
wait(ticks: int, until: dict | None = None, poll_ticks: int = 300) -> dict
```

An optional inventory condition stops the wait early:

```python
result = wait(
    ticks=18000,
    until={
        "inventory": {
            "entity": furnace,
            "item": Prototype.StoneBrick,
            "at_least": 100,
        }
    },
    poll_ticks=300,
)
print(result)
```

The result reports requested and waited ticks, actual simulation advancement,
charged action ticks, whether the condition was met, and the last observation.
Contract deadlines continue to apply while waiting.
