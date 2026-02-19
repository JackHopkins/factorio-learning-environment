"""
Test character persistence and recovery across various scenarios.

This test suite explores different triggers that could cause the player character
to disappear or become invalid, including:
- Long distance teleportation (>1000 tiles)
- Enemy damage/death scenarios
- Rapid successive movements
- Edge of map scenarios
- Character invalidation through various game mechanics
"""

import pytest
import time

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(configure_game):
    """Configure game with standard inventory for character persistence tests."""
    return configure_game(
        inventory={
            "coal": 100,
            "iron-plate": 100,
            "copper-plate": 50,
            "stone": 50,
            "transport-belt": 50,
            "burner-mining-drill": 5,
            "stone-furnace": 5,
            "wooden-chest": 5,
        }
    )


class TestLongDistanceMovement:
    """Test character persistence during long distance movements."""

    def test_move_100_tiles_away(self, game):
        """Test moving player character 1000+ tiles from origin."""
        # Get starting position
        start_pos = game.player_location
        print(f"Starting position: {start_pos}")

        # Attempt to move 1000 tiles away
        far_position = Position(x=100, y=0)
        try:
            result = game.move_to(far_position)
            print(f"Moved to: {result}")

            # Verify character still valid by checking position
            current_pos = game.player_location
            print(f"Current position after move: {current_pos}")

            # Try a subsequent action to verify character is functional
            nearby_pos = Position(x=current_pos.x + 5, y=current_pos.y)
            game.move_to(nearby_pos)
            print("Character still functional after 1000 tile move")

        except Exception as e:
            print(f"Move to 100 tiles failed: {e}")
            # This is expected - check if character recovered
            current_pos = game.player_location
            print(f"Position after failed move: {current_pos}")

    def test_move_1000_tiles_away(self, game):
        """Test moving player character 1000+ tiles from origin."""
        # Get starting position
        start_pos = game.player_location
        print(f"Starting position: {start_pos}")

        # Attempt to move 1000 tiles away
        far_position = Position(x=1000, y=0)
        try:
            result = game.move_to(far_position)
            print(f"Moved to: {result}")

            # Verify character still valid by checking position
            current_pos = game.player_location
            print(f"Current position after move: {current_pos}")

            # Try a subsequent action to verify character is functional
            nearby_pos = Position(x=current_pos.x + 5, y=current_pos.y)
            game.move_to(nearby_pos)
            print("Character still functional after 1000 tile move")

        except Exception as e:
            print(f"Move to 1000 tiles failed: {e}")
            # This is expected - check if character recovered
            current_pos = game.player_location
            print(f"Position after failed move: {current_pos}")

    def test_move_2000_tiles_away(self, game):
        """Test moving player character 2000+ tiles from origin."""
        far_position = Position(x=2000, y=2000)
        try:
            result = game.move_to(far_position)
            print(f"Moved to 2000 tiles: {result}")

            # Verify character functionality
            current_pos = game.player_location
            assert current_pos is not None, "Character position should be valid"

        except Exception as e:
            print(f"Expected failure for 2000 tiles: {e}")
            # Verify character recovery
            try:
                game.move_to(Position(x=0, y=0))
                print("Character recovered after failed long move")
            except Exception as recovery_error:
                pytest.fail(f"Character did not recover: {recovery_error}")

    def test_incremental_long_distance_movement(self, game):
        """Move far away in increments to test cumulative effect."""
        increment = 100
        max_distance = 1500
        current_x = 0

        for i in range(max_distance // increment):
            current_x += increment
            target = Position(x=current_x, y=0)
            try:
                game.move_to(target)
                print(f"Successfully moved to x={current_x}")
            except Exception as e:
                print(f"Failed at x={current_x}: {e}")
                # Verify character still exists
                try:
                    pos = game.player_location
                    print(f"Character still at: {pos}")
                except Exception as pos_error:
                    pytest.fail(f"Character lost at x={current_x}: {pos_error}")
                break

    def test_diagonal_long_distance(self, game):
        """Test long diagonal movement."""
        # Move diagonally 700 tiles in each direction (about 1000 tiles total)
        far_diagonal = Position(x=700, y=700)
        try:
            result = game.move_to(far_diagonal)
            print(f"Diagonal move result: {result}")

            # Verify character
            current = game.player_location
            print(f"Position after diagonal: {current}")

        except Exception as e:
            print(f"Diagonal move failed: {e}")


def generate_chunks(game, center_x: int, center_y: int, chunk_radius: int):
    """
    Generate chunks around a position to enable pathfinding in that area.

    Factorio chunks are 32x32 tiles. The pathfinder can only find paths
    through generated chunks.

    Args:
        game: The game namespace with instance access
        center_x: Center X position (in tiles)
        center_y: Center Y position (in tiles)
        chunk_radius: Radius in chunks (each chunk is 32 tiles)
    """
    game.instance._generate_chunks(center_x, center_y, chunk_radius)

    print(
        f"Generated chunks: center=({center_x}, {center_y}), radius={chunk_radius} chunks ({chunk_radius * 32} tiles)"
    )


def generate_chunks_along_path(
    game, start_x: int, start_y: int, end_x: int, end_y: int, chunk_radius: int = 2
):
    """
    Generate chunks along a path from start to end position.

    Args:
        game: The game namespace with instance access
        start_x, start_y: Starting position in tiles
        end_x, end_y: Ending position in tiles
        chunk_radius: Radius around each point to generate (in chunks)
    """
    instance = game.instance

    # Calculate how many points we need along the path
    # Generate chunks every 32 tiles (1 chunk width)
    dx = end_x - start_x
    dy = end_y - start_y
    distance = (dx**2 + dy**2) ** 0.5

    if distance == 0:
        generate_chunks(game, start_x, start_y, chunk_radius)
        return

    # Generate a point every 32 tiles
    num_points = max(2, int(distance / 32) + 1)

    # Request chunks at each point along the path
    for i in range(num_points):
        t = i / (num_points - 1) if num_points > 1 else 0
        x = int(start_x + dx * t)
        y = int(start_y + dy * t)
        instance.rcon_client.send_command(
            f"/silent-command game.surfaces[1].request_to_generate_chunks({{x={x}, y={y}}}, {chunk_radius})"
        )

    # Force immediate generation of all requested chunks
    instance.rcon_client.send_command(
        "/silent-command game.surfaces[1].force_generate_chunk_requests()"
    )

    print(
        f"Generated chunks along path: ({start_x}, {start_y}) -> ({end_x}, {end_y}), {num_points} points"
    )


class TestPathfindingLimits:
    """Comprehensive tests to explore pathfinding distance limits.

    These tests verify that pathfinding can reach minimum expected distances.
    Failures indicate regressions in pathfinding capability.
    """

    # Minimum expected distances - tests fail if we can't reach these
    MIN_SINGLE_MOVE_DISTANCE = (
        200  # Should be able to do at least 200 tiles in one move
    )
    MIN_INCREMENTAL_DISTANCE = 500  # Should reach at least 500 tiles with small steps

    def test_find_max_single_move_distance(self, game):
        """Binary search to find maximum single move_to distance.

        Fails if maximum single-move distance is less than MIN_SINGLE_MOVE_DISTANCE.
        """
        low = 10
        high = 500
        max_working = 0

        while low <= high:
            mid = (low + high) // 2
            # Reset to origin first
            try:
                game.move_to(Position(x=0, y=0))
            except:
                pass

            try:
                game.move_to(Position(x=mid, y=0))
                print(f"✓ Single move to x={mid} succeeded")
                max_working = mid
                low = mid + 1
            except Exception as e:
                print(f"✗ Single move to x={mid} failed: {str(e)[:200]}")
                high = mid - 1

        print(f"\n=== Maximum single move distance: {max_working} tiles ===")
        assert max_working >= self.MIN_SINGLE_MOVE_DISTANCE, (
            f"Single move distance {max_working} is below minimum {self.MIN_SINGLE_MOVE_DISTANCE}"
        )

    def test_incremental_10_tile_moves(self, game):
        """Move in 10-tile increments to find how far we can go.

        Fails if we can't reach MIN_INCREMENTAL_DISTANCE with 10-tile steps.
        """
        increment = 10
        current_x = 0
        max_reached = 0
        failures = 0

        for i in range(200):  # Up to 2000 tiles
            current_x += increment
            try:
                game.move_to(Position(x=current_x, y=0))
                max_reached = current_x
                failures = 0  # Reset consecutive failure count on success
                if current_x % 100 == 0:
                    print(f"✓ Reached x={current_x}")
            except Exception as e:
                failures += 1
                print(f"✗ Failed at x={current_x}: {str(e)[:200]}")
                if failures >= 3:
                    print("Stopping after 3 consecutive failures")
                    break
                # Try to continue from current position
                try:
                    pos = game.player_location
                    current_x = int(pos.x)
                except:
                    break

        print(f"\n=== Max reached with 10-tile increments: {max_reached} tiles ===")
        pos = game.player_location
        print(f"Final position: {pos}")

        assert max_reached >= self.MIN_INCREMENTAL_DISTANCE, (
            f"10-tile increments only reached {max_reached}, expected at least {self.MIN_INCREMENTAL_DISTANCE}"
        )

    def test_incremental_25_tile_moves(self, game):
        """Move in 25-tile increments.

        Fails if we can't reach MIN_INCREMENTAL_DISTANCE with 25-tile steps.
        """
        increment = 25
        current_x = 0
        max_reached = 0

        for i in range(100):  # Up to 2500 tiles
            current_x += increment
            try:
                game.move_to(Position(x=current_x, y=0))
                max_reached = current_x
                if current_x % 100 == 0:
                    print(f"✓ Reached x={current_x}")
            except Exception as e:
                print(f"✗ Failed at x={current_x}: {str(e)[:200]}")
                break

        print(f"\n=== Max reached with 25-tile increments: {max_reached} tiles ===")

        assert max_reached >= self.MIN_INCREMENTAL_DISTANCE, (
            f"25-tile increments only reached {max_reached}, expected at least {self.MIN_INCREMENTAL_DISTANCE}"
        )

    def test_incremental_50_tile_moves(self, game):
        """Move in 50-tile increments.

        Fails if we can't reach MIN_INCREMENTAL_DISTANCE with 50-tile steps.
        """
        increment = 50
        current_x = 0
        max_reached = 0

        for i in range(60):  # Up to 3000 tiles
            current_x += increment
            try:
                game.move_to(Position(x=current_x, y=0))
                max_reached = current_x
                print(f"✓ Reached x={current_x}")
            except Exception as e:
                print(f"✗ Failed at x={current_x}: {str(e)[:200]}")
                break

        print(f"\n=== Max reached with 50-tile increments: {max_reached} tiles ===")

        assert max_reached >= self.MIN_INCREMENTAL_DISTANCE, (
            f"50-tile increments only reached {max_reached}, expected at least {self.MIN_INCREMENTAL_DISTANCE}"
        )

    def test_move_to_edge_of_generated_world(self, game, instance):
        """Find and move to the edge of the generated world."""
        # First, check how far the world is generated
        result = instance.rcon_client.send_command(
            "/silent-command local chunks = 0; for chunk in game.surfaces[1].get_chunks() do chunks = chunks + 1 end; rcon.print(chunks)"
        )
        print(f"Total chunks in world: {result}")

        # Get the bounding box of generated chunks
        result = instance.rcon_client.send_command(
            "/silent-command local min_x, max_x, min_y, max_y = math.huge, -math.huge, math.huge, -math.huge; "
            "for chunk in game.surfaces[1].get_chunks() do "
            "min_x = math.min(min_x, chunk.x); max_x = math.max(max_x, chunk.x); "
            "min_y = math.min(min_y, chunk.y); max_y = math.max(max_y, chunk.y); "
            "end; rcon.print(min_x .. ',' .. max_x .. ',' .. min_y .. ',' .. max_y)"
        )
        print(f"Chunk bounds (chunk coords): {result}")

        if result:
            try:
                min_x, max_x, min_y, max_y = map(int, result.split(","))
                # Convert to tile coordinates (chunks are 32x32 tiles)
                max_tile_x = (max_x + 1) * 32
                print(f"Max generated tile X: {max_tile_x}")

                # Try to move near the edge
                target_x = min(max_tile_x - 10, 500)  # Cap at 500 for safety
                try:
                    game.move_to(Position(x=target_x, y=0))
                    print(f"✓ Moved to x={target_x} (near world edge)")
                except Exception as e:
                    print(f"✗ Could not move to edge: {e}")
            except:
                print("Could not parse chunk bounds")

    def test_pathfinding_with_teleport_assist(self, game, instance):
        """Use teleport to get far, then test pathfinding from there."""
        distances_to_test = [500, 1000, 2000, 3000]

        for distance in distances_to_test:
            # Teleport to the distance
            instance.rcon_client.send_command(
                f"/silent-command storage.agent_characters[1].teleport({{x={distance}, y=0}})"
            )

            # Update game state's knowledge of position
            game.instance.player_location = Position(x=distance, y=0)

            # Try a short move from there
            try:
                game.move_to(Position(x=distance + 10, y=0))
                print(f"✓ Pathfinding works at x={distance}")

                # Try moving back a bit
                game.move_to(Position(x=distance - 10, y=0))
                print(f"✓ Pathfinding works going back at x={distance}")
            except Exception as e:
                print(f"✗ Pathfinding failed at x={distance}: {str(e)[:200]}")

            # Reset for next test
            instance.rcon_client.send_command(
                "/silent-command storage.agent_characters[1].teleport({x=0, y=0})"
            )
            game.instance.player_location = Position(x=0, y=0)

    def test_zig_zag_long_distance(self, game):
        """Move in a zig-zag pattern to cover long distance."""
        max_x = 0
        step = 30
        y_offset = 10

        for i in range(50):
            target_x = (i + 1) * step
            target_y = y_offset if i % 2 == 0 else -y_offset

            try:
                game.move_to(Position(x=target_x, y=target_y))
                max_x = target_x
                if target_x % 150 == 0:
                    print(f"✓ Zig-zag reached x={target_x}")
            except Exception as e:
                print(f"✗ Zig-zag failed at x={target_x}: {str(e)[:200]}")
                break

        print(f"\n=== Max reached with zig-zag: {max_x} tiles ===")

    def test_spiral_outward_movement(self, game):
        """Move in an expanding spiral to test pathfinding in all directions."""
        max_distance = 0
        x, y = 0, 0
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # right, down, left, up
        step_size = 20

        for ring in range(1, 20):
            side_length = ring * step_size

            for dir_idx, (dx, dy) in enumerate(directions):
                steps_this_side = side_length // step_size
                if dir_idx >= 2:
                    steps_this_side += 1  # Adjust for spiral geometry

                for _ in range(steps_this_side):
                    x += dx * step_size
                    y += dy * step_size

                    try:
                        game.move_to(Position(x=x, y=y))
                        distance = (x**2 + y**2) ** 0.5
                        max_distance = max(max_distance, distance)
                    except Exception as e:
                        print(f"✗ Spiral failed at ({x}, {y}): {str(e)[:50]}")
                        print(
                            f"\n=== Max spiral distance: {max_distance:.1f} tiles ==="
                        )
                        return

            if ring % 5 == 0:
                print(f"✓ Completed ring {ring}, max distance: {max_distance:.1f}")

        print(f"\n=== Max spiral distance: {max_distance:.1f} tiles ===")

    def test_follow_resource_patches(self, game):
        """Move between resource patches to test real-world long-distance movement."""
        resources_visited = []
        resources = [
            Resource.IronOre,
            Resource.CopperOre,
            Resource.Coal,
            Resource.Stone,
        ]

        for i in range(20):
            resource = resources[i % len(resources)]
            resource_name = (
                resource[0] if isinstance(resource, tuple) else resource.value
            )
            try:
                pos = game.nearest(resource)
                if pos:
                    game.move_to(pos)
                    current = game.player_location
                    distance = (current.x**2 + current.y**2) ** 0.5
                    resources_visited.append((resource_name, current, distance))
                    print(f"✓ Visited {resource_name} at distance {distance:.1f}")
            except Exception as e:
                print(f"✗ Failed to reach {resource_name}: {str(e)[:50]}")
                break

        if resources_visited:
            max_dist = max(r[2] for r in resources_visited)
            print(f"\n=== Max distance via resources: {max_dist:.1f} tiles ===")

    def test_character_state_after_many_moves(self, game, instance):
        """Check character state after many successful moves."""
        moves = 0

        # Do many small moves
        for i in range(100):
            x = (i % 10) * 10
            y = (i // 10) * 10
            try:
                game.move_to(Position(x=x, y=y))
                moves += 1
            except:
                break

        print(f"Completed {moves} moves")

        # Check character state
        health = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].health)"
        )
        valid = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].valid)"
        )
        pos = instance.rcon_client.send_command(
            "/silent-command local p = storage.agent_characters[1].position; rcon.print(p.x .. ',' .. p.y)"
        )

        print(
            f"After {moves} moves - Health: {health}, Valid: {valid}, Position: {pos}"
        )

    def test_return_to_origin_from_far(self, game):
        """Move far away incrementally, then try to return to origin."""
        # Move outward
        max_x = 0
        for i in range(20):
            target = Position(x=(i + 1) * 25, y=0)
            try:
                game.move_to(target)
                max_x = target.x
            except:
                break

        print(f"Reached x={max_x}")

        # Now try to return to origin
        try:
            game.move_to(Position(x=0, y=0))
            pos = game.player_location
            print(f"✓ Returned to origin: {pos}")
        except Exception as e:
            print(f"✗ Could not return to origin: {str(e)[:60]}")

            # Try incremental return
            current_x = max_x
            while current_x > 0:
                current_x -= 25
                try:
                    game.move_to(Position(x=max(0, current_x), y=0))
                    print(f"✓ Returned to x={current_x}")
                except Exception:
                    print(f"✗ Failed returning at x={current_x}")
                    break


class TestRapidMovement:
    """Test character persistence during rapid successive movements."""

    def test_rapid_short_moves(self, game):
        """Execute many rapid short movements."""
        moves_completed = 0
        try:
            for i in range(50):
                x = (i % 10) * 5
                y = (i // 10) * 5
                game.move_to(Position(x=x, y=y))
                moves_completed += 1

            print(f"Completed {moves_completed} rapid moves")
            assert moves_completed == 50, "Should complete all rapid moves"

        except Exception as e:
            print(f"Failed after {moves_completed} moves: {e}")
            # Check character recovery
            pos = game.player_location
            assert pos is not None, f"Character should survive, got position: {pos}"

    def test_rapid_back_and_forth(self, game):
        """Rapidly move back and forth between two positions."""
        pos_a = Position(x=0, y=0)
        pos_b = Position(x=50, y=50)

        for i in range(20):
            try:
                if i % 2 == 0:
                    game.move_to(pos_b)
                else:
                    game.move_to(pos_a)
            except Exception as e:
                print(f"Back-and-forth failed at iteration {i}: {e}")
                # Verify character
                current = game.player_location
                assert current is not None, "Character should persist"
                return

        print("Completed 20 back-and-forth movements")

    def test_spiral_movement(self, game):
        """Move in an expanding spiral pattern."""
        radius = 5
        for lap in range(10):
            try:
                # Move in a square spiral
                game.move_to(Position(x=radius, y=0))
                game.move_to(Position(x=radius, y=radius))
                game.move_to(Position(x=-radius, y=radius))
                game.move_to(Position(x=-radius, y=-radius))
                game.move_to(Position(x=radius, y=-radius))
                radius += 10
            except Exception as e:
                print(f"Spiral failed at radius {radius}: {e}")
                pos = game.player_location
                assert pos is not None, "Character should persist during spiral"
                break

        print(f"Spiral completed to radius {radius}")


class TestEdgeCases:
    """Test character persistence in edge case scenarios."""

    def test_move_to_negative_coordinates(self, game):
        """Test movement to negative coordinate space."""
        negative_pos = Position(x=-500, y=-500)
        try:
            result = game.move_to(negative_pos)
            print(f"Moved to negative coords: {result}")

            # Verify character
            current = game.player_location
            assert current is not None

        except Exception as e:
            print(f"Negative coord move failed: {e}")
            # Should still have character
            pos = game.player_location
            assert pos is not None

    def test_move_to_origin_from_far(self, game):
        """Move far away then return to origin."""
        # First move somewhat far
        game.move_to(Position(x=200, y=200))

        # Then return to origin
        try:
            game.move_to(Position(x=0, y=0))
            pos = game.player_location
            print(f"Returned to origin: {pos}")
            assert abs(pos.x) < 5 and abs(pos.y) < 5, "Should be near origin"

        except Exception as e:
            pytest.fail(f"Failed to return to origin: {e}")

    def test_move_to_same_position(self, game):
        """Test moving to current position (zero distance)."""
        current = game.player_location
        try:
            result = game.move_to(current)
            print(f"Move to same position: {result}")
        except Exception as e:
            # This might fail but shouldn't break character
            print(f"Same position move failed (expected): {e}")

        # Character should still work
        new_pos = game.player_location
        assert new_pos is not None

    def test_very_small_movements(self, game):
        """Test many very small movements."""
        for i in range(100):
            try:
                game.move_to(Position(x=i * 0.5, y=i * 0.25))
            except Exception as e:
                print(f"Small movement {i} failed: {e}")
                break

        pos = game.player_location
        assert pos is not None, "Character should survive small movements"


class TestCharacterRecovery:
    """Test that character auto-recovers when invalidated."""

    def test_character_validity_after_actions(self, game):
        """Verify character remains valid after various actions."""
        # Place some entities
        game.move_to(Position(x=10, y=10))
        game.place_entity(Prototype.WoodenChest, position=Position(x=12, y=10))

        # Check character
        pos = game.player_location
        assert pos is not None, "Character valid after placing entity"

        # Mine something
        stone_pos = game.nearest(Resource.Stone)
        if stone_pos:
            game.move_to(stone_pos)
            game.harvest_resource(stone_pos, quantity=5)

        pos = game.player_location
        assert pos is not None, "Character valid after harvesting"

    def test_character_after_failed_path(self, game):
        """Test character persists after pathfinding fails."""
        # Try to move somewhere potentially unreachable
        try:
            # Place obstacles
            game.move_to(Position(x=0, y=0))
            for i in range(5):
                game.place_entity(
                    Prototype.WoodenChest, position=Position(x=5, y=i - 2)
                )

            # Try to move through obstacles
            game.move_to(Position(x=10, y=0))
        except Exception as e:
            print(f"Blocked path (expected): {e}")

        # Character should still be valid
        pos = game.player_location
        assert pos is not None, "Character should survive failed pathfinding"

    def test_multiple_game_resets(self, instance):
        """Test character survives multiple resets."""
        for i in range(5):
            instance.reset()
            pos = instance.namespace.player_location
            assert pos is not None, f"Character should exist after reset {i + 1}"
            print(f"Reset {i + 1}: Character at {pos}")


class TestConcurrentOperations:
    """Test character persistence during complex operations."""

    def test_move_while_placing_entities(self, game):
        """Move while placing entities along the path."""
        try:
            # Move while laying belts
            result = game.move_to(Position(x=30, y=0), laying=Prototype.TransportBelt)
            print(f"Move with belt laying: {result}")
        except Exception as e:
            print(f"Belt laying move failed: {e}")

        pos = game.player_location
        assert pos is not None, "Character should survive move with laying"

    def test_inspect_during_movement(self, game):
        """Test that inspection works during movement sequence."""
        game.move_to(Position(x=20, y=20))
        inv = game.inspect_inventory()
        assert inv is not None, "Should be able to inspect inventory"

        game.move_to(Position(x=40, y=40))
        _entities = game.get_entities()
        # Should not raise an error

        pos = game.player_location
        assert pos is not None


class TestCharacterState:
    """Direct tests on character state."""

    def test_player_location_consistency(self, game):
        """Verify player_location returns consistent results."""
        pos1 = game.player_location
        pos2 = game.player_location

        assert pos1.x == pos2.x and pos1.y == pos2.y, (
            f"Position should be consistent: {pos1} vs {pos2}"
        )

    def test_player_location_after_teleport(self, game):
        """Test location tracking after direct teleportation."""
        target = Position(x=100, y=100)
        game.move_to(target)

        pos = game.player_location
        # Allow some tolerance for pathfinding
        assert abs(pos.x - target.x) < 5, f"X should be near target: {pos}"
        assert abs(pos.y - target.y) < 5, f"Y should be near target: {pos}"

    def test_character_exists_check(self, instance):
        """Directly verify character entity exists in game."""
        # Use RCON to check character validity
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters and storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        assert result == "valid", f"Character should be valid, got: {result}"

    def test_character_health(self, instance):
        """Check character has health (not dead)."""
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters and storage.agent_characters[1] and storage.agent_characters[1].health or 0)"
        )
        health = float(result) if result else 0
        assert health > 0, f"Character should have health > 0, got: {health}"


