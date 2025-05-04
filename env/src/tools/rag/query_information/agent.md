# query_information

The `query_information` tool allows you to retrieve pages that are relevant to your query to obtain information and instructions regarding how to effectively use the API and how to use different factorio specific entities.

## Basic Usage
To get content relevant to a query, send in the query in a question format using the tool 

```python
inserter_information = query_information("How to use inserters to input items into a chest")
print(f"Manual how to use inserters")
print(inserter_information)

electricity_information = query_information("How to set up electricity networks?")
print(f"Manual how to set up elctricity")
print(electricity_information)


chem_plant_information = query_information("How to use chemical plants to create sulfur?")
print(f"Manual how to set up chemical plants")
print(chem_plant_information)


resource_mine_information = query_information("How to set up  resource mines?")
print(f"Manual how to set up resource mines")
print(resource_mine_information)
```
NB: Do not under any circumstances execute steps that rely on printed information in the same policy. You need to first print the information in step n and then execute actions that rely on that information in step n+1
EXTREMELY IMPORTANT: Do not use this tool for entity recipes. Use the get_prototype_recipe tool to get recipes and ingredients for entities
Do not use this tool to get information about the general environment. This tool only gives API examples and factorio know-how