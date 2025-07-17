Use the API to write a Python script to test whether the objective was achieved. Here is an example

EXAMPLE INPUT
The objective is to craft 5 copper plates. 

EXAMPLE OUTPUT
```python
number_of_copper_plates = inspect_inventory()[Prototype.CopperPlate]
assert number_of_copper_plates == 5, f"Inventory does not have 5 copper plates, it has {{number_of_copper_plates}}" 
```

USER INPUT
The objective is '{objective}'