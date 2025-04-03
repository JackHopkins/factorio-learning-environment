# connect_entities

The `connect_entities` tool provides functionality to connect different types of Factorio entities using various connection types like transport belts, pipes and power poles. This document outlines how to use the tool effectively.

## Core Concepts

The connect_entities tool can connect:
- Transport belts (including underground belts)
- Pipes (including underground pipes) 
- Power poles
- Walls

For each connection type, the tool handles:
- Pathing around obstacles
- Proper entity rotation and orientation
- Network/group management
- Resource requirements verification
- Connection point validation

## Basic Usage

### General Pattern
```python
# Basic connection between two positions or entities
connection = connect_entities(source, target, connection_type=Prototype.X)

# Connection with multiple waypoints
connection = connect_entities(pos1, pos2, pos3, pos4, connection_type=Prototype.X)
```

### Source/Target Types
The source and target can be:
- Positions
- Entities 
- Entity Groups

### Connection Types
You must specify a connection type prototype:
```python
# Single connection type
connection_type=Prototype.TransportBelt

# Multiple compatible connection types 
# If you have UndergroundBelts in inventory, use them to simplify above-ground structures
connection_type={Prototype.TransportBelt, Prototype.UndergroundBelt}
```