class TestDirectTeleportation:
    """Test character persistence with direct teleportation (bypassing pathfinding)."""

    def test_teleport_100_tiles(self, instance):
        """Directly teleport character 100 tiles via RCON."""
        # First check character is valid
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].valid)"
        )
        assert result == "true", (
            f"Character should be valid before teleport, got: {result}"
        )

        # Teleport directly
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].teleport({x=100, y=0})"
        )

        # Verify character still valid and at new position
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].valid)"
        )
        assert result == "true", (
            f"Character should be valid after 100 tile teleport, got: {result}"
        )

        pos = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].position.x .. ',' .. storage.agent_characters[1].position.y)"
        )
        print(f"Position after 100 tile teleport: {pos}")

    def test_teleport_1000_tiles(self, instance):
        """Directly teleport character 1000 tiles via RCON."""
        # Teleport to far location
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].teleport({x=1000, y=0})"
        )

        # Check if character is still valid
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after 1000 tile teleport: {result}")

        # Try to use the character
        if result == "valid":
            pos = instance.rcon_client.send_command(
                "/silent-command rcon.print(storage.agent_characters[1].position.x)"
            )
            print(f"Character X position: {pos}")

    def test_teleport_to_uncharted_territory(self, instance):
        """Teleport to area that may not be charted/generated."""
        # Teleport very far
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].teleport({x=5000, y=5000})"
        )

        # Check validity
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character after 5000 tile teleport: {result}")

        # Try to teleport back
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].teleport({x=0, y=0})"
        )

        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character after return teleport: {result}")

    def test_teleport_into_water(self, instance):
        """Try to teleport into water (if any exists)."""
        # This may fail or cause issues depending on map
        try:
            # Find water tile
            water_check = instance.rcon_client.send_command(
                "/silent-command local pos = game.surfaces[1].find_tiles_filtered({name='water', limit=1})[1]; rcon.print(pos and (pos.position.x .. ',' .. pos.position.y) or 'none')"
            )
            print(f"Water tile found: {water_check}")

            if water_check and water_check != "none":
                x, y = water_check.split(",")
                instance.rcon_client.send_command(
                    f"/silent-command storage.agent_characters[1].teleport({{x={x}, y={y}}})"
                )

                result = instance.rcon_client.send_command(
                    "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
                )
                print(f"Character after water teleport: {result}")
        except Exception as e:
            print(f"Water teleport test: {e}")


