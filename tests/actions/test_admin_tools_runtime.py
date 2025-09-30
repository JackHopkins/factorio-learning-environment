"""Test admin tools runtime enable/disable functionality."""

from fle.env import FactorioInstance


def test_admin_tools_default_behavior(namespace):
    """Test that admin tools are hidden by default."""
    assert namespace.is_admin_tools_enabled() is False

    # Check if admin tools are hidden (with underscore prefix)
    admin_tools = [
        attr
        for attr in dir(namespace)
        if attr.startswith("_") and not attr.startswith("__")
    ]
    assert len(admin_tools) > 0, "Should have hidden admin tools"

    # Check that admin tools are not exposed without underscore prefix
    exposed_admin_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    # Should not have admin tools like get_elapsed_ticks exposed
    assert "get_elapsed_ticks" not in exposed_admin_tools, (
        "Admin tools should be hidden by default"
    )


def test_admin_tools_runtime_enable(namespace):
    """Test enabling admin tools at runtime."""
    # Enable admin tools at runtime
    namespace.enable_admin_tools_in_runtime(True)
    assert namespace.is_admin_tools_enabled() is True

    # Check that admin tools are now exposed
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    # Should now have admin tools like get_elapsed_ticks exposed
    assert "get_elapsed_ticks" in exposed_tools, (
        "Admin tools should be exposed when enabled"
    )


def test_admin_tools_runtime_disable(namespace):
    """Test disabling admin tools at runtime."""
    # Enable then disable admin tools
    namespace.enable_admin_tools_in_runtime(True)
    assert namespace.is_admin_tools_enabled() is True

    namespace.enable_admin_tools_in_runtime(False)
    assert namespace.is_admin_tools_enabled() is False

    # Check that admin tools are hidden again
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" not in exposed_tools, (
        "Admin tools should be hidden when disabled"
    )


def test_admin_tools_construction_enable(configure_game):
    """Test enabling admin tools at construction time."""
    # Create a new instance with admin tools enabled
    instance = FactorioInstance(
        address="localhost",
        tcp_port=27000,
        fast=True,
        cache_scripts=True,
        peaceful=True,
        enable_admin_tools_in_runtime=True,
    )

    namespace = instance.first_namespace
    assert namespace.is_admin_tools_enabled() is True

    # Check that admin tools are exposed from the start
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools, (
        "Admin tools should be exposed when enabled at construction"
    )

    # Cleanup
    instance.cleanup()


def test_admin_tools_toggle_multiple_times(namespace):
    """Test toggling admin tools multiple times."""
    # Toggle multiple times
    for i in range(3):
        namespace.enable_admin_tools_in_runtime(True)
        assert namespace.is_admin_tools_enabled() is True

        namespace.enable_admin_tools_in_runtime(False)
        assert namespace.is_admin_tools_enabled() is False


def test_admin_tools_persist_after_reset(namespace):
    """Test that admin tools state persists after namespace reset."""
    # Enable admin tools
    namespace.enable_admin_tools_in_runtime(True)
    assert namespace.is_admin_tools_enabled() is True

    # Verify admin tools are exposed
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools, (
        "Admin tools should be exposed before reset"
    )

    # Reset the namespace
    namespace.reset()

    # Check that admin tools state is preserved
    assert namespace.is_admin_tools_enabled() is True, (
        "Admin tools should still be enabled after reset"
    )

    # Check that admin tools are still exposed after reset
    exposed_tools_after_reset = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools_after_reset, (
        "Admin tools should still be exposed after reset"
    )


def test_admin_tools_disabled_persist_after_reset(namespace):
    """Test that disabled admin tools state persists after namespace reset."""
    # Ensure admin tools are disabled
    namespace.enable_admin_tools_in_runtime(False)
    assert namespace.is_admin_tools_enabled() is False

    # Verify admin tools are hidden
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" not in exposed_tools, (
        "Admin tools should be hidden before reset"
    )

    # Reset the namespace
    namespace.reset()

    # Check that admin tools state is preserved
    assert namespace.is_admin_tools_enabled() is False, (
        "Admin tools should still be disabled after reset"
    )

    # Check that admin tools are still hidden after reset
    exposed_tools_after_reset = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" not in exposed_tools_after_reset, (
        "Admin tools should still be hidden after reset"
    )


def test_admin_tools_reset_with_construction_enabled(configure_game):
    """Test that admin tools enabled at construction persist through reset."""
    # Create instance with admin tools enabled
    instance = FactorioInstance(
        address="localhost",
        tcp_port=27000,
        fast=True,
        cache_scripts=True,
        peaceful=True,
        enable_admin_tools_in_runtime=True,
    )

    namespace = instance.first_namespace
    assert namespace.is_admin_tools_enabled() is True

    # Verify admin tools are exposed
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools, (
        "Admin tools should be exposed before reset"
    )

    # Reset the namespace
    namespace.reset()

    # Check that admin tools state is preserved
    assert namespace.is_admin_tools_enabled() is True, (
        "Admin tools should still be enabled after reset"
    )

    # Check that admin tools are still exposed after reset
    exposed_tools_after_reset = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools_after_reset, (
        "Admin tools should still be exposed after reset"
    )

    # Cleanup
    instance.cleanup()


def test_admin_tools_reset_preserves_agent_variables(namespace):
    """Test that reset preserves agent variables and admin tools state."""
    # Enable admin tools
    namespace.enable_admin_tools_in_runtime(True)
    assert namespace.is_admin_tools_enabled() is True

    # Create some agent variables
    namespace.eval_with_timeout("my_variable = 42")
    namespace.eval_with_timeout("my_list = [1, 2, 3]")

    # Verify variables exist by checking if they're in the namespace
    assert hasattr(namespace, "my_variable"), "Agent variable should exist before reset"
    assert hasattr(namespace, "my_list"), "Agent variable should exist before reset"

    # Reset the namespace
    namespace.reset()

    # Check that admin tools state is preserved
    assert namespace.is_admin_tools_enabled() is True, (
        "Admin tools should still be enabled after reset"
    )

    # Check that admin tools are still exposed
    exposed_tools = [
        attr
        for attr in dir(namespace)
        if not attr.startswith("_") and not attr.startswith("__")
    ]
    assert "get_elapsed_ticks" in exposed_tools, (
        "Admin tools should still be exposed after reset"
    )

    # Check that agent variables are preserved (namespace reset doesn't clear persistent_vars)
    assert getattr(namespace, "my_variable", "NOT_FOUND") == 42, (
        "Agent variable should be preserved after reset"
    )
    assert getattr(namespace, "my_list", "NOT_FOUND") == [1, 2, 3], (
        "Agent variable should be preserved after reset"
    )
