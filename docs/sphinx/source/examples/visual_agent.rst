Visual Agent Example
====================

This example demonstrates how to create a visual agent that processes visual information from the Factorio Learning Environment, including map images and entity visualizations.

Agent Implementation
--------------------

.. code-block:: python

   from fle.agents.agent_abc import AgentABC
   from fle.agents.models import Conversation, Response, Policy
   from fle.agents.models import CompletionState
   from typing import Optional, Dict, Any
   import base64
   import io
   from PIL import Image

   class VisualAgent(AgentABC):
       def __init__(self, vision_model: str = "gpt-4-vision", **kwargs):
           super().__init__(**kwargs)
           self.name = "VisualAgent"
           self.vision_model = vision_model
           self.vision_client = self._initialize_vision()
           self.step_count = 0
           
       def _initialize_vision(self):
           """Initialize the vision model client"""
           # Initialize your vision client here
           # This is a placeholder - replace with actual implementation
           return None
           
       def step(self, conversation: Conversation, response: Response) -> Policy:
           """Visual step implementation"""
           self.step_count += 1
           
           # Extract visual information from response
           visual_data = self._extract_visual_data(response)
           
           # Process visual information
           visual_analysis = self._analyze_visual_data(visual_data)
           
           # Generate action based on visual analysis
           action = self._generate_action_from_visual(visual_analysis)
           
           return Policy(
               action=action,
               reasoning=f"Based on visual analysis: {visual_analysis}"
           )
           
       def _extract_visual_data(self, response: Response) -> Dict[str, Any]:
           """Extract visual data from response"""
           visual_data = {
               'map_image': None,
               'entity_images': [],
               'ui_elements': []
           }
           
           # Extract map image if available
           if hasattr(response, 'map_image') and response.map_image:
               visual_data['map_image'] = response.map_image
           
           # Extract entity visualizations if available
           if hasattr(response, 'entity_images') and response.entity_images:
               visual_data['entity_images'] = response.entity_images
           
           # Extract UI elements if available
           if hasattr(response, 'ui_elements') and response.ui_elements:
               visual_data['ui_elements'] = response.ui_elements
           
           return visual_data
           
       def _analyze_visual_data(self, visual_data: Dict[str, Any]) -> str:
           """Analyze visual data using vision model"""
           analysis = []
           
           # Analyze map image
           if visual_data['map_image']:
               map_analysis = self._analyze_map_image(visual_data['map_image'])
               analysis.append(f"Map analysis: {map_analysis}")
           
           # Analyze entity images
           if visual_data['entity_images']:
               entity_analysis = self._analyze_entity_images(visual_data['entity_images'])
               analysis.append(f"Entity analysis: {entity_analysis}")
           
           # Analyze UI elements
           if visual_data['ui_elements']:
               ui_analysis = self._analyze_ui_elements(visual_data['ui_elements'])
               analysis.append(f"UI analysis: {ui_analysis}")
           
           return "; ".join(analysis) if analysis else "No visual data available"
           
       def _analyze_map_image(self, map_image: str) -> str:
           """Analyze map image"""
           try:
               # Decode base64 image
               image_data = base64.b64decode(map_image)
               image = Image.open(io.BytesIO(image_data))
               
               # Basic image analysis (placeholder)
               width, height = image.size
               analysis = f"Map size: {width}x{height}"
               
               # Use vision model for detailed analysis
               if self.vision_client:
                   detailed_analysis = self.vision_client.analyze_image(image)
                   analysis += f"; Detailed: {detailed_analysis}"
               
               return analysis
               
           except Exception as e:
               return f"Map analysis error: {e}"
           
       def _analyze_entity_images(self, entity_images: list) -> str:
           """Analyze entity images"""
           analysis = f"Found {len(entity_images)} entity images"
           
           for i, entity_img in enumerate(entity_images):
               try:
                   # Analyze individual entity image
                   entity_analysis = self._analyze_single_entity(entity_img)
                   analysis += f"; Entity {i}: {entity_analysis}"
                   
               except Exception as e:
                   analysis += f"; Entity {i} analysis error: {e}"
           
           return analysis
           
       def _analyze_single_entity(self, entity_img: str) -> str:
           """Analyze a single entity image"""
           try:
               # Decode and analyze entity image
               image_data = base64.b64decode(entity_img)
               image = Image.open(io.BytesIO(image_data))
               
               # Basic analysis
               width, height = image.size
               analysis = f"Entity size: {width}x{height}"
               
               # Use vision model for detailed analysis
               if self.vision_client:
                   detailed_analysis = self.vision_client.analyze_image(image)
                   analysis += f"; Type: {detailed_analysis}"
               
               return analysis
               
           except Exception as e:
               return f"Entity analysis error: {e}"
           
       def _analyze_ui_elements(self, ui_elements: list) -> str:
           """Analyze UI elements"""
           analysis = f"Found {len(ui_elements)} UI elements"
           
           for element in ui_elements:
               if 'type' in element:
                   analysis += f"; {element['type']}"
               if 'text' in element:
                   analysis += f": {element['text']}"
           
           return analysis
           
       def _generate_action_from_visual(self, visual_analysis: str) -> str:
           """Generate action based on visual analysis"""
           if "iron ore" in visual_analysis.lower():
               action = """
   # Move to iron ore patch
   iron_pos = nearest(Resource.IronOre)
   move_to(iron_pos)
   print(f'Moved to iron ore at {iron_pos}')
   """
           elif "mining drill" in visual_analysis.lower():
               action = """
   # Place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   print(f'Placed mining drill at {drill.position}')
   """
           elif "chest" in visual_analysis.lower():
               action = """
   # Place chest
   chest = place_entity(
       entity=Prototype.IronChest,
       position=Position(x=0, y=1),
       direction=Direction.NORTH
   )
   print(f'Placed chest at {chest.position}')
   """
           else:
               action = f"print('Visual analysis: {visual_analysis}')"
           
           return action
           
       def end(self, conversation: Conversation, completion: CompletionState) -> None:
           """Handle conversation end"""
           print(f"Visual agent completed {self.step_count} steps")
           print(f"Completion state: {completion}")