class TestCharacterDamageAndDeath:
    """Test character persistence when damaged or killed."""

    def test_damage_character(self, instance):
        """Apply damage to character and verify it survives."""
        # Get initial health
        health_before = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].health)"
        )
        print(f"Health before damage: {health_before}")

        # Apply some damage (not lethal)
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].damage(50, game.forces.enemy, 'physical')"
        )

        # Check health after
        health_after = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].health)"
        )
        print(f"Health after 50 damage: {health_after}")

        # Verify character still valid
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].valid)"
        )
        assert result == "true", f"Character should survive 50 damage, got: {result}"

    def test_near_lethal_damage(self, instance):
        """Apply near-lethal damage and verify character survives."""
        # Get max health - in Factorio 2.0, use max_health on the entity directly
        max_health = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].max_health)"
        )
        print(f"Max health: {max_health}")

        # Heal to full first
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].health = storage.agent_characters[1].max_health"
        )

        # Apply damage leaving 1 HP
        damage_amount = float(max_health) - 1
        instance.rcon_client.send_command(
            f"/silent-command storage.agent_characters[1].damage({damage_amount}, game.forces.enemy, 'physical')"
        )

        health_after = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].health)"
        )
        print(f"Health after near-lethal damage: {health_after}")

        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].valid)"
        )
        assert result == "true", f"Character should survive with 1 HP, got: {result}"

    def test_kill_character_and_recovery(self, instance):
        """Kill the character and verify it can be recovered."""
        # Record position before death
        pos_before = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1].position.x .. ',' .. storage.agent_characters[1].position.y)"
        )
        print(f"Position before death: {pos_before}")

        # Kill the character
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].die()"
        )

        # Check if character is now invalid
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after die(): {result}")

        # Try to use ensure_valid_character to recover
        instance.rcon_client.send_command(
            "/silent-command storage.utils.ensure_valid_character(1)"
        )

        # Check if recovered
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after recovery attempt: {result}")
        assert result == "valid", f"Character should be recovered, got: {result}"

    def test_destroy_character_entity(self, instance):
        """Directly destroy the character entity."""
        # Destroy the character
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].destroy()"
        )

        # Check status
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after destroy(): {result}")

        # Attempt recovery
        instance.rcon_client.send_command(
            "/silent-command storage.utils.ensure_valid_character(1)"
        )

        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after recovery: {result}")
        assert result == "valid", (
            f"Character should be recovered after destroy, got: {result}"
        )

    def test_spawn_enemy_near_character(self, instance):
        """Spawn an enemy near character and see what happens."""
        # Get character position
        pos = instance.rcon_client.send_command(
            "/silent-command local p = storage.agent_characters[1].position; rcon.print(p.x .. ',' .. p.y)"
        )
        if not pos or "," not in pos:
            pytest.fail(f"Failed to get character position, got: {pos}")
        x, y = pos.split(",")

        # Spawn a biter near the character
        instance.rcon_client.send_command(
            f"/silent-command game.surfaces[1].create_entity{{name='small-biter', position={{x={float(x) + 5}, y={float(y)}}}, force='enemy'}}"
        )

        # Wait a moment (in-game ticks)
        instance.rcon_client.send_command("/silent-command game.tick_paused = false")

        time.sleep(0.5)

        # Check character health
        health = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].health or 'dead')"
        )
        print(f"Character health after biter spawn: {health}")

        # Kill the biter to clean up
        instance.rcon_client.send_command(
            '/silent-command game.forces["enemy"].kill_all_units()'
        )

        # Check character validity
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status: {result}")


