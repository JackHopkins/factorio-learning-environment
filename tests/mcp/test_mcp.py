"""
Integration tests for MCP tools in the Factorio environment.
Tests the happy path for each tool against a real server.
"""
import base64
import io
import os

import pytest
import asyncio
import json
from pathlib import Path
from typing import List, Tuple
from concurrent import futures
from unittest.mock import patch, MagicMock

from pathlib import Path
from PIL import Image as PILImage

from fle.commons.cluster_ips import get_local_container_ips
from fle.env.entities import Position
from fle.env.protocols.mcp.tools import (
    render,
    entities,
    inventory,
    execute,
    status,
    get_entity_names,
    position,
    get_recipe,
    schema,
    manual
)
from fle.env.protocols.mcp.init import state, initialize_session
from fle.env.instance import FactorioInstance

from fastmcp.tools.tool import ToolResult
from mcp.types import ImageContent, TextContent
from dotenv import load_dotenv

load_dotenv()

class TestMCPTools:
    """Integration tests for MCP tools"""

    @classmethod
    def setup_class(cls):
        """Setup test fixtures once for all tests"""
        cls.instances = cls.create_factorio_instances()
        cls.test_instance = cls.instances[0] if cls.instances else None

    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests"""
        if cls.instances:
            for instance in cls.instances:
                try:
                    instance.close()
                except:
                    pass

    @staticmethod
    def create_factorio_instances() -> List[FactorioInstance]:
        """Create Factorio instances in parallel from local servers"""

        def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
            ip, udp_port, tcp_port = params
            try:
                instance = FactorioInstance(
                    address=ip,
                    tcp_port=tcp_port,
                    bounding_box=200,
                    fast=True,
                    cache_scripts=False,
                    inventory={},
                )
            except Exception as e:
                raise e
            instance.set_speed(100)
            return instance

        # Mock or get actual server details
        # For testing, you might want to mock this or use test containers
        ips, udp_ports, tcp_ports = get_local_container_ips()
        with futures.ThreadPoolExecutor() as executor:
            return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))

    @pytest.fixture(autouse=True)
    async def setup_state(self):
        """Setup state before each test"""
        # Initialize state with test instance
        if self.test_instance:
            state.active_server = self.test_instance
            state.available_servers = {
                self.test_instance.tcp_port: MagicMock(
                    name="TestServer",
                    address="127.0.0.1",
                    tcp_port=self.test_instance.tcp_port,
                )
            }
            # Initialize VCS if needed
            await initialize_session(None)
        yield
        # Cleanup after each test
        state.active_server = None
        state.available_servers = {}

    @pytest.mark.asyncio
    async def test_render(self):
        """Test render tool renders the current factory state"""
        DISPLAY_IMAGES = os.getenv('DISPLAY_TEST_IMAGES', 'false').lower() == 'true'

        await status.run({})
        # Test with default parameters
        result = await render.run({})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]

        if hasattr(first_content, 'type'):
            if first_content.type == 'image':
                assert hasattr(first_content, 'data')
                assert hasattr(first_content, 'mimeType')
                assert first_content.mimeType == 'image/png'

                # Display the image if requested
                if DISPLAY_IMAGES:
                    image_data = base64.b64decode(first_content.data)
                    img = PILImage.open(io.BytesIO(image_data))
                    print(f"\nImage dimensions: {img.size}, mode: {img.mode}")
                    img.show()  # This creates a temp file and opens it

            elif first_content.type == 'text':
                assert hasattr(first_content, 'text')
                print(f"\nReceived text response: {first_content.text}")
                assert "No active Factorio server connection" in first_content.text

        # Test with custom center coordinates
        result_custom = await render.run({"center_x": 10.0, "center_y": 10.0})
        assert result_custom is not None
        assert isinstance(result_custom, ToolResult)

    @pytest.mark.asyncio
    async def test_entities(self):
        """Test entities tool retrieves entities from the map"""
        await status.run({})

        # Test with default parameters
        result = await entities.run({})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]
        assert hasattr(first_content, 'text')
        text_result = first_content.text
        assert "Error" not in text_result or text_result == "[]"  # Empty list is valid

        # Test with custom parameters
        result_custom = await entities.run({"center_x": 50.0, "center_y": 50.0, "radius": 100.0})
        assert result_custom is not None
        assert isinstance(result_custom, ToolResult)

    @pytest.mark.asyncio
    async def test_inventory(self):
        """Test inventory tool retrieves current inventory"""
        await status.run({})

        result = await inventory.run({})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]
        assert hasattr(first_content, 'text')
        text_result = first_content.text
        assert "Error" not in text_result
        # Inventory should be a string representation of dict or list
        # Could be empty {} or [] which is valid

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test execute tool runs Python code and commits result"""
        await status.run({})

        # Simple code that should work
        test_code = """
# Get player position
pos = player_location
print(f"Player is at: {pos}")
"""
        result = await execute.run({"code": test_code})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]
        assert hasattr(first_content, 'text')
        text_result = first_content.text
        assert "[commit" in text_result  # Should include commit ID

        # Verify state file was created
        state_file = Path("/tmp/factorio_game_state.json")
        if state_file.exists():
            with open(state_file, 'r') as f:
                game_state = json.load(f)
                assert 'inventory' in game_state
                assert 'entities' in game_state
                assert 'score' in game_state

    @pytest.mark.asyncio
    async def test_status(self):
        """Test status tool checks server connection"""
        result = await status.run({})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]
        assert hasattr(first_content, 'text')
        text_result = first_content.text
        assert "Connected to Factorio server" in text_result or "Initializing" in text_result

    @pytest.mark.asyncio
    async def test_get_entity_names(self):
        """Test get_entity_names retrieves available entity prototypes"""
        await status.run({})

        result = await get_entity_names.run({})
        assert result is not None
        assert isinstance(result, ToolResult)

        # Check if we have structured content (list of names)
        if result.structured_content is not None:
            assert isinstance(result.structured_content, list)
            if result.structured_content:
                assert all(isinstance(name, str) for name in result.structured_content)
        else:
            # Fall back to checking text content
            assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_position(self):
        """Test position tool gets player position"""
        await status.run({})

        result = await position.run({})
        assert result is not None
        assert isinstance(result, ToolResult)

        # Position returns a Position object, check structured content
        if result.structured_content is not None:
            pos_data = result.structured_content
            if isinstance(pos_data, dict):
                # Wrapped result
                if 'result' in pos_data:
                    pos_data = pos_data['result']
                assert 'x' in pos_data
                assert 'y' in pos_data
                assert isinstance(pos_data['x'], (int, float))
                assert isinstance(pos_data['y'], (int, float))

    @pytest.mark.asyncio
    async def test_get_recipe(self):
        """Test get_recipe retrieves recipe details"""
        await status.run({})

        # First get available recipes
        entity_names_result = await get_entity_names.run({})
        entity_names = []

        if entity_names_result.structured_content:
            entity_names = entity_names_result.structured_content['result']

        if entity_names:
            # Test with first available recipe
            test_recipe_name = entity_names[0]
            result = await get_recipe.run({"name": test_recipe_name})
            assert result is not None
            assert isinstance(result, ToolResult)

            if result.structured_content and isinstance(result.structured_content, dict):
                recipe_data = result.structured_content
                if 'result' in recipe_data:
                    recipe_data = recipe_data['result']
                assert 'name' in recipe_data
                assert 'ingredients' in recipe_data
                assert 'results' in recipe_data
                assert 'energy_required' in recipe_data
            else:
                # Check text content for "not found"
                first_content = result.content[0]
                assert "not found" in first_content.text

        # Test with non-existent recipe
        try:
            result_invalid = await get_recipe.run({"name": "non_existent_recipe_xyz"})
        except Exception as e:
            assert isinstance(e, ValueError)

    @pytest.mark.asyncio
    async def test_schema(self):
        """Test schema tool returns API documentation"""
        await status.run({})

        result = await schema.run({})
        assert result is not None
        assert isinstance(result, ToolResult)
        assert len(result.content) > 0

        first_content = result.content[0]
        assert hasattr(first_content, 'text')
        text_result = first_content.text
        assert len(text_result) > 100  # Should have substantial documentation
        # Should contain type or entity information
        assert any(keyword in text_result.lower() for keyword in ['type', 'entity', 'class', 'def'])

    @pytest.mark.asyncio
    async def test_manual(self):
        """Test manual tool returns method documentation"""
        await status.run({})

        # Test with a common method name
        test_methods = ['move_to', 'place_entity']

        for method_name in test_methods:
            result = await manual.run({"name": method_name})
            assert result is not None
            assert isinstance(result, ToolResult)
            assert len(result.content) > 0

            first_content = result.content[0]
            assert hasattr(first_content, 'text')
            text_result = first_content.text

            # Either valid documentation or error message
            if "Error" in text_result:
                assert "Available tools" in text_result
            else:
                assert len(text_result) > 50  # Should have some documentation
                break  # Found at least one valid method


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])