"""
API Key Management and Rotation System

Handles multiple API keys for different providers with round-robin rotation,
rate limiting awareness, and error recovery.
"""

import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from collections import defaultdict
import logging


@dataclass
class APIKeyConfig:
    """Configuration for a single API key"""

    key: str
    provider: str
    rate_limit_per_minute: Optional[int] = None
    max_concurrent: Optional[int] = None
    priority: int = 1  # Higher priority keys used first
    enabled: bool = True
    last_used: Optional[float] = None
    error_count: int = 0
    max_errors: int = 5  # Disable key after this many consecutive errors

    def is_available(self) -> bool:
        """Check if key is available for use"""
        return self.enabled and self.error_count < self.max_errors

    def mark_used(self):
        """Mark key as recently used"""
        self.last_used = time.time()

    def mark_error(self):
        """Mark an error occurred with this key"""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            logging.warning(
                f"API key {self.key[:8]}... disabled due to {self.error_count} errors"
            )

    def reset_errors(self):
        """Reset error count (e.g., after successful use)"""
        self.error_count = 0


class APIKeyManager:
    """Manages multiple API keys with rotation and rate limiting"""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize API key manager

        Args:
            config_file: Path to JSON config file with API keys
        """
        self._keys: Dict[str, List[APIKeyConfig]] = defaultdict(list)
        self._lock = threading.Lock()
        self._usage_counts: Dict[str, int] = defaultdict(int)

        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)
        else:
            self.load_from_environment()

    def load_from_file(self, config_file: str):
        """Load API keys from JSON configuration file

        Expected format:
        {
            "anthropic": [
                {"key": "sk-ant-...", "rate_limit_per_minute": 50, "priority": 1},
                {"key": "sk-ant-...", "rate_limit_per_minute": 50, "priority": 2}
            ],
            "openai": [
                {"key": "sk-...", "rate_limit_per_minute": 100, "max_concurrent": 10}
            ]
        }
        """
        with open(config_file, "r") as f:
            config_data = json.load(f)

        for provider, keys_data in config_data.items():
            for key_data in keys_data:
                key_config = APIKeyConfig(
                    key=key_data["key"],
                    provider=provider,
                    **{k: v for k, v in key_data.items() if k != "key"},
                )
                self._keys[provider].append(key_config)

        logging.info(f"Loaded API keys from {config_file}:")
        for provider, keys in self._keys.items():
            logging.info(f"  {provider}: {len(keys)} keys")

    def load_from_environment(self):
        """Load API keys from environment variables

        Supports both single keys and multiple keys:
        - ANTHROPIC_API_KEY or ANTHROPIC_API_KEYS (comma-separated)
        - OPENAI_API_KEY or OPENAI_API_KEYS (comma-separated)
        """
        # Mapping of provider names to env var prefixes
        provider_env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "together": "TOGETHER_API_KEY",
            "open-router": "OPEN_ROUTER_API_KEY",
        }

        for provider, env_prefix in provider_env_map.items():
            # Try multiple keys first (PROVIDER_API_KEYS)
            keys_env = f"{env_prefix}S"  # Add 'S' for plural
            keys_str = os.getenv(keys_env)

            if keys_str:
                # Multiple keys separated by commas
                keys = [k.strip() for k in keys_str.split(",") if k.strip()]
                for i, key in enumerate(keys):
                    key_config = APIKeyConfig(
                        key=key,
                        provider=provider,
                        priority=i + 1,  # First key has highest priority
                    )
                    self._keys[provider].append(key_config)
                logging.info(f"Loaded {len(keys)} {provider} keys from {keys_env}")
            else:
                # Try single key (PROVIDER_API_KEY)
                single_key = os.getenv(env_prefix)
                if single_key:
                    key_config = APIKeyConfig(
                        key=single_key, provider=provider, priority=1
                    )
                    self._keys[provider].append(key_config)
                    logging.info(f"Loaded 1 {provider} key from {env_prefix}")

    def add_key(self, provider: str, key: str, **kwargs):
        """Add a new API key for a provider"""
        with self._lock:
            key_config = APIKeyConfig(key=key, provider=provider, **kwargs)
            self._keys[provider].append(key_config)
            logging.info(f"Added new {provider} API key")

    def get_key(self, provider: str, prefer_unused: bool = True) -> Optional[str]:
        """Get an available API key for the specified provider

        Args:
            provider: Provider name (e.g., 'anthropic', 'openai')
            prefer_unused: Whether to prefer less recently used keys

        Returns:
            API key string or None if no available keys
        """
        with self._lock:
            available_keys = [key for key in self._keys[provider] if key.is_available()]

            if not available_keys:
                logging.warning(f"No available API keys for provider: {provider}")
                return None

            # Sort by priority, then by usage/last used time
            if prefer_unused:
                available_keys.sort(
                    key=lambda k: (
                        -k.priority,  # Higher priority first (negative for desc sort)
                        k.last_used or 0,  # Less recently used first
                        self._usage_counts.get(k.key, 0),  # Less used keys first
                    )
                )
            else:
                # Just use priority and randomize among equal priorities
                available_keys.sort(key=lambda k: (-k.priority, random.random()))

            selected_key = available_keys[0]
            selected_key.mark_used()
            self._usage_counts[selected_key.key] += 1

            logging.debug(f"Selected {provider} key: {selected_key.key[:8]}...")
            return selected_key.key

    def mark_key_success(self, provider: str, key: str):
        """Mark a key as successfully used (resets error count)"""
        with self._lock:
            for key_config in self._keys[provider]:
                if key_config.key == key:
                    key_config.reset_errors()
                    break

    def mark_key_error(self, provider: str, key: str, error: Exception):
        """Mark an error occurred with a specific key"""
        with self._lock:
            for key_config in self._keys[provider]:
                if key_config.key == key:
                    key_config.mark_error()
                    logging.warning(
                        f"Error with {provider} key {key[:8]}...: {error}"
                        f" (error count: {key_config.error_count})"
                    )
                    break

    def get_key_stats(self) -> Dict[str, Any]:
        """Get statistics about key usage"""
        with self._lock:
            stats = {}
            for provider, keys in self._keys.items():
                provider_stats = {
                    "total_keys": len(keys),
                    "available_keys": len([k for k in keys if k.is_available()]),
                    "disabled_keys": len([k for k in keys if not k.is_available()]),
                    "keys": [],
                }

                for key in keys:
                    key_stats = {
                        "key_preview": f"{key.key[:8]}...{key.key[-4:]}",
                        "priority": key.priority,
                        "enabled": key.enabled,
                        "error_count": key.error_count,
                        "usage_count": self._usage_counts.get(key.key, 0),
                        "last_used": key.last_used,
                    }
                    provider_stats["keys"].append(key_stats)

                stats[provider] = provider_stats

            return stats

    def reset_key(self, provider: str, key_prefix: str):
        """Reset error count for a key (by prefix match)"""
        with self._lock:
            for key_config in self._keys[provider]:
                if key_config.key.startswith(key_prefix):
                    key_config.reset_errors()
                    key_config.enabled = True
                    logging.info(f"Reset {provider} key {key_prefix}...")
                    break

    def list_providers(self) -> List[str]:
        """Get list of providers with available keys"""
        return [provider for provider, keys in self._keys.items() if keys]

    def has_keys(self, provider: str) -> bool:
        """Check if provider has any available keys"""
        with self._lock:
            return any(key.is_available() for key in self._keys[provider])


# Global instance for easy access
_global_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(config_file: Optional[str] = None) -> APIKeyManager:
    """Get or create global API key manager instance"""
    global _global_key_manager

    if _global_key_manager is None:
        _global_key_manager = APIKeyManager(config_file)

    return _global_key_manager


def create_api_keys_config_template(output_file: str = "api_keys.json"):
    """Create a template configuration file for API keys"""

    template = {
        "anthropic": [
            {
                "key": "sk-ant-api01-your-key-here",
                "rate_limit_per_minute": 50,
                "max_concurrent": 5,
                "priority": 1,
            },
            {
                "key": "sk-ant-api01-your-second-key-here",
                "rate_limit_per_minute": 50,
                "max_concurrent": 5,
                "priority": 2,
            },
        ],
        "openai": [
            {
                "key": "sk-your-openai-key-here",
                "rate_limit_per_minute": 100,
                "max_concurrent": 10,
                "priority": 1,
            }
        ],
        "deepseek": [
            {
                "key": "sk-your-deepseek-key-here",
                "rate_limit_per_minute": 60,
                "priority": 1,
            }
        ],
    }

    with open(output_file, "w") as f:
        json.dump(template, f, indent=2)

    print(f"Created API keys template: {output_file}")
    print("Please edit this file with your actual API keys.")

    return template


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "template":
        create_api_keys_config_template()
    else:
        # Demo the key manager
        manager = get_api_key_manager()

        print("Available providers:", manager.list_providers())

        # Try to get keys
        for provider in manager.list_providers():
            key = manager.get_key(provider)
            print(f"{provider}: {key[:8] if key else 'No key'}...")

        # Show stats
        stats = manager.get_key_stats()
        print("\nKey statistics:")
        for provider, provider_stats in stats.items():
            print(
                f"{provider}: {provider_stats['available_keys']}/{provider_stats['total_keys']} keys available"
            )
