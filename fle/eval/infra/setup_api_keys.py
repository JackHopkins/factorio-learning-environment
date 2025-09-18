"""
Setup and management utilities for API keys in the Factorio Learning Environment.

This script helps you configure multiple API keys for different providers,
test their functionality, and manage key rotation.
"""

import json
import asyncio
from pathlib import Path

from fle.eval.infra.api_key_manager import (
    create_api_keys_config_template,
    get_api_key_manager,
)


def create_config_interactive():
    """Interactive setup of API key configuration"""

    print("🔑 API Key Configuration Setup")
    print("=" * 40)

    config = {}

    # Anthropic (Claude) keys
    print("\n1. Anthropic (Claude) API Keys:")
    anthropic_keys = []
    while True:
        key = input(
            f"Enter Anthropic API key #{len(anthropic_keys) + 1} (or press Enter to skip): "
        ).strip()
        if not key:
            break
        if not key.startswith("sk-ant-"):
            print("Warning: Anthropic keys typically start with 'sk-ant-'")

        rate_limit = input("Rate limit per minute (default: 50): ").strip()
        rate_limit = int(rate_limit) if rate_limit.isdigit() else 50

        anthropic_keys.append(
            {
                "key": key,
                "rate_limit_per_minute": rate_limit,
                "priority": len(anthropic_keys) + 1,
            }
        )

        if input("Add another Anthropic key? (y/N): ").lower() != "y":
            break

    if anthropic_keys:
        config["anthropic"] = anthropic_keys

    # OpenAI keys
    print("\n2. OpenAI API Keys:")
    openai_keys = []
    while True:
        key = input(
            f"Enter OpenAI API key #{len(openai_keys) + 1} (or press Enter to skip): "
        ).strip()
        if not key:
            break
        if not key.startswith("sk-"):
            print("Warning: OpenAI keys typically start with 'sk-'")

        rate_limit = input("Rate limit per minute (default: 100): ").strip()
        rate_limit = int(rate_limit) if rate_limit.isdigit() else 100

        openai_keys.append(
            {
                "key": key,
                "rate_limit_per_minute": rate_limit,
                "priority": len(openai_keys) + 1,
            }
        )

        if input("Add another OpenAI key? (y/N): ").lower() != "y":
            break

    if openai_keys:
        config["openai"] = openai_keys

    # Other providers
    other_providers = {
        "deepseek": ("DeepSeek", "sk-"),
        "gemini": ("Gemini", ""),
        "together": ("Together AI", ""),
        "open-router": ("OpenRouter", "sk-"),
    }

    for provider, (display_name, key_prefix) in other_providers.items():
        print(f"\n3. {display_name} API Keys:")
        keys = []
        while True:
            key = input(
                f"Enter {display_name} API key (or press Enter to skip): "
            ).strip()
            if not key:
                break
            if key_prefix and not key.startswith(key_prefix):
                print(
                    f"Warning: {display_name} keys typically start with '{key_prefix}'"
                )

            rate_limit = input("Rate limit per minute (default: 60): ").strip()
            rate_limit = int(rate_limit) if rate_limit.isdigit() else 60

            keys.append(
                {
                    "key": key,
                    "rate_limit_per_minute": rate_limit,
                    "priority": len(keys) + 1,
                }
            )

            if input(f"Add another {display_name} key? (y/N): ").lower() != "y":
                break

        if keys:
            config[provider] = keys

    # Save configuration
    if not config:
        print("No API keys configured.")
        return

    config_file = (
        input("\nConfig file name (default: api_keys.json): ").strip()
        or "api_keys.json"
    )

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Configuration saved to: {config_file}")
    print(f"📊 Total providers configured: {len(config)}")

    total_keys = sum(len(keys) for keys in config.values())
    print(f"🔑 Total API keys: {total_keys}")

    print("\n💡 To use this configuration:")
    print(f"   export API_KEY_CONFIG_FILE={Path(config_file).absolute()}")
    print("   # or")
    print(f"   python your_script.py --api-key-config {config_file}")

    return config_file


async def test_api_keys(config_file: str):
    """Test all configured API keys"""

    print(f"🧪 Testing API keys from: {config_file}")
    print("=" * 50)

    try:
        manager = get_api_key_manager(config_file)
    except Exception as e:
        print(f"❌ Failed to load API key manager: {e}")
        return

    providers = manager.list_providers()
    if not providers:
        print("❌ No providers found in configuration")
        return

    print(f"Found {len(providers)} providers: {', '.join(providers)}")

    # Test each provider
    for provider in providers:
        print(f"\n🔍 Testing {provider}...")

        # Get available keys for this provider
        available_count = len(
            [key for key in manager._keys[provider] if key.is_available()]
        )

        print(f"   Available keys: {available_count}")

        if available_count == 0:
            print("   ❌ No available keys")
            continue

        # Test getting keys
        for i in range(min(3, available_count)):  # Test up to 3 keys
            key = manager.get_key(provider)
            if key:
                print(f"   ✅ Key {i + 1}: {key[:8]}...{key[-4:]}")
            else:
                print(f"   ❌ Failed to get key {i + 1}")

    # Show statistics
    print("\n📊 Key Statistics:")
    stats = manager.get_key_stats()

    for provider, provider_stats in stats.items():
        print(f"\n{provider}:")
        print(f"  Total keys: {provider_stats['total_keys']}")
        print(f"  Available: {provider_stats['available_keys']}")
        print(f"  Disabled: {provider_stats['disabled_keys']}")


