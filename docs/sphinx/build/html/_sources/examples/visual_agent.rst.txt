Visual Agent Example
====================

This example demonstrates how to create a visual agent that processes visual information from the game environment.

Agent Overview
--------------

The visual agent uses computer vision techniques to:

1. **Image Processing**: Analyze game screenshots and map images
2. **Object Detection**: Identify entities and resources in the visual data
3. **Spatial Reasoning**: Understand spatial relationships between objects
4. **Visual Planning**: Plan actions based on visual information

Agent Implementation
--------------------

.. code-block:: python

   from fle.agents.agent_abc import Agent
   from fle.env.gym_env.action import Action
   from fle.env.game_types import Position, Direction
   from typing import Dict, Any, List
   import base64
   import io
   from PIL import Image
   import numpy as np
   
   class VisualAgent(Agent):
       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           self.name = "VisualAgent"
           self.vision_enabled = config.get('vision_enabled', True)
           self.image_processing = config.get('image_processing', True)
           self.spatial_reasoning = config.get('spatial_reasoning', True)
           self.visual_memory = {}
           self.step_count = 0
       
       def act(self, observation: Dict[str, Any]) -> Action:
           """Generate action based on visual observation"""
           self.step_count += 1
           
           # Get visual information
           map_image = observation.get('map_image', '')
           entities = observation.get('entities', [])
           inventory = observation.get('inventory', {})
           
           # Process visual information
           if self.vision_enabled and map_image:
               visual_analysis = self._analyze_visual_data(map_image)
           else:
               visual_analysis = {}
           
           # Generate action based on visual analysis
           if self.step_count == 1:
               code = self._initial_visual_exploration(visual_analysis)
           elif self.step_count <= 10:
               code = self._visual_setup(visual_analysis, entities)
           else:
               code = self._visual_monitoring(visual_analysis, entities, inventory)
           
           return Action(
               agent_idx=0,
               code=code,
               game_state=None
           )
       
       def _analyze_visual_data(self, map_image: str) -> Dict[str, Any]:
           """Analyze visual data from map image"""
           try:
               # Decode base64 image
               image_data = base64.b64decode(map_image)
               image = Image.open(io.BytesIO(image_data))
               
               # Convert to numpy array
               img_array = np.array(image)
               
               # Perform visual analysis
               analysis = {
                   'image_size': image.size,
                   'image_mode': image.mode,
                   'dominant_colors': self._extract_dominant_colors(img_array),
                   'entity_locations': self._detect_entities(img_array),
                   'resource_patches': self._detect_resource_patches(img_array),
                   'spatial_features': self._extract_spatial_features(img_array)
               }
               
               return analysis
               
           except Exception as e:
               print(f"Visual analysis error: {e}")
               return {}
       
       def _extract_dominant_colors(self, img_array: np.ndarray) -> List[tuple]:
           """Extract dominant colors from image"""
           # Reshape image to 2D array of pixels
           pixels = img_array.reshape(-1, img_array.shape[-1])
           
           # Simple color extraction (in practice, use more sophisticated methods)
           unique_colors = np.unique(pixels, axis=0)
           return unique_colors[:10].tolist()  # Return top 10 colors
       
       def _detect_entities(self, img_array: np.ndarray) -> List[Dict[str, Any]]:
           """Detect entities in the image"""
           # Simple entity detection (in practice, use computer vision models)
           entities = []
           
           # Look for specific color patterns that might indicate entities
           # This is a simplified example
           for y in range(0, img_array.shape[0], 10):
               for x in range(0, img_array.shape[1], 10):
                   pixel = img_array[y, x]
                   if self._is_entity_pixel(pixel):
                       entities.append({
                           'position': (x, y),
                           'type': self._classify_entity(pixel),
                           'confidence': 0.8
                       })
           
           return entities
       
       def _detect_resource_patches(self, img_array: np.ndarray) -> List[Dict[str, Any]]:
           """Detect resource patches in the image"""
           resource_patches = []
           
           # Look for resource-specific color patterns
           for y in range(0, img_array.shape[0], 20):
               for x in range(0, img_array.shape[1], 20):
                   region = img_array[y:y+20, x:x+20]
                   if self._is_resource_region(region):
                       resource_patches.append({
                           'position': (x, y),
                           'type': self._classify_resource(region),
                           'size': self._estimate_resource_size(region)
                       })
           
           return resource_patches
       
       def _extract_spatial_features(self, img_array: np.ndarray) -> Dict[str, Any]:
           """Extract spatial features from the image"""
           return {
               'image_center': (img_array.shape[1] // 2, img_array.shape[0] // 2),
               'image_bounds': (0, 0, img_array.shape[1], img_array.shape[0]),
               'density_map': self._calculate_density_map(img_array),
               'connectivity': self._analyze_connectivity(img_array)
           }
       
       def _initial_visual_exploration(self, visual_analysis: Dict[str, Any]) -> str:
           """Initial visual exploration"""
           return f'''
   # Initial visual exploration
   print("Starting VisualAgent exploration")
   
   # Analyze visual data
   visual_analysis = {visual_analysis}
   print(f"Visual analysis: {visual_analysis}")
   
   # Get current position
   position = get_position()
   print(f"Starting position: {{position}}")
   
   # Look for resources using visual analysis
   if visual_analysis.get('resource_patches'):
       for patch in visual_analysis['resource_patches']:
           print(f"Found resource patch: {{patch['type']}} at {{patch['position']}}")
   
   # Look for entities using visual analysis
   if visual_analysis.get('entity_locations'):
       for entity in visual_analysis['entity_locations']:
           print(f"Found entity: {{entity['type']}} at {{entity['position']}}")
   '''
       
       def _visual_setup(self, visual_analysis: Dict[str, Any], entities: List) -> str:
           """Set up operations based on visual analysis"""
           return '''
   # Visual-based setup
   print("Setting up operations based on visual analysis")
   
   # Find resources using visual cues
   iron_pos = nearest(Resource.IRON_ORE)
   copper_pos = nearest(Resource.COPPER_ORE)
   
   if iron_pos:
       # Place mining drill with visual guidance
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=iron_pos,
           direction=Direction.NORTH
       )
       print(f"Placed mining drill at {iron_pos} based on visual analysis")
       
       # Add storage with visual positioning
       chest = place_entity_next_to(
           entity=Prototype.IronChest,
           reference_position=drill.drop_position,
           direction=Direction.SOUTH
       )
       print(f"Placed chest at {chest.position}")
   
   # Check visual feedback
   entities = get_entities()
   print(f"Current entities: {len(entities)}")
   '''
       
       def _visual_monitoring(self, visual_analysis: Dict[str, Any], entities: List, inventory: Dict) -> str:
           """Monitor operations using visual feedback"""
           return '''
   # Visual monitoring
   print("Monitoring operations with visual feedback")
   
   # Check entities
   entities = get_entities()
   working_entities = [e for e in entities if hasattr(e, 'status') and e.status == EntityStatus.WORKING]
   print(f"Working entities: {len(working_entities)}")
   
   # Check inventory
   inventory = inspect_inventory()
   total_items = sum(inventory.values())
   print(f"Total items: {total_items}")
   
   # Visual analysis feedback
   if visual_analysis:
       print(f"Visual analysis: {visual_analysis}")
       if 'spatial_features' in visual_analysis:
           features = visual_analysis['spatial_features']
           print(f"Spatial features: {features}")
   '''

Visual Processing Features
--------------------------

**Image Analysis**
   - Dominant color extraction
   - Entity detection and classification
   - Resource patch identification
   - Spatial feature extraction

**Computer Vision Techniques**
   - Edge detection
   - Color segmentation
   - Object recognition
   - Spatial reasoning

**Visual Memory**
   - Store visual information across steps
   - Track changes in visual data
   - Maintain spatial maps

Example Visual Analysis
-----------------------

**Input Image**
   Base64 encoded PNG image of the game map

**Output Analysis**
   .. code-block:: python

      {
          'image_size': (1024, 1024),
          'image_mode': 'RGB',
          'dominant_colors': [
              [0, 0, 0],      # Black (background)
              [139, 69, 19],  # Brown (dirt)
              [128, 128, 128], # Gray (stone)
              [255, 215, 0]   # Gold (resources)
          ],
          'entity_locations': [
              {
                  'position': (512, 256),
                  'type': 'mining_drill',
                  'confidence': 0.9
              },
              {
                  'position': (520, 264),
                  'type': 'chest',
                  'confidence': 0.8
              }
          ],
          'resource_patches': [
              {
                  'position': (100, 200),
                  'type': 'iron_ore',
                  'size': 'large'
              },
              {
                  'position': (300, 400),
                  'type': 'copper_ore',
                  'size': 'medium'
              }
          ],
          'spatial_features': {
              'image_center': (512, 512),
              'image_bounds': (0, 0, 1024, 1024),
              'density_map': {...},
              'connectivity': {...}
          }
      }

Running the Visual Agent
-----------------------

**Environment Setup**
   .. code-block:: python

      import gym
      from fle.agents.visual_agent import VisualAgent
      
      # Create environment
      env = gym.make("iron_ore_throughput")
      
      # Create visual agent
      agent = VisualAgent({
          'vision_enabled': True,
          'image_processing': True,
          'spatial_reasoning': True
      })
      
      # Run episode
      obs = env.reset()
      done = False
      step = 0
      
      while not done and step < 100:
          action = agent.act(obs)
          obs, reward, terminated, truncated, info = env.step(action)
          done = terminated or truncated
          step += 1
          print(f"Step {step}: Reward = {reward}")
      
      env.close()

**Command Line Usage**
   .. code-block:: bash

      # Run visual agent evaluation
      fle eval --agent visual_agent --config configs/visual_agent_config.json

Agent Configuration
-------------------

**Basic Configuration**
   .. code-block:: json

      {
          "agent_type": "VisualAgent",
          "config": {
              "vision_enabled": true,
              "image_processing": true,
              "spatial_reasoning": true,
              "visual_memory_size": 100
          },
          "evaluation": {
              "episodes": 5,
              "max_steps": 1000,
              "success_threshold": 0.6
          }
      }

**Advanced Configuration**
   .. code-block:: json

      {
          "agent_type": "VisualAgent",
          "config": {
              "vision_enabled": true,
              "image_processing": true,
              "spatial_reasoning": true,
              "visual_memory_size": 1000,
              "computer_vision_model": "resnet50",
              "object_detection_threshold": 0.7,
              "spatial_analysis_depth": 3
          },
          "evaluation": {
              "episodes": 10,
              "max_steps": 2000,
              "success_threshold": 0.8,
              "metrics": ["visual_accuracy", "spatial_reasoning", "object_detection"]
          }
      }

Performance Metrics
-------------------

**Visual Accuracy**
   - Object detection accuracy
   - Resource identification accuracy
   - Spatial reasoning accuracy

**Processing Performance**
   - Image processing time
   - Memory usage
   - CPU utilization

**Visual Reasoning**
   - Spatial relationship understanding
   - Object interaction prediction
   - Visual planning effectiveness

Example Metrics
~~~~~~~~~~~~~~~

.. code-block:: python

   {
       "visual_accuracy": {
           "object_detection": 0.85,  # fraction of objects correctly identified
           "resource_identification": 0.90,  # fraction of resources correctly identified
           "spatial_reasoning": 0.75  # fraction of spatial relationships correctly understood
       },
       "processing_performance": {
           "image_processing_time": 0.1,  # seconds per image
           "memory_usage": 512,  # MB
           "cpu_utilization": 0.3  # fraction of CPU used
       },
       "visual_reasoning": {
           "spatial_understanding": 0.80,  # fraction of spatial relationships understood
           "object_interaction_prediction": 0.70,  # fraction of interactions correctly predicted
           "visual_planning_effectiveness": 0.65  # fraction of visual plans that succeed
       }
   }

Troubleshooting
---------------

**Visual Processing Issues**
   - **Poor image quality**: Check image resolution and format
   - **Detection failures**: Adjust detection thresholds
   - **Memory issues**: Reduce visual memory size

**Performance Issues**
   - **Slow processing**: Optimize image processing algorithms
   - **High memory usage**: Implement image compression
   - **CPU bottlenecks**: Use parallel processing

**Accuracy Issues**
   - **False positives**: Adjust detection thresholds
   - **Missed objects**: Improve detection algorithms
   - **Spatial errors**: Enhance spatial reasoning

Best Practices
--------------

1. **Image Quality**: Ensure high-quality input images
2. **Detection Thresholds**: Tune detection parameters
3. **Memory Management**: Monitor and optimize memory usage
4. **Performance Optimization**: Use efficient algorithms
5. **Error Handling**: Implement robust error recovery
6. **Visual Memory**: Maintain useful visual information
7. **Spatial Reasoning**: Develop strong spatial understanding
