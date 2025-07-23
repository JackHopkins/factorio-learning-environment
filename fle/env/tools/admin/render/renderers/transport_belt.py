# renderers/transport_belt.py
"""
Transport belt renderer
"""
from typing import Dict, Tuple, Optional, Callable

from PIL import Image

from fle.env import EntityCore, Entity
from ..constants import NORTH, SOUTH, EAST, WEST, VERTICAL, HORIZONTAL, DEFAULT_SCALING



def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render transport belt"""

    around = get_around(entity, grid)
    count = sum(around)
    direction = entity.get('direction', 0)
    if not isinstance(direction, int):
        direction = direction.value
    degree_offset = 90

    image = None


    if count in [0, 2, 3]:
        if direction in VERTICAL:
            image = image_resolver(f"{entity['name']}_vertical")
            degree_offset = -90
        else:
            image = image_resolver(f"{entity['name']}_horizontal")
    elif count == 1:
        if around[0] == 1:  # South
            if direction in VERTICAL:
                image = image_resolver(f"{entity['name']}_vertical")
                degree_offset = -90
            elif direction == EAST:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = 180
            elif direction == WEST:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
        elif around[1] == 1:  # West
            if direction in HORIZONTAL:
                image = image_resolver(f"{entity['name']}_horizontal")
            elif direction == NORTH:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
            elif direction == SOUTH:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = -180  # Add this back
        elif around[2] == 1:  # North
            if direction in VERTICAL:
                image = image_resolver(f"{entity['name']}_vertical")
                degree_offset = -90
            elif direction == EAST:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
            elif direction == WEST:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = 180
        elif around[3] == 1:  # East
            if direction in HORIZONTAL:
                image = image_resolver(f"{entity['name']}_horizontal")
            elif direction == NORTH:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = -180
            elif direction == SOUTH:
                image = image_resolver(f"{entity['name']}_bend_right")  # Changed from bend_right
                degree_offset = 90
                # Keep default degree_offset = 90

    if image is None:
        return None

    # Rotate image based on direction
    rotation = (direction * 45) - degree_offset
    if rotation != 0:
        image = image.rotate(-rotation, expand=True)

    return image


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Transport belts have no shadows"""
    return None