def show_key_status(config_file: str):
    """Show detailed status of all configured keys"""

    print(f"📈 API Key Status: {config_file}")
    print("=" * 60)

    try:
        manager = get_api_key_manager(config_file)
    except Exception as e:
        print(f"❌ Failed to load API key manager: {e}")
        return

    stats = manager.get_key_stats()

    for provider, provider_stats in stats.items():
        print(f"\n🏢 {provider.upper()}:")
        print(f"   Total: {provider_stats['total_keys']}")
        print(f"   Available: {provider_stats['available_keys']}")
        print(f"   Disabled: {provider_stats['disabled_keys']}")

        if provider_stats["keys"]:
            print("   Keys:")
            for i, key_stat in enumerate(provider_stats["keys"], 1):
                status = (
                    "✅"
                    if key_stat["enabled"] and key_stat["error_count"] == 0
                    else "⚠️"
                    if key_stat["enabled"]
                    else "❌"
                )

                print(
                    f"     {i}. {status} {key_stat['key_preview']} "
                    f"(priority: {key_stat['priority']}, "
                    f"errors: {key_stat['error_count']}, "
                    f"used: {key_stat['usage_count']})"
                )


def setup_environment_variables():
    """Help set up environment variables for API keys"""

    print("🌍 Environment Variable Setup")
    print("=" * 40)

    print("For simple single-key setup, you can use environment variables:")
    print()

    providers = [
        ("Anthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS"),
        ("OpenAI", "OPENAI_API_KEY", "OPENAI_API_KEYS"),
        ("DeepSeek", "DEEPSEEK_API_KEY", "DEEPSEEK_API_KEYS"),
        ("Gemini", "GEMINI_API_KEY", "GEMINI_API_KEYS"),
        ("Together", "TOGETHER_API_KEY", "TOGETHER_API_KEYS"),
        ("OpenRouter", "OPEN_ROUTER_API_KEY", "OPEN_ROUTER_API_KEYS"),
    ]

    for provider, single_var, multi_var in providers:
        print(f"{provider}:")
        print(f"  Single key:    export {single_var}=your-key-here")
        print(f"  Multiple keys: export {multi_var}=key1,key2,key3")
        print()

    print(
        "💡 For advanced features like rate limiting, priorities, and error tracking,"
    )
    print("   use a JSON configuration file instead.")


def validate_config_file(config_file: str):
    """Validate a configuration file"""

    print(f"🔍 Validating: {config_file}")
    print("=" * 40)

    if not Path(config_file).exists():
        print(f"❌ File not found: {config_file}")
        return False

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

    if not isinstance(config, dict):
        print("❌ Configuration must be a JSON object")
        return False

    total_keys = 0
    valid_providers = []

    for provider, keys in config.items():
        print(f"\n📍 {provider}:")

        if not isinstance(keys, list):
            print("   ❌ Keys must be a list")
            continue

        valid_keys = 0
        for i, key_config in enumerate(keys):
            if not isinstance(key_config, dict):
                print(f"   ❌ Key {i + 1}: Must be an object")
                continue

            if "key" not in key_config:
                print(f"   ❌ Key {i + 1}: Missing 'key' field")
                continue

            if not isinstance(key_config["key"], str) or not key_config["key"].strip():
                print(f"   ❌ Key {i + 1}: 'key' must be a non-empty string")
                continue

            valid_keys += 1
            total_keys += 1

        print(f"   ✅ {valid_keys}/{len(keys)} valid keys")
        if valid_keys > 0:
            valid_providers.append(provider)

    print("\n📊 Summary:")
    print(f"   Valid providers: {len(valid_providers)}")
    print(f"   Total valid keys: {total_keys}")

    if valid_providers:
        print("✅ Configuration is valid!")
        return True
    else:
        print("❌ No valid keys found in configuration")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("🔑 Factorio API Key Management")
        print("=" * 30)
        print("Commands:")
        print("  setup          - Interactive API key setup")
        print("  template       - Create a template configuration file")
        print("  test <file>    - Test API keys in configuration file")
        print("  status <file>  - Show status of API keys")
        print("  validate <file> - Validate configuration file")
        print("  env            - Show environment variable setup")
        print()
        print("Examples:")
        print("  python setup_api_keys.py setup")
        print("  python setup_api_keys.py test api_keys.json")
        print("  python setup_api_keys.py status api_keys.json")
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        config_file = create_config_interactive()
        if config_file:
            print("\n🧪 Would you like to test the configuration? (y/N): ", end="")
            if input().lower() == "y":
                asyncio.run(test_api_keys(config_file))

    elif command == "template":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "api_keys_template.json"
        create_api_keys_config_template(output_file)

    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Please provide configuration file path")
            sys.exit(1)
        asyncio.run(test_api_keys(sys.argv[2]))

    elif command == "status":
        if len(sys.argv) < 3:
            print("❌ Please provide configuration file path")
            sys.exit(1)
        show_key_status(sys.argv[2])

    elif command == "validate":
        if len(sys.argv) < 3:
            print("❌ Please provide configuration file path")
            sys.exit(1)
        validate_config_file(sys.argv[2])

    elif command == "env":
        setup_environment_variables()

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
