# query_information

The `query_information` tool allows you to obtain information regarding from a pre-defined list of pages containing instructions how to effectively use the API.

## Basic Usage
To get content of a specific page, the page_id needs to be sent in 
```python
inserter_information = query_information("how_to_use_inserters") -> str
print(f"Manual how to use inserters")
print(inserter_information)
```
### Parameters

- `page_id`: ID of the page whose information is needed

## Existing pages

The following page IDs exist currently in the database

"how_to_check_research_progress"
"how_to_connect_entities"
"how_to_create_assembling_machines"
"how_to_create_electricity_generators" -- Information on how to setup electricity generators
"how_to_create_reserach_setups"
"how_to_create_self_fueling_mining_system"
"how_to_launch_a_rocket"
"how_to_set_up_multiple_drill_plate_mine"
"how_to_set_up_raw_resource_burner_mine"
"how_to_setup_chemical_plants" -- Information on how to setup and use chemical plants
"how_to_setup_oil_refineries" -- Information on how to setup and use oil refineries
"how_to_smelt_ores"
"how_to_setup_storage_tanks" -- Information on how to setup and use storage tanks
"how_to_setup_crude_oil_production" -- Information on how to setup and use pumpjacks to harvest crude oil