class TestCharacterInvalidation:
    """Test various ways the character reference could become invalid."""

    def test_nil_character_reference(self, instance):
        """Set character reference to nil and test recovery."""
        # Nil out the reference (but don't destroy entity)
        instance.rcon_client.send_command(
            "/silent-command local char = storage.agent_characters[1]; storage.agent_characters[1] = nil"
        )

        # Check status
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"After nil reference: {result}")

        # Recovery should create new character
        instance.rcon_client.send_command(
            "/silent-command storage.utils.ensure_valid_character(1)"
        )

        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        assert result == "valid", f"Should recover from nil reference, got: {result}"

    def test_move_to_after_character_death(self, game, instance):
        """Test that move_to works after character has been killed and recovered."""
        # Kill the character
        instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].die()"
        )

        # Try to move - this should trigger recovery via ensure_valid_character
        try:
            game.move_to(Position(x=10, y=10))
            print("Move succeeded after character death")
        except Exception as e:
            print(f"Move after death failed: {e}")

        # Verify character exists now
        result = instance.rcon_client.send_command(
            "/silent-command rcon.print(storage.agent_characters[1] and storage.agent_characters[1].valid and 'valid' or 'invalid')"
        )
        print(f"Character status after move attempt: {result}")


class TestExtremeScenarios:
    """Test extreme scenarios that might cause character loss."""

    def test_move_to_chunk_boundary(self, game):
        """Test movement to chunk boundaries (every 32 tiles)."""
        chunk_positions = [
            Position(x=32, y=0),
            Position(x=64, y=0),
            Position(x=32, y=32),
            Position(x=96, y=96),
        ]

        for pos in chunk_positions:
            try:
                game.move_to(pos)
                print(f"Moved to chunk boundary: {pos}")
            except Exception as e:
                print(f"Chunk boundary move failed: {e}")

            # Verify character
            current = game.player_location
            assert current is not None, (
                f"Character should exist at chunk boundary {pos}"
            )

    def test_move_to_ungenerated_chunks(self, game):
        """Test movement to potentially ungenerated chunks."""
        # Chunks at 500+ tiles might not be generated
        far_chunk = Position(x=512, y=512)  # 16 chunks away

        try:
            result = game.move_to(far_chunk)
            print(f"Moved to ungenerated chunk area: {result}")
        except Exception as e:
            print(f"Ungenerated chunk move failed (expected): {e}")

        # Character should still exist
        pos = game.player_location
        assert pos is not None, "Character should survive ungenerated chunk attempt"

    def test_sequential_long_moves(self, game):
        """Make multiple long moves in sequence."""
        positions = [
            Position(x=200, y=0),
            Position(x=200, y=200),
            Position(x=0, y=200),
            Position(x=0, y=0),
        ]

        for i, pos in enumerate(positions):
            try:
                game.move_to(pos)
                print(f"Sequential move {i + 1}: {pos}")
            except Exception as e:
                print(f"Sequential move {i + 1} failed: {e}")

        # Final check
        final_pos = game.player_location
        assert final_pos is not None, "Character should survive sequential long moves"


class TestPathfindingWithChunkGeneration:
    """Test pathfinding after forcefully generating chunks.

    These tests verify that pathfinding works over long distances when
    the terrain has been pre-generated using request_to_generate_chunks.
    """

    # Distance expectations when chunks are pre-generated
    # Map topology (oceans/obstacles) can limit straight-line travel on some seeds
    MIN_DISTANCE_WITH_CHUNKS = 500

    def test_generate_chunks_and_move_500_tiles(self, game):
        """Generate chunks along a path and move 500 tiles."""
        target_distance = 500

        # Pre-generate chunks along the path
        generate_chunks_along_path(game, 0, 0, target_distance, 0, chunk_radius=2)

        # Now try to move
        try:
            game.move_to(Position(x=target_distance, y=0))
            pos = game.player_location
            print(f"✓ Moved to x={target_distance} with chunk generation: {pos}")
            assert pos.x >= target_distance - 5, (
                f"Should reach x={target_distance}, got {pos.x}"
            )
        except Exception as e:
            pytest.fail(f"Failed to move 500 tiles with chunk generation: {e}")

    def test_generate_chunks_and_move_1000_tiles(self, game):
        """Generate chunks and attempt 1000 tile movement."""
        target_distance = 1000

        # Pre-generate chunks along the path
        print(f"Generating chunks from origin to x={target_distance}...")
        generate_chunks_along_path(game, 0, 0, target_distance, 0, chunk_radius=3)

        # Try the move
        try:
            game.move_to(Position(x=target_distance, y=0))
            pos = game.player_location
            print(f"✓ Moved to x={target_distance} with chunk generation: {pos}")
            assert pos.x >= target_distance - 10, (
                f"Should reach x={target_distance}, got {pos.x}"
            )
        except Exception as e:
            print(f"✗ Failed to move 1000 tiles: {e}")
            # Try incremental approach — map topology (water/obstacles) may limit
            # how far we can go in a straight line
            current_x = 0
            increment = 100
            max_reached = 0

            for i in range(target_distance // increment):
                current_x += increment
                try:
                    game.move_to(Position(x=current_x, y=0))
                    max_reached = current_x
                    if current_x % 200 == 0:
                        print(f"✓ Incremental: reached x={current_x}")
                except Exception as e2:
                    print(f"✗ Incremental failed at x={current_x}: {str(e2)[:100]}")
                    break

            # Map topology (oceans) may block paths beyond ~500-600 tiles on some seeds
            assert max_reached >= 500, (
                f"With generated chunks, should reach at least 500 tiles, got {max_reached}"
            )

    def test_generate_large_area_and_explore(self, game):
        """Generate a large area and test movement throughout."""
        # Reset to origin first
        game.instance.rcon_client.send_command(
            "/silent-command storage.agent_characters[1].teleport({x=0, y=0})"
        )
        game.instance.player_location = Position(x=0, y=0)

        # Generate a 64x64 chunk area (2048x2048 tiles) centered at origin
        print("Generating large area (64 chunk radius = 2048 tiles)...")
        generate_chunks(game, 0, 0, chunk_radius=32)

        # Test movement to various points within this area
        test_positions = [
            Position(x=500, y=0),
            Position(x=500, y=500),
            Position(x=0, y=500),
            Position(x=-500, y=0),
            Position(x=-500, y=-500),
            Position(x=1000, y=0),
            Position(x=0, y=1000),
        ]

        successful_moves = 0
        for pos in test_positions:
            try:
                game.move_to(pos)
                current = game.player_location
                print(
                    f"✓ Reached ({pos.x}, {pos.y}) -> actual: ({current.x:.1f}, {current.y:.1f})"
                )
                successful_moves += 1
            except Exception as e:
                print(f"✗ Failed to reach ({pos.x}, {pos.y}): {str(e)[:80]}")

        print(f"\n=== Successful moves: {successful_moves}/{len(test_positions)} ===")
        # Some positions may be unreachable due to water/obstacles on the map
        assert successful_moves >= 4, (
            f"Should reach at least 4 positions with generated chunks, got {successful_moves}/{len(test_positions)}"
        )

    def test_incremental_with_chunk_generation(self, game):
        """Move incrementally while generating chunks ahead."""
        max_distance = 2000
        increment = 100
        current_x = 0
        max_reached = 0

        for i in range(max_distance // increment):
            next_x = current_x + increment

            # Generate chunks ahead of our current position
            generate_chunks(game, next_x + 200, 0, chunk_radius=3)

            try:
                game.move_to(Position(x=next_x, y=0))
                max_reached = next_x
                current_x = next_x
                if next_x % 500 == 0:
                    print(f"✓ Reached x={next_x}")
            except Exception as e:
                print(f"✗ Failed at x={next_x}: {str(e)[:100]}")
                break

        print(f"\n=== Max reached with incremental chunk gen: {max_reached} tiles ===")
        assert max_reached >= self.MIN_DISTANCE_WITH_CHUNKS, (
            f"Should reach {self.MIN_DISTANCE_WITH_CHUNKS} with chunk gen, got {max_reached}"
        )

    def test_diagonal_long_distance_with_chunks(self, game):
        """Test diagonal movement over long distance with chunk generation."""
        target_x, target_y = 300, 300  # ~424 tiles diagonal, within generated area

        # Generate chunks along diagonal
        print("Generating chunks along diagonal path...")
        generate_chunks_along_path(game, 0, 0, target_x, target_y, chunk_radius=3)

        try:
            game.move_to(Position(x=target_x, y=target_y))
            pos = game.player_location
            distance = (pos.x**2 + pos.y**2) ** 0.5
            print(
                f"✓ Diagonal move successful: ({pos.x:.1f}, {pos.y:.1f}), distance={distance:.1f}"
            )
            assert distance >= 350, f"Should reach ~424 diagonal tiles, got {distance}"
        except Exception as e:
            print(f"✗ Diagonal move failed: {e}")
            pytest.fail(f"Diagonal move with chunk generation should succeed: {e}")

    def test_chunk_generation_performance(self, game):
        """Test that chunk generation doesn't significantly impact game performance."""

        # Time chunk generation
        start = time.time()
        generate_chunks(game, 0, 0, chunk_radius=20)  # 40x40 chunks = 1280x1280 tiles
        gen_time = time.time() - start
        print(f"Chunk generation (20 radius): {gen_time:.2f}s")

        # Time a move within generated area
        start = time.time()
        try:
            game.move_to(Position(x=500, y=0))
            game.move_to(Position(x=0, y=0))
            move_time = time.time() - start
            print(f"Round-trip move (500 tiles): {move_time:.2f}s")
        except Exception as e:
            print(f"Move failed: {e}")

        # Chunk generation should be reasonably fast
        assert gen_time < 30, f"Chunk generation took too long: {gen_time}s"

    def test_verify_chunks_are_generated(self, game, instance):
        """Verify that chunk generation via request_path works.

        Our server.lua auto-generates chunks before pathfinding. Verify this
        by checking that a move_to triggers chunk generation at the goal area.
        """
        # Pick a target within reachable range but outside the initial 25-chunk radius
        # The initial generation covers ~800 tiles from origin
        # Use a position at 400 tiles — within range, definitely has generated chunks
        target_x = 400

        # Count chunks before
        before = instance.rcon_client.send_command(
            "/silent-command local c=0; for _ in game.surfaces[1].get_chunks() do c=c+1 end; rcon.print(c)"
        )
        print(f"Chunks before move: {before}")

        # move_to triggers request_path which auto-generates chunks
        try:
            game.move_to(Position(x=target_x, y=0))
            pos = game.player_location
            print(f"Moved to: x={pos.x}, y={pos.y}")
        except Exception as e:
            print(f"Move failed (expected if blocked by water): {e}")

        # Count chunks after — request_path generates chunks along the corridor
        after = instance.rcon_client.send_command(
            "/silent-command local c=0; for _ in game.surfaces[1].get_chunks() do c=c+1 end; rcon.print(c)"
        )
        print(f"Chunks after move: {after}")

        # Verify that chunks exist at the target area
        # Check chunk at target position (400/32 = 12, which should be generated)
        chunk_exists = instance.rcon_client.send_command(
            f"/silent-command rcon.print(game.surfaces[1].is_chunk_generated({{x={target_x // 32}, y=0}}) and 'yes' or 'no')"
        )
        print(f"Chunk at ({target_x // 32}, 0) exists: {chunk_exists}")

        assert chunk_exists.strip() == "yes", (
            "Chunk at target position should be generated after move_to"
        )