Vision Model Integration
------------------------

OpenAI Vision Model
^^^^^^^^^^^^^^^^^^^

Integration with OpenAI's vision model:

.. code-block:: python

   import openai
   from typing import Optional

   class OpenAIVisionAgent(VisualAgent):
       def __init__(self, api_key: str, **kwargs):
           super().__init__(**kwargs)
           self.api_key = api_key
           self.client = openai.OpenAI(api_key=api_key)
           
       def _initialize_vision(self):
           """Initialize OpenAI vision client"""
           return self.client
           
       def _analyze_map_image(self, map_image: str) -> str:
           """Analyze map image using OpenAI vision"""
           try:
               # Decode image
               image_data = base64.b64decode(map_image)
               
               # Use OpenAI vision API
               response = self.client.chat.completions.create(
                   model="gpt-4-vision-preview",
                   messages=[
                       {
                           "role": "user",
                           "content": [
                               {
                                   "type": "text",
                                   "text": "Analyze this Factorio map image. Describe what you see, including resources, buildings, and any notable features."
                               },
                               {
                                   "type": "image_url",
                                   "image_url": {
                                       "url": f"data:image/png;base64,{map_image}"
                                   }
                               }
                           ]
                       }
                   ],
                   max_tokens=500
               )
               
               return response.choices[0].message.content
               
           except Exception as e:
               return f"Vision analysis error: {e}"

Custom Vision Model
^^^^^^^^^^^^^^^^^^^

Integration with a custom vision model:

.. code-block:: python

   class CustomVisionAgent(VisualAgent):
       def __init__(self, model_path: str, **kwargs):
           super().__init__(**kwargs)
           self.model_path = model_path
           self.model = self._load_model()
           
       def _load_model(self):
           """Load custom vision model"""
           # Load your custom model here
           # This is a placeholder
           return None
           
       def _analyze_map_image(self, map_image: str) -> str:
           """Analyze map image using custom model"""
           try:
               # Decode image
               image_data = base64.b64decode(map_image)
               image = Image.open(io.BytesIO(image_data))
               
               # Use custom model for analysis
               if self.model:
                   analysis = self.model.predict(image)
                   return analysis
               else:
                   return "Custom model not available"
                   
           except Exception as e:
               return f"Custom model analysis error: {e}"

Visual Processing Pipeline
--------------------------

Image Preprocessing
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class PreprocessingVisualAgent(VisualAgent):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.preprocessing_enabled = True
           
       def _preprocess_image(self, image: Image.Image) -> Image.Image:
           """Preprocess image for better analysis"""
           # Resize image if too large
           if image.size[0] > 1024 or image.size[1] > 1024:
               image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
           
           # Enhance contrast
           from PIL import ImageEnhance
           enhancer = ImageEnhance.Contrast(image)
           image = enhancer.enhance(1.2)
           
           # Enhance sharpness
           enhancer = ImageEnhance.Sharpness(image)
           image = enhancer.enhance(1.1)
           
           return image
           
       def _analyze_map_image(self, map_image: str) -> str:
           """Analyze preprocessed map image"""
           try:
               # Decode and preprocess image
               image_data = base64.b64decode(map_image)
               image = Image.open(io.BytesIO(image_data))
               
               if self.preprocessing_enabled:
                   image = self._preprocess_image(image)
               
               # Continue with analysis
               return super()._analyze_map_image(map_image)
               
           except Exception as e:
               return f"Preprocessed analysis error: {e}"

Multi-Modal Analysis
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class MultiModalVisualAgent(VisualAgent):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.analysis_modes = ['map', 'entities', 'ui', 'text']
           
       def _analyze_visual_data(self, visual_data: Dict[str, Any]) -> str:
           """Multi-modal visual analysis"""
           analyses = []
           
           # Map analysis
           if visual_data['map_image']:
               map_analysis = self._analyze_map_image(visual_data['map_image'])
               analyses.append(f"Map: {map_analysis}")
           
           # Entity analysis
           if visual_data['entity_images']:
               entity_analysis = self._analyze_entity_images(visual_data['entity_images'])
               analyses.append(f"Entities: {entity_analysis}")
           
           # UI analysis
           if visual_data['ui_elements']:
               ui_analysis = self._analyze_ui_elements(visual_data['ui_elements'])
               analyses.append(f"UI: {ui_analysis}")
           
           # Text analysis (from conversation)
           text_analysis = self._analyze_text_context(visual_data)
           if text_analysis:
               analyses.append(f"Text: {text_analysis}")
           
           return "; ".join(analyses)
           
       def _analyze_text_context(self, visual_data: Dict[str, Any]) -> str:
           """Analyze text context"""
           # Extract and analyze text from conversation
           # This is a placeholder
           return "Text analysis placeholder"

Running the Visual Agent
------------------------

Environment Setup
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import gym
   from fle.env.gym_env.action import Action

   # Create environment with visual support
   env = gym.make("iron_ore_throughput")
   
   # Create visual agent
   agent = VisualAgent(vision_model="gpt-4-vision")
   
   # Reset environment
   obs = env.reset(options={'game_state': None})

Agent Execution Loop
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Run visual agent
   for step in range(10):
       # Generate action from visual analysis
       policy = agent.step(obs, None)
       
       # Create action for environment
       action = Action(
           agent_idx=0,
           game_state=None,
           code=policy.action
       )
       
       # Execute action
       obs, reward, terminated, truncated, info = env.step(action)
       
       # Check if done
       if terminated or truncated:
           break
       
       print(f"Step {step}: {policy.reasoning}")
       print(f"Reward: {reward}")

   # Clean up
   env.close()

Expected Output
---------------

The visual agent will analyze visual information and generate actions based on what it sees:

1. **Step 1**: Analyze initial map image and identify resources
2. **Step 2**: Move to identified iron ore patch
3. **Step 3**: Place mining drill based on visual analysis
4. **Step 4**: Place chest based on entity positions
5. **Step 5+**: Continue based on visual feedback

Example Output
^^^^^^^^^^^^^^

.. code-block:: bash

   Step 0: Based on visual analysis: Map analysis: Map size: 1024x1024; Detailed: I can see iron ore patches in the northwest area
   Reward: 0.0
   Step 1: Based on visual analysis: Map analysis: Map size: 1024x1024; Detailed: Iron ore patch visible at coordinates (100, 50)
   Reward: 0.0
   >>> Moved to iron ore at Position(x=100.0, y=50.0)
   Step 2: Based on visual analysis: Map analysis: Map size: 1024x1024; Detailed: Mining drill placed successfully at iron ore patch
   Reward: 0.0
   >>> Placed mining drill at Position(x=100.0, y=50.0)

Best Practices
--------------

1. **Image Preprocessing**: Enhance images for better analysis
2. **Multi-Modal Analysis**: Combine visual and text information
3. **Error Handling**: Handle vision model failures gracefully
4. **Performance**: Optimize image processing for speed
5. **Caching**: Cache analysis results when possible
6. **Validation**: Validate visual analysis results
7. **Documentation**: Document vision model capabilities
8. **Testing**: Test with various image types and qualities
9. **Resource Management**: Manage memory usage for large images
10. **Fallback**: Provide fallback when vision analysis fails