def render_inventory(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Transport belts display their contents on them"""
    inventory = entity.get('inventory', {})
    if not inventory or (not inventory.get('left') and not inventory.get('right')):
        return None

    # Get belt direction
    direction = entity.get('direction', 0)
    if not isinstance(direction, int):
        direction = direction.value

    # Import required modules
    from PIL import Image
    import math

    # Determine belt type and rotation using the same logic as render()
    from ..constants import VERTICAL, HORIZONTAL, EAST, WEST, NORTH, SOUTH

    around = get_around(entity, grid)
    count = sum(around)
    degree_offset = 90
    belt_type = 'straight'  # Default

    # Determine belt configuration
    if count == 1:
        if around[0] == 1:  # South
            if direction == EAST:
                belt_type = 'bend_left'
                degree_offset = 180
            elif direction == WEST:
                belt_type = 'bend_right'
                degree_offset = 90
            elif direction in VERTICAL:
                belt_type = 'vertical'
                degree_offset = -90
        elif around[1] == 1:  # West
            if direction == NORTH:
                belt_type = 'bend_right'
                degree_offset = 90
            elif direction == SOUTH:
                belt_type = 'bend_left'
                degree_offset = -180
            else:
                belt_type = 'horizontal'
        elif around[2] == 1:  # North
            if direction == EAST:
                belt_type = 'bend_right'
                degree_offset = 90
            elif direction == WEST:
                belt_type = 'bend_left'
                degree_offset = 180
            elif direction in VERTICAL:
                belt_type = 'vertical'
                degree_offset = -90
        elif around[3] == 1:  # East
            if direction == NORTH:
                belt_type = 'bend_left'
                degree_offset = -180
            elif direction == SOUTH:
                belt_type = 'bend_right'
                degree_offset = 90
            else:
                belt_type = 'horizontal'
    else:  # count in [0, 2, 3]
        if direction in VERTICAL:
            belt_type = 'vertical'
            degree_offset = -90
        else:
            belt_type = 'horizontal'

    # Calculate final rotation
    rotation = (direction * 45) - degree_offset

    # Create overlay (64x64 to match sprite size)
    overlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))

    # Item configuration
    item_size = 16  # Larger items since we have more space
    max_items_per_lane = 4

    # Center offset - belt content is centered in 64x64 sprite
    center = 32  # Center of the 64x64 image
    belt_half_width = 16  # Roughly half of the 32x32 belt content

    def place_items_on_lane(items_dict, is_left_lane):
        """Place items on a specific lane"""
        if not items_dict:
            return

        item_name = list(items_dict.keys())[0]
        item_count = min(items_dict[item_name], max_items_per_lane)

        item_icon = image_resolver(f"icon_{item_name}", False)
        if not item_icon:
            return

        item_icon = item_icon.resize((item_size, item_size), Image.Resampling.LANCZOS)

        # Define item positions based on belt type
        # All positions are in the "canonical" orientation (before rotation)
        positions = []
        spacing = 8

        if belt_type in ('horizontal', 'vertical'):
            for i in range(item_count):
                offset = -12 + (i * spacing)
                if direction in VERTICAL:
                    # This belt will be rotated to vertical
                    # For a south-facing belt (direction 4), rotation is 270 degrees
                    # This means our "left" needs to be on the bottom to end up on the left after rotation
                    if direction == SOUTH:  # Going down
                        if is_left_lane:
                            x = center + offset
                            y = center + 6  # Bottom becomes left after 270° rotation
                        else:
                            x = center + offset
                            y = center - 6  # Top becomes right after 270° rotation
                    else:  # NORTH - Going up
                        if is_left_lane:
                            x = center + offset
                            y = center - 6  # Top becomes left after 90° rotation
                        else:
                            x = center + offset
                            y = center + 6  # Bottom becomes right after 90° rotation
                else:
                    # Horizontal belts - standard layout
                    if is_left_lane:
                        x = center + offset
                        y = center - 6  # Top lane
                    else:
                        x = center + offset
                        y = center + 6  # Bottom lane
                positions.append((x, y))

        elif belt_type == 'bend_left':
            # Actually curves from bottom to RIGHT (naming is confusing!)
            # Left lane is outer curve, right lane is inner curve
            for i in range(item_count):
                t = (i + 0.5) / max_items_per_lane  # 0 to 1 along curve

                if is_left_lane:
                    # Outer curve - larger radius (this is working correctly)
                    angle = t * math.pi / 2  # 0 to 90 degrees
                    radius = 18
                    center_x, center_y = center - 10, center + 10  # Curve center on left

                    # Calculate position on arc (curving right)
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                else:
                    # Inner curve - needs 90 degree rotation
                    # Start from right side and curve up instead of starting from bottom
                    angle = t * math.pi / 2  # 0 to 90 degrees
                    radius = 10
                    center_x, center_y = center - 10, center + 10

                    # Rotate the arc by 90 degrees (start from right, go up)
                    x = center_x + radius * math.sin(angle)
                    y = center_y + radius * math.cos(angle)

                positions.append((int(x), int(y)))

        elif belt_type == 'bend_right':
            # Actually curves from bottom to LEFT (naming is confusing!)
            # Left lane is inner curve, right lane is outer curve
            for i in range(item_count):
                t = (i + 0.5) / max_items_per_lane

                if is_left_lane:
                    # Inner curve - needs 90 degree rotation
                    # Start from left side and curve up instead of starting from bottom
                    angle = t * math.pi / 2
                    radius = 10
                    center_x, center_y = center + 10, center + 10

                    # Rotate the arc by 90 degrees (start from left, go up)
                    x = center_x - radius * math.sin(angle)
                    y = center_y - radius * math.cos(angle)
                else:
                    # Outer curve - larger radius (this is working correctly)
                    angle = t * math.pi / 2
                    radius = 18
                    center_x, center_y = center + 10, center + 10

                    # Calculate position on arc (curving left)
                    x = center_x - radius * math.cos(angle)
                    y = center_y - radius * math.sin(angle)

                positions.append((int(x), int(y)))

        # Place items at calculated positions
        for x, y in positions:
            # Center the item icon at position
            paste_x = x - item_size // 2
            paste_y = y - item_size // 2
            overlay.paste(item_icon, (paste_x, paste_y), item_icon if item_icon.mode == 'RGBA' else None)

    # Process both lanes
    place_items_on_lane(inventory.get('left', {}), True)
    place_items_on_lane(inventory.get('right', {}), False)

    # Apply rotation to match belt sprite
    if rotation != 0:
        overlay = overlay.rotate(-rotation, expand=False)  # Keep 64x64 size

    return overlay

def render_inventory2(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Transport belts display their contents on them"""
    inventory = entity.get('inventory', {})
    if not inventory:
        return None

    # Get belt direction
    direction = entity.get('direction', 0)
    if not isinstance(direction, int):
        direction = direction.value

    # Import required modules
    from PIL import Image, ImageDraw
    import math

    # Create a transparent image to overlay items on
    # Start with a larger canvas to handle rotation
    canvas_size = 64
    overlay = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))

    # Determine belt type using the same logic as render()
    from ..constants import VERTICAL, HORIZONTAL, EAST, WEST, NORTH, SOUTH

    # Get surrounding connections
    around = get_around(entity, grid)
    count = sum(around)

    # Determine belt configuration and rotation
    degree_offset = 90
    is_bend = False
    bend_type = None

    if count == 1:
        if around[0] == 1:  # South
            if direction == EAST:
                is_bend = True
                bend_type = 'left'
                degree_offset = 180
            elif direction == WEST:
                is_bend = True
                bend_type = 'right'
                degree_offset = 90
            elif direction in VERTICAL:
                degree_offset = -90
        elif around[1] == 1:  # West
            if direction == NORTH:
                is_bend = True
                bend_type = 'right'
                degree_offset = 90
            elif direction == SOUTH:
                is_bend = True
                bend_type = 'left'
                degree_offset = -180
        elif around[2] == 1:  # North
            if direction == EAST:
                is_bend = True
                bend_type = 'right'
                degree_offset = 90
            elif direction == WEST:
                is_bend = True
                bend_type = 'left'
                degree_offset = 180
            elif direction in VERTICAL:
                degree_offset = -90
        elif around[3] == 1:  # East
            if direction == NORTH:
                is_bend = True
                bend_type = 'left'
                degree_offset = -180
            elif direction == SOUTH:
                is_bend = True
                bend_type = 'right'
                degree_offset = 90
    elif count in [0, 2, 3]:
        if direction in VERTICAL:
            degree_offset = -90

    # Calculate the rotation that will be applied to match the belt sprite
    rotation = (direction * 45) - degree_offset

    # Belt items are roughly 16x16 pixels
    item_size = 16
    center = canvas_size // 2

    def place_items_on_path(items_dict, is_left_lane):
        """Place items along the belt path"""
        if not items_dict:
            return

        item_name = list(items_dict.keys())[0]
        item_count = min(items_dict[item_name], 4)

        item_icon = image_resolver(f"icon_{item_name}", False)
        if not item_icon:
            return

        item_icon = item_icon.resize((item_size, item_size), Image.Resampling.LANCZOS)

        for i in range(item_count):
            if is_bend:
                # Place items along the curve
                # All curves start from bottom and turn 90 degrees
                t = (i + 0.5) / 4.0  # Parameter from 0 to 1, offset to center items

                # Determine if this lane is on the inside or outside of the curve
                is_inside = (bend_type == 'left' and is_left_lane) or (bend_type == 'right' and not is_left_lane)

                # Lane offset from center line
                lane_offset = 6

                if bend_type == 'left':
                    # Left turn: bottom to left
                    # Use a simple quarter circle arc
                    angle = t * math.pi / 2  # 0 to 90 degrees

                    # Center line of the belt follows this path
                    center_x = center - 6 * math.sin(angle)
                    center_y = center - 6 * (1 - math.cos(angle))

                    # Offset perpendicular to the curve for lanes
                    # Normal vector at this point on the curve
                    normal_x = -math.cos(angle)
                    normal_y = -math.sin(angle)

                    if not is_inside:
                        x = center_x - normal_x * lane_offset
                        y = center_y - normal_y * lane_offset
                    else:
                        x = center_x + normal_x * lane_offset
                        y = center_y + normal_y * lane_offset

                else:
                    # Right turn: bottom to right
                    angle = t * math.pi / 2  # 0 to 90 degrees

                    # Center line of the belt
                    center_x = center + 6 * math.sin(angle)
                    center_y = center - 6 * (1 - math.cos(angle))

                    # Normal vector (pointing outward from curve)
                    normal_x = math.cos(angle)
                    normal_y = math.sin(angle)

                    if not is_inside:
                        x = center_x - normal_x * lane_offset
                        y = center_y - normal_y * lane_offset
                    else:
                        x = center_x + normal_x * lane_offset
                        y = center_y - normal_y * lane_offset

            else:
                # Straight belt - always draw horizontally, rotation handles orientation
                spacing = 8
                offset = -12 + (i * spacing)

                # For straight belts, we need to consider how rotation will affect lanes
                # The rotation will transform our coordinate system
                # For belts that will be rotated to vertical, we need to adjust

                if direction in VERTICAL:
                    # This belt will be rotated to vertical
                    # For a south-facing belt (direction 4), rotation is 270 degrees
                    # This means our "left" needs to be on the bottom to end up on the left after rotation
                    if direction == SOUTH:  # Going down
                        if is_left_lane:
                            x = center + offset
                            y = center + 6  # Bottom becomes left after 270° rotation
                        else:
                            x = center + offset
                            y = center - 6  # Top becomes right after 270° rotation
                    else:  # NORTH - Going up
                        if is_left_lane:
                            x = center + offset
                            y = center - 6  # Top becomes left after 90° rotation
                        else:
                            x = center + offset
                            y = center + 6  # Bottom becomes right after 90° rotation
                else:
                    # Horizontal belts - standard layout
                    if is_left_lane:
                        x = center + offset
                        y = center - 6  # Top lane
                    else:
                        x = center + offset
                        y = center + 6  # Bottom lane

            # Place the item
            x_pos = int(x - item_size / 2)
            y_pos = int(y - item_size / 2)
            overlay.paste(item_icon, (x_pos, y_pos), item_icon if item_icon.mode == 'RGBA' else None)

    # Process both lanes
    place_items_on_path(inventory.get('left', {}), True)
    place_items_on_path(inventory.get('right', {}), False)

    # Apply the same rotation as the belt sprite
    if rotation != 0:
        overlay = overlay.rotate(-rotation, expand=True)

    # Crop to final size (32x32) centered
    final_size = 32
    if overlay.size[0] > final_size or overlay.size[1] > final_size:
        left = (overlay.width - final_size) // 2
        top = (overlay.height - final_size) // 2
        right = left + final_size
        bottom = top + final_size
        overlay = overlay.crop((left, top, right, bottom))

    # Return the overlay if we added any items
    if inventory.get('left') or inventory.get('right'):
        return overlay

    return None


