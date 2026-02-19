"""
Integration tests for MCP resources in the Factorio environment.
Tests the happy path for each resource against a real server.
"""

import base64
import io
import os
import json
from typing import List, Tuple
from concurrent import futures
from unittest.mock import MagicMock

import pytest
from PIL import Image as PILImage

# Skip all tests in this module if fastmcp is not installed
import importlib.util

_FASTMCP_AVAILABLE = importlib.util.find_spec("fastmcp") is not None

pytestmark = pytest.mark.skipif(
    not _FASTMCP_AVAILABLE, reason="fastmcp is not installed"
)

from fle.env.instance import FactorioInstance

if _FASTMCP_AVAILABLE:
    from fle.commons.cluster_ips import get_local_container_ips
    from fle.env.protocols._mcp.resources import (
        render_at,
        entities,
        inventory,
        position,
        recipe,
        manual,
        schema,
        status,
        prototypes,
    )
    from fle.env.protocols._mcp.tools import reconnect
    from fle.env.protocols._mcp.init import state, initialize_session
    from mcp.types import ImageContent

from dotenv import load_dotenv

load_dotenv()


class TestMCPResources:
    """Integration tests for MCP resources"""

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
    async def test_render_with_position_default(self):
        """Test render_with_position resource with default position"""
        # Ensure connection
        await reconnect.run({})

        # Create resource with default parameters
        resource = await render_at.create_resource(
            "fle://render/", {"center_x": "0", "center_y": "0"}
        )

        result = await resource.read()
        assert result is not None

        # Check if it's image content
        if isinstance(result, ImageContent):
            assert result.type == "image"
            assert result.mimeType == "image/png"
            assert hasattr(result, "data")

            # Optionally display the image
            if os.getenv("DISPLAY_TEST_IMAGES", "false").lower() == "true":
                image_data = base64.b64decode(result.data)
                img = PILImage.open(io.BytesIO(image_data))
                print(f"\nImage dimensions: {img.size}, mode: {img.mode}")
                # img.show()
        elif isinstance(result, (str, bytes)):
            print(f"Render returned: {type(result)}")

    @pytest.mark.asyncio
    async def test_render_with_position_custom(self):
        """Test render_with_position with custom center coordinates"""
        await reconnect.run({})

        # Create resource with custom coordinates
        resource = await render_at.create_resource(
            "fle://render/", {"center_x": "10.0", "center_y": "10.0"}
        )

        result = await resource.read()
        assert result is not None

    @pytest.mark.asyncio
    async def test_entities_resource_default(self):
        """Test entities resource with default parameters"""
        await reconnect.run({})

        # Create resource with default parameters
        resource = await entities.create_resource(
            "fle://entities/",
            {"center_x": "default", "center_y": "default", "radius": "default"},
        )

        result = await resource.read()
        result = json.loads(result)
        assert result is not None
        assert isinstance(result, list)

        # Check structure if entities exist
        if result:
            first_entity = result[0]
            assert isinstance(first_entity, dict)

    @pytest.mark.asyncio
    async def test_entities_resource_custom(self):
        """Test entities resource with custom parameters"""
        await reconnect.run({})

        # Create resource with specific coordinates and radius
        resource = await entities.create_resource(
            "fle://entities/",
            {"center_x": "50.0", "center_y": "50.0", "radius": "100.0"},
        )

        result = await resource.read()
        assert result is not None
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_inventory_resource(self):
        """Test inventory resource retrieves current inventory"""
        await reconnect.run({})

        # Create resource - no parameters needed
        resource = inventory

        result = await resource.read()
        assert result is not None
        assert result[0] == "{"
        # Inventory should be a dict, could be empty {}

    @pytest.mark.asyncio
    async def test_position_resource(self):
        """Test position resource gets player position"""
        await reconnect.run({})

        # Create resource - no parameters needed
        resource = position

        result = await resource.read()
        result = json.loads(result)
        assert result is not None
        assert isinstance(result, dict)
        assert "x" in result
        assert "y" in result
        assert isinstance(result["x"], (int, float))
        assert isinstance(result["y"], (int, float))

    @pytest.mark.asyncio
    async def test_entity_names_resource(self):
        """Test entity_names resource retrieves available entity prototypes"""
        await reconnect.run({})

        # Create resource - no parameters needed
        resource = prototypes  # .create_resource('fle://entity-names', {})

        result = await resource.read()
        result = json.loads(result)
        assert result is not None
        assert isinstance(result, list)

        if result:
            # All items should be strings
            assert all(isinstance(name, str) for name in result)

    @pytest.mark.asyncio
    async def test_recipe_resource(self):
        """Test recipe resource with specific recipe name"""
        await reconnect.run({})

        # First get available recipes
        names_resource = prototypes
        available_names = await names_resource.read()
        available_names = json.loads(available_names)

        if available_names and len(available_names) > 0:
            # Test with first available recipe
            test_recipe_name = available_names[0]

            # Create resource with recipe name
            resource = await recipe.create_resource(
                "fle://recipe/", {"name": test_recipe_name}
            )

            result = await resource.read()
            assert result is not None
            assert isinstance(result, str)

            # Check if it's valid JSON or error message
            if "not found" not in result:
                # Should be valid JSON
                recipe_data = json.loads(result)
                assert "name" in recipe_data
                assert "ingredients" in recipe_data
                assert "results" in recipe_data
                assert "energy_required" in recipe_data

        # Test with non-existent recipe
        invalid_resource = await recipe.create_resource(
            "fle://recipe/", {"name": "non_existent_recipe_xyz"}
        )
        result_invalid = await invalid_resource.read()
        assert result_invalid is not None
        assert "not found" in result_invalid

    @pytest.mark.asyncio
    async def test_schema_resource(self):
        """Test schema resource returns API documentation"""
        await reconnect.run({})

        # Create resource - no parameters needed
        resource = schema

        result = await resource.read()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 100  # Should have substantial documentation

        # Should contain type or entity information
        assert any(
            keyword in result.lower() for keyword in ["type", "entity", "class", "def"]
        )

    @pytest.mark.asyncio
    async def test_manual_resource(self):
        """Test manual resource with specific method name"""
        await reconnect.run({})

        # Test with common method names
        test_methods = ["move_to", "place_entity", "craft_item"]

        for method_name in test_methods:
            try:
                # Create resource with method name
                resource = await manual.create_resource(
                    "fle://api/manual/", {"method": method_name}
                )

                result = await resource.read()
                assert result is not None
                assert isinstance(result, str)

                if "Error" not in result:
                    # Found valid documentation
                    assert len(result) > 50
                    break
            except Exception:
                continue

        # Test with invalid method
        invalid_resource = await manual.create_resource(
            "fle://api/manual/", {"method": "non_existent_method_xyz"}
        )
        result_invalid = await invalid_resource.read()
        assert result_invalid is not None
        assert isinstance(result_invalid, str)
        assert "Error" in result_invalid or "not a valid" in result_invalid

    @pytest.mark.asyncio
    async def test_status_resource(self):
        """Test status resource checks server connection"""
        # Create resource - no parameters needed
        resource = status  # .create_resource('fle://status', {})

        result = await resource.read()
        assert result is not None
        assert isinstance(result, str)
        assert "Connected to Factorio server" in result or "Initializing" in result

    @pytest.mark.asyncio
    async def test_resource_error_handling_no_connection(self):
        """Test resource error handling when server is not connected"""
        # Clear state to simulate no connection
        state.active_server = None

        # Test inventory resource
        inv_resource = inventory  # .create_resource('fle://inventory', {})
        with pytest.raises(Exception, match="No active Factorio server connection"):
            await inv_resource.read()

        # Test position resource
        pos_resource = position  # .create_resource('fle://position', {})
        with pytest.raises(Exception, match="No active Factorio server connection"):
            await pos_resource.read()

        # Test entities resource
        ent_resource = await entities.create_resource(
            "fle://entities/", {"center_x": "0", "center_y": "0", "radius": "100"}
        )
        with pytest.raises(Exception, match="No active Factorio server connection"):
            await ent_resource.read()

    @pytest.mark.asyncio
    async def test_entities_parameter_conversion(self):
        """Test entities resource properly converts string parameters"""
        await reconnect.run({})

        # Test with different parameter formats
        test_cases = [
            {"center_x": "0", "center_y": "0", "radius": "500"},  # String numbers
            {
                "center_x": "10.5",
                "center_y": "-20.5",
                "radius": "100.0",
            },  # Float strings
            {
                "center_x": "default",
                "center_y": "default",
                "radius": "default",
            },  # Default values
        ]

        for params in test_cases:
            resource = await entities.create_resource("fle://entities/", params)
            result = await resource.read()
            result = json.loads(result)
            assert result is not None
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_render_parameter_conversion(self):
        """Test render_with_position properly converts string parameters"""
        await reconnect.run({})

        # Test with different coordinate formats
        test_cases = [
            {"center_x": "0", "center_y": "0"},
            {"center_x": "10.5", "center_y": "-20.5"},
            {"center_x": "-100", "center_y": "100"},
        ]

        for params in test_cases:
            resource = await render_at.create_resource("fle://render/", params)
            result = await resource.read()
            assert result is not None

    @pytest.mark.asyncio
    async def test_recipe_names_consistency(self):
        """Test that entity_names and recipe lookups are consistent"""
        await reconnect.run({})

        # Get all available recipe names
        names_resource = prototypes  # .create_resource('fle://entity-names', {})
        names = await names_resource.read()
        names = json.loads(names)
        assert names is not None

        if len(names) > 5:
            # Sample a few recipes and verify they can be retrieved
            sample_names = names[:5]
            for name in sample_names:
                resource = await recipe.create_resource("fle://recipe/", {"name": name})
                result = await resource.read()
                assert result is not None
                assert "not found" not in result

                # Parse and verify structure
                recipe_data = json.loads(result)
                assert recipe_data["name"] == name

    @pytest.mark.asyncio
    async def test_resources_without_params(self):
        """Test resources that don't take parameters"""
        await reconnect.run({})

        # These resources should work with empty parameter dict
        no_param_resources = [
            (inventory, "fle://inventory", dict),
            (position, "fle://position", dict),
            (prototypes, "fle://prototypes", list),
            (schema, "fle://api/schema", str),
            (status, "fle://status", str),
        ]

        for resource_template, uri, expected_type in no_param_resources:
            resource = await resource_template.create_resource(uri, {})
            result = await resource.read()
            assert result is not None
            assert isinstance(result, expected_type), (
                f"{resource_template} should return {expected_type}, got {type(result)}"
            )

    @pytest.mark.asyncio
    async def test_resources_with_path_params(self):
        """Test resources that take path parameters"""
        await reconnect.run({})

        # Test entities with path params
        entities_resource = await entities.create_resource(
            "fle://entities/", {"center_x": "0", "center_y": "0", "radius": "100"}
        )
        entities_result = await entities_resource.read()
        assert isinstance(entities_result, list)

        # Test render with path params
        render_resource = await render_at.create_resource(
            "fle://render/", {"center_x": "0", "center_y": "0"}
        )
        render_result = await render_resource.read()
        assert render_result is not None

        # Test recipe with path param
        names_resource = await prototypes.create_resource("fle://prototypes", {})
        names = await names_resource.read()
        if names:
            recipe_resource = await recipe.create_resource(
                "fle://recipe/", {"name": names[0]}
            )
            recipe_result = await recipe_resource.read()
            assert isinstance(recipe_result, str)

        # Test manual with path param
        manual_resource = await manual.create_resource(
            "fle://api/manual/", {"method": "move_to"}
        )
        manual_result = await manual_resource.read()
        assert isinstance(manual_result, str)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
