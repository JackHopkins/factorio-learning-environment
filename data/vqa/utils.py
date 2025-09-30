from pathlib import Path


def find_blueprints_dir() -> Path:
    """Walk up the directory tree until we find .fle directory."""
    current = Path.cwd()

    while current != current.parent:
        fle_dir = current / ".fle"
        if fle_dir.exists() and fle_dir.is_dir():
            return fle_dir / "blueprints"
        current = current.parent

    # Fallback - return the path even if it doesn't exist
    return Path.cwd() / ".fle" / "blueprints"