# def render_inventory(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
#     """Transport belts display their contents on them"""
#     inventory = entity.get('inventory', {})
#     if not inventory:
#         return None
#
#     # Get belt direction
#     direction = entity.get('direction', 0)
#     if not isinstance(direction, int):
#         direction = direction.value
#
#     # Import required modules
#     from PIL import Image, ImageDraw
#     import math
#
#     # Create a transparent image to overlay items on
#     # Start with a larger canvas to handle rotation
#     canvas_size = 64
#     overlay = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
#
#     # Determine belt type using the same logic as render()
#     from ..constants import VERTICAL, HORIZONTAL, EAST, WEST, NORTH, SOUTH
#
#     # Get surrounding connections
#     around = get_around(entity, grid)
#     count = sum(around)
#
#     # Determine belt configuration and rotation
#     degree_offset = 90
#     is_bend = False
#     bend_type = None
#
#     if count == 1:
#         if around[0] == 1:  # South
#             if direction == EAST:
#                 is_bend = True
#                 bend_type = 'left'
#                 degree_offset = 180
#             elif direction == WEST:
#                 is_bend = True
#                 bend_type = 'right'
#                 degree_offset = 90
#             elif direction in VERTICAL:
#                 degree_offset = -90
#         elif around[1] == 1:  # West
#             if direction == NORTH:
#                 is_bend = True
#                 bend_type = 'right'
#                 degree_offset = 90
#             elif direction == SOUTH:
#                 is_bend = True
#                 bend_type = 'left'
#                 degree_offset = -180
#         elif around[2] == 1:  # North
#             if direction == EAST:
#                 is_bend = True
#                 bend_type = 'right'
#                 degree_offset = 90
#             elif direction == WEST:
#                 is_bend = True
#                 bend_type = 'left'
#                 degree_offset = 180
#             elif direction in VERTICAL:
#                 degree_offset = -90
#         elif around[3] == 1:  # East
#             if direction == NORTH:
#                 is_bend = True
#                 bend_type = 'left'
#                 degree_offset = -180
#             elif direction == SOUTH:
#                 is_bend = True
#                 bend_type = 'right'
#                 degree_offset = 90
#     elif count in [0, 2, 3]:
#         if direction in VERTICAL:
#             degree_offset = -90
#
#     # Calculate the rotation that will be applied to match the belt sprite
#     rotation = (direction * 45) - degree_offset
#
#     # Belt items are roughly 16x16 pixels (smaller to fit on belt)
#     item_size = 16
#     center = canvas_size // 2
#
#     def place_items_on_path(items_dict, lane_offset, is_left_lane):
#         """Place items along the belt path"""
#         if not items_dict:
#             return
#
#         item_name = list(items_dict.keys())[0]
#         item_count = min(items_dict[item_name], 4)
#
#         item_icon = image_resolver(f"icon_{item_name}", False)
#         if not item_icon:
#             return
#
#         item_icon = item_icon.resize((item_size, item_size), Image.Resampling.LANCZOS)
#
#         for i in range(item_count):
#             if is_bend:
#                 # For bends, place items along a curve
#                 # The curve follows the belt's bend before rotation
#                 t = (i + 0.5) / 4.0  # Parameter along curve (0 to 1)
#
#                 # Base curve in unrotated space
#                 if bend_type == 'left':
#                     # Left bend: straight to curved left
#                     angle = t * math.pi / 2  # 0 to 90 degrees
#                     radius = 16
#                     x = center + radius * math.sin(angle) + lane_offset * math.cos(angle)
#                     y = center + radius * (1 - math.cos(angle)) + lane_offset * math.sin(angle)
#                 else:
#                     # Right bend: straight to curved right
#                     angle = t * math.pi / 2  # 0 to 90 degrees
#                     radius = 16
#                     x = center + radius * math.sin(angle) + lane_offset * math.cos(angle)
#                     y = center - radius * (1 - math.cos(angle)) - lane_offset * math.sin(angle)
#             else:
#                 # Straight belt - items in a line
#                 # Place items along the belt before rotation
#                 spacing = 8
#                 if direction in VERTICAL or (count in [0, 2, 3] and direction in VERTICAL):
#                     # Vertical belt (before rotation)
#                     x = center + lane_offset
#                     y = center - 12 + (i * spacing)
#                 else:
#                     # Horizontal belt (before rotation)
#                     x = center - 12 + (i * spacing)
#                     y = center + lane_offset
#
#             # Center the item icon
#             x_pos = int(x - item_size / 2)
#             y_pos = int(y - item_size / 2)
#
#             overlay.paste(item_icon, (x_pos, y_pos), item_icon if item_icon.mode == 'RGBA' else None)
#
#     # Process left and right lanes
#     # Lane offsets are perpendicular to belt direction
#     lane_spacing = 6
#     place_items_on_path(inventory.get('left', {}), -lane_spacing, True)
#     place_items_on_path(inventory.get('right', {}), lane_spacing, False)
#
#     # Apply the same rotation as the belt sprite
#     if rotation != 0:
#         overlay = overlay.rotate(-rotation, expand=True)
#
#     # Crop to final size (32x32) centered
#     final_size = 32
#     if overlay.size[0] > final_size or overlay.size[1] > final_size:
#         # Calculate crop box to center the result
#         left = (overlay.width - final_size) // 2
#         top = (overlay.height - final_size) // 2
#         right = left + final_size
#         bottom = top + final_size
#         overlay = overlay.crop((left, top, right, bottom))
#
#     # Return the overlay if we added any items
#     if inventory.get('left') or inventory.get('right'):
#         return overlay
#
#     return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    around = get_around(entity, grid)
    return f"{entity.get('direction', 0)}_{'_'.join(map(str, around))}"


