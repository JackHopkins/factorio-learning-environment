Sprites
=======

FLE includes sprite management functionality for downloading spritemaps, extracting individual entity sprites, icons, and other visual assets from HuggingFace for use in visual reasoning tasks.

Overview
--------

The sprite system provides:

- **Sprite Downloads**: Automatic downloading of Factorio sprite assets
- **Extraction**: Processing spritemaps into individual entity sprites
- **Icons**: Entity and item icons for visual identification
- **Visual Reasoning**: Support for vision-enabled agents

Why Use Sprites?
----------------

Sprites enable visual reasoning capabilities for agents:

1. **Visual Observations**: Agents can see the game state as images
2. **Entity Recognition**: Identify entities by their visual appearance
3. **Spatial Reasoning**: Understand layouts and positioning visually
4. **Multimodal Learning**: Combine text and visual information

Installation
------------

Sprites are automatically downloaded when needed, but you can pre-download them:

.. code-block:: bash

   # Download and generate sprites
   fle sprites

   # Force re-download even if sprites exist
   fle sprites --force

   # Use custom directories and worker count
   fle sprites --spritemap-dir .fle/spritemaps --sprite-dir .fle/sprites --workers 5

Default Locations
-----------------

By default, sprites are stored in:

- **Spritemaps**: ``.fle/spritemaps/`` - Raw spritemap files from HuggingFace
- **Sprites**: ``.fle/sprites/`` - Extracted individual entity/item sprites

You can customize these locations using command-line arguments.

CLI Usage
---------

Basic Command
~~~~~~~~~~~~~

.. code-block:: bash

   # Download and extract sprites
   fle sprites

Options
~~~~~~~

.. code-block:: bash

   # Force re-download
   fle sprites --force

   # Custom directories
   fle sprites --spritemap-dir /path/to/spritemaps --sprite-dir /path/to/sprites

   # Parallel processing (default: 4 workers)
   fle sprites --workers 8

Programmatic Usage
------------------

Loading Sprites
~~~~~~~~~~~~~~~

.. code-block:: python

   from fle.env.sprites import SpriteManager

   # Initialize sprite manager
   sprite_manager = SpriteManager()

   # Get sprite for an entity
   sprite = sprite_manager.get_sprite('burner-mining-drill')

   # Get icon for an item
   icon = sprite_manager.get_icon('iron-plate')

   # Get all available sprites
   available = sprite_manager.list_sprites()

Using Sprites with Agents
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from fle.agents import VisualAgent
   import gym

   # Create environment with visual observations
   env = gym.make("iron_ore_throughput")

   # Create visual agent
   agent = VisualAgent(
       sprite_manager=SpriteManager(),
       model="gpt-4-vision"
   )

   # Agent can now use visual information
   obs = env.reset()
   action = agent.get_action(obs, include_visual=True)

Visual Observations
-------------------

Visual observations include:

- **Map Image**: Base64 encoded PNG of the game map
- **Entity Sprites**: Individual entity appearances
- **Overlays**: Visual indicators for status, connections, etc.

Example observation with visuals:

.. code-block:: python

   {
       'raw_text': '...',
       'entities': [...],
       'map_image': 'data:image/png;base64,...',
       'sprites': {
           'burner-mining-drill': 'data:image/png;base64,...',
           'iron-chest': 'data:image/png;base64,...'
       }
   }

Sprite Categories
-----------------

Entity Sprites
~~~~~~~~~~~~~~

Visual representations of game entities:

- Mining drills
- Furnaces
- Assembling machines
- Inserters
- Transport belts
- Pipes
- Power poles

Item Icons
~~~~~~~~~~

Icons for items and resources:

- Raw materials (ore, wood, stone)
- Plates (iron, copper, steel)
- Intermediate products
- Science packs
- Modules

Performance Considerations
--------------------------

Sprite Loading
~~~~~~~~~~~~~~

- Sprites are loaded on-demand by default
- Pre-loading all sprites increases memory usage but improves performance
- Use worker processes for faster initial extraction

Caching
~~~~~~~

- Extracted sprites are cached on disk
- Subsequent loads are much faster
- Clear cache with ``fle sprites --force``

Resolution
~~~~~~~~~~

Sprites are provided at their native resolution. You can resize them as needed:

.. code-block:: python

   from PIL import Image
   import base64
   from io import BytesIO

   # Decode base64 sprite
   sprite_data = base64.b64decode(sprite_base64)
   image = Image.open(BytesIO(sprite_data))

   # Resize
   resized = image.resize((32, 32))

Advanced Usage
--------------

Custom Sprite Sources
~~~~~~~~~~~~~~~~~~~~~

You can provide custom sprite sources:

.. code-block:: python

   sprite_manager = SpriteManager(
       spritemap_dir='/custom/path/spritemaps',
       sprite_dir='/custom/path/sprites'
   )

Batch Processing
~~~~~~~~~~~~~~~~

Process multiple sprites efficiently:

.. code-block:: python

   # Get multiple sprites at once
   sprites = sprite_manager.get_sprites([
       'burner-mining-drill',
       'iron-chest',
       'stone-furnace'
   ])

Export Sprites
~~~~~~~~~~~~~~

Export sprites to individual files:

.. code-block:: bash

   # Export all sprites to directory
   fle sprites --export-dir ./exported_sprites

Integration with Vision Models
-------------------------------

GPT-4 Vision
~~~~~~~~~~~~

.. code-block:: python

   import openai
   import base64

   # Get map image
   map_image = obs['map_image']

   # Send to GPT-4 Vision
   response = openai.ChatCompletion.create(
       model="gpt-4-vision-preview",
       messages=[
           {
               "role": "user",
               "content": [
                   {"type": "text", "text": "Analyze this Factorio base layout:"},
                   {"type": "image_url", "image_url": {"url": map_image}}
               ]
           }
       ]
   )

Claude Vision
~~~~~~~~~~~~~

.. code-block:: python

   import anthropic

   client = anthropic.Anthropic()

   # Get map image (remove data URL prefix)
   map_image_data = obs['map_image'].split(',')[1]

   message = client.messages.create(
       model="claude-3-opus-20240229",
       messages=[
           {
               "role": "user",
               "content": [
                   {
                       "type": "image",
                       "source": {
                           "type": "base64",
                           "media_type": "image/png",
                           "data": map_image_data
                       }
                   },
                   {
                       "type": "text",
                       "text": "What entities do you see in this layout?"
                   }
               ]
           }
       ]
   )

Troubleshooting
---------------

Download Fails
~~~~~~~~~~~~~~

If sprite download fails:

1. Check your internet connection
2. Verify access to HuggingFace
3. Try again with ``--force`` flag

Missing Sprites
~~~~~~~~~~~~~~~

If specific sprites are missing:

1. Run ``fle sprites --force`` to re-download
2. Check the sprite directory exists
3. Verify sprite names match Factorio prototypes

Memory Issues
~~~~~~~~~~~~~

If you encounter memory issues:

1. Don't pre-load all sprites
2. Use on-demand loading
3. Clear sprite cache periodically

Image Format Issues
~~~~~~~~~~~~~~~~~~~

If image decoding fails:

1. Verify base64 encoding is correct
2. Check image format (should be PNG)
3. Ensure data URL prefix is handled correctly

Next Steps
----------

- Learn about :doc:`../tools/overview` for non-visual interactions
- See the `Visual Agent example <https://github.com/JackHopkins/factorio-learning-environment/tree/main/examples>`_
- Review :doc:`../environment/overview` for context
