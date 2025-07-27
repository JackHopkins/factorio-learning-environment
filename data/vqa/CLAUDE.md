I want to train a visual encoder for the Factorio Learning Environment.

We have Blueprints, which represent entities on the map. Blueprints can be converted into Python - the imperative steps to construct the blueprint.

Our goal is to construct tasks that train a model to effectively reason over a rendering of the game state, using a text representation as ground truth.

# Tools
- Load blueprint - load_blueprint()
- Render it - render()

# VQA Tasks

## Basic
- Render a blueprint
- Predict the name of the entity | position

## Spatial Reasoning
- Render the blueprint
- Determine relative entity offsets to each other
- Compose natural language reasoning questions e.g:
  - what is 5 to the left, and 2 below the leftmost mining drill?
  - what is the distance between the leftmost and rightmost mining drill?
- Predict the name of the entity | Q ∪ image

## State Prediction
- Render a live factory
- Predict the state of an entity | Q ∪ image

## Denoising
- Pick an entity
- Remove / Modify / Replace it
- Q: What entity should be at X, Y?
- Predict the original entity | Q ∪ image

## Action Prediction
- Get blueprint
- Convert it to Python
- Run N-1 Python actions
- Predict Nth action | image

## Productivity Planning
- Get a live factory
- Connect 2 entities
- Predict the production throughput | image


## Contrastive Image–Text Alignment
- Get blueprint (main)
  - Get 3 other named blueprints
  - Summarize each blueprint into a 'title' \ 'purpose': e.g
    - title: 15-to-6 Express Belt Balancer (Compact, Prioritized)" 
    - purpose: Evenly distributes items from 15 input belts across 6 output belts, ensuring balanced throughput in a high-capacity logistics system.
- Predict the title/purpose | Q ∪ image ∪ options