# TODO: I think the semantics are wrong here @jack
def get_around(entity: Dict, grid) -> list:
    """Check surrounding connections"""
    return [
        is_transport_belt(grid.get_relative(0, -1), SOUTH) or
        is_splitter(grid.get_relative(0.5, -1), SOUTH) or
        is_splitter(grid.get_relative(-0.5, -1), SOUTH),

        is_transport_belt(grid.get_relative(1, 0), WEST) or
        is_splitter(grid.get_relative(1, 0.5), WEST) or
        is_splitter(grid.get_relative(1, -0.5), WEST),

        is_transport_belt(grid.get_relative(0, 1),  NORTH) or
        is_splitter(grid.get_relative(0.5, 1), NORTH) or
        is_splitter(grid.get_relative(-0.5, 1), NORTH),

        is_transport_belt(grid.get_relative(-1, 0), EAST) or
        is_splitter(grid.get_relative(-1, 0.5), EAST) or
        is_splitter(grid.get_relative(-1, -0.5), EAST)
    ]


def is_transport_belt(entity: Optional[Dict], direction: int) -> int:
    """Check if entity is transport belt facing direction"""
    if entity is None:
        return 0

    belt_types = ['transport-belt', 'fast-transport-belt', 'express-transport-belt']
    underground_types = ['underground-belt', 'fast-underground-belt', 'express-underground-belt']

    if entity['name'] in belt_types:
        if entity['direction'] == direction or (
                entity['direction'].value == direction if not isinstance(entity['direction'], int) else 0
        ):
            return 1

    if entity['name'] in underground_types:
        if entity['type'] == 'output':
            if entity['direction'] == direction or (
                    entity['direction'].value == direction if not isinstance(entity['direction'], int) else 0
            ):
                return 1

    return 0


def is_splitter(entity: Optional[Dict], direction: int) -> int:
    """Check if entity is splitter facing direction"""
    if entity is None:
        return 0

    splitter_types = ['splitter', 'fast-splitter', 'express-splitter']

    if entity['name'] in splitter_types:
        if entity['direction'] == direction or (
                entity['direction'].value == direction if not isinstance(entity['direction'], int) else 0
        ):
            return 1

    return 0


def get_size(entity: Dict) -> Tuple[float, float]:
    """Transport belt is 1x1"""
    return (1, 1)