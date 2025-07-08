"""
Unix-like tools for code introspection in Factorio Learning Environment
"""

import glob
import os
import re
from pathlib import Path

from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.env.protocols.mcp import mcp


def _get_tools_base_path() -> Path:
    """Get the base path to the tools directory"""
    return (
        Path(os.path.dirname(os.path.realpath(__file__))).parent
        / Path("env")
        / Path("src")
        / "tools"
    )


@mcp.tool()
async def ls(path: str = "agent", pattern: str = None) -> str:
    """
    List tools and directories in the tools path

    Args:
        path: Relative path within the tools directory (default: "agent")
        pattern: Optional glob pattern to filter results (e.g., "*.py", "place*")
    """
    base_path = _get_tools_base_path()
    target_path = base_path / path

    if not target_path.exists():
        return f"Error: Path '{path}' does not exist"

    if not target_path.is_dir():
        return f"Error: '{path}' is not a directory"

    # Get all entries in the directory
    entries = list(target_path.iterdir())

    # Filter by pattern if provided
    if pattern:
        # Convert to glob pattern and filter
        try:
            pattern_path = (
                str(target_path / pattern)
                if "*" not in pattern
                else str(target_path) + "/" + pattern
            )
            matched_paths = glob.glob(pattern_path)
            entries = [Path(p) for p in matched_paths]
        except Exception as e:
            return f"Error applying pattern '{pattern}': {str(e)}"

    # Sort directories first, then files
    dirs = sorted([entry for entry in entries if entry.is_dir()], key=lambda x: x.name)
    files = sorted(
        [entry for entry in entries if entry.is_file()], key=lambda x: x.name
    )

    # Format output
    result = f"Contents of {path}:\n"

    if dirs:
        result += "\nDirectories:\n"
        for d in dirs:
            result += f"  📁 {d.name}/\n"

    if files:
        result += "\nFiles:\n"
        for f in files:
            result += f"  📄 {f.name}\n"

    if not dirs and not files:
        result += "\nDirectory is empty\n"

    return result


@mcp.tool()
async def cat(file_path: str) -> str:
    """
    Display the contents of a file in the tools directory

    Args:
        file_path: Relative path to the file within the tools directory
    """
    base_path = _get_tools_base_path()
    target_file = base_path / file_path

    if not target_file.exists():
        return f"Error: File '{file_path}' does not exist"

    if not target_file.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        with open(target_file, "r") as f:
            content = f.read()

        return f"Contents of {file_path}:\n\n```python\n{content}\n```"
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@mcp.tool()
async def find(
    path: str = "",
    name_pattern: str = None,
    content_pattern: str = None,
    type_filter: str = None,
    max_depth: int = None,
) -> str:
    """
    Find files or directories in the tools directory

    Args:
        path: Starting path within the tools directory (default: root tools dir)
        name_pattern: Pattern to match in file/directory names (glob pattern)
        content_pattern: Pattern to search for in file contents (regex)
        type_filter: Limit to specific types: "f" for files, "d" for directories
        max_depth: Maximum directory depth to search
    """
    base_path = _get_tools_base_path()
    start_path = base_path if not path else base_path / path

    if not start_path.exists():
        return f"Error: Path '{path}' does not exist"

    results = []
    current_depth = 0

    def search_dir(current_path, depth):
        nonlocal results

        if max_depth is not None and depth > max_depth:
            return

        try:
            for entry in current_path.iterdir():
                rel_path = str(entry.relative_to(base_path))

                # Check type filter
                if type_filter == "f" and not entry.is_file():
                    continue
                if type_filter == "d" and not entry.is_dir():
                    continue

                # Check name pattern
                name_match = True
                if name_pattern:
                    name_match = glob.fnmatch.fnmatch(entry.name, name_pattern)

                # For files, check content pattern if applicable
                content_match = True
                if content_pattern and entry.is_file():
                    try:
                        with open(entry, "r") as f:
                            content = f.read()
                        content_match = bool(re.search(content_pattern, content))
                    except:
                        content_match = False

                # Add to results if all conditions are met
                if name_match and content_match:
                    entry_type = "📁" if entry.is_dir() else "📄"
                    results.append(f"{entry_type} {rel_path}")

                # Recurse into directories
                if entry.is_dir():
                    search_dir(entry, depth + 1)
        except Exception as e:
            results.append(f"Error accessing {current_path}: {str(e)}")

    # Start the search
    search_dir(start_path, current_depth)

    if not results:
        return "No matches found for the specified criteria"

    return f"Found {len(results)} matches:\n\n" + "\n".join(results)


@mcp.tool()
async def grep(
    pattern: str,
    path: str,
    recursive: bool = True,
    case_sensitive: bool = False,
    line_numbers: bool = True,
) -> str:
    """
    Search for a pattern in files

    Args:
        pattern: Regex pattern to search for
        path: File or directory path within the tools directory
        recursive: Whether to search directories recursively
        case_sensitive: Whether the search should be case-sensitive
        line_numbers: Whether to show line numbers in the output
    """
    base_path = _get_tools_base_path()
    target_path = base_path / path

    if not target_path.exists():
        return f"Error: Path '{path}' does not exist"

    # Prepare regex flags
    flags = 0 if case_sensitive else re.IGNORECASE

    try:
        # Compile the pattern
        regex = re.compile(pattern, flags)
    except Exception as e:
        return f"Error in regex pattern: {str(e)}"

    results = []

    def search_file(file_path):
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            file_matches = []
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    if line_numbers:
                        file_matches.append(f"{i}: {line.rstrip()}")
                    else:
                        file_matches.append(line.rstrip())

            if file_matches:
                rel_path = str(file_path.relative_to(base_path))
                results.append(f"File: {rel_path}")
                results.append("```")
                results.extend(file_matches[:20])  # Limit matches to avoid huge outputs
                if len(file_matches) > 20:
                    results.append(f"... and {len(file_matches) - 20} more matches")
                results.append("```")
                results.append("")
        except Exception:
            # Skip binary or unreadable files
            pass

    def search_dir(dir_path):
        try:
            for entry in dir_path.iterdir():
                if entry.is_file() and entry.suffix in [".py", ".lua", ".md", ".txt"]:
                    search_file(entry)
                elif entry.is_dir() and recursive:
                    search_dir(entry)
        except Exception as e:
            results.append(f"Error accessing {dir_path}: {str(e)}")

    if target_path.is_file():
        search_file(target_path)
    elif target_path.is_dir():
        search_dir(target_path)

    if not results:
        return f"No matches found for pattern '{pattern}' in {path}"

    return f"Matches for '{pattern}' in {path}:\n\n" + "\n".join(results)


@mcp.tool()
async def which(command: str) -> str:
    """
    Find the implementation file for a specific Factorio tool

    Args:
        command: Name of the tool to locate
    """
    base_path = _get_tools_base_path()

    # Locations to check for agent tools
    agent_path = base_path / "agent"
    admin_path = base_path / "admin"

    # First check agent tools (most common)
    if (agent_path / command).exists() and (agent_path / command).is_dir():
        client_file = agent_path / command / "client.py"
        server_file = agent_path / command / "server.lua"

        result = f"Tool '{command}' found in agent tools:\n"

        if client_file.exists():
            result += f"- Python client: tools/agent/{command}/client.py\n"

        if server_file.exists():
            result += f"- Lua server: tools/agent/{command}/server.lua\n"

        return result

    # Check admin tools
    if (admin_path / command).exists() and (admin_path / command).is_dir():
        client_file = admin_path / command / "client.py"
        server_file = admin_path / command / "server.lua"

        result = f"Tool '{command}' found in admin tools:\n"

        if client_file.exists():
            result += f"- Python client: tools/admin/{command}/client.py\n"

        if server_file.exists():
            result += f"- Lua server: tools/admin/{command}/server.lua\n"

        return result

    # If not found in expected locations, do a broader search
    matches = []

    # Search for any file containing the command name
    for client_py in base_path.glob(f"**/{command}*/*.py"):
        matches.append(str(client_py.relative_to(base_path)))

    for server_lua in base_path.glob(f"**/{command}*/*.lua"):
        matches.append(str(server_lua.relative_to(base_path)))

    if matches:
        return (
            f"Tool '{command}' not found directly, but these files might be related:\n- "
            + "\n- ".join(matches)
        )

    return f"Tool '{command}' not found in the tools directory"


@mcp.tool()
async def head(file_path: str, lines: int = 10) -> str:
    """
    Display the first lines of a file

    Args:
        file_path: Relative path to the file within the tools directory
        lines: Number of lines to show (default: 10)
    """
    base_path = _get_tools_base_path()
    target_file = base_path / file_path

    if not target_file.exists():
        return f"Error: File '{file_path}' does not exist"

    if not target_file.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        with open(target_file, "r") as f:
            content = f.readlines()[:lines]

        return (
            f"First {lines} lines of {file_path}:\n\n```python\n{''.join(content)}\n```"
        )
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@mcp.tool()
async def tail(file_path: str, lines: int = 10) -> str:
    """
    Display the last lines of a file

    Args:
        file_path: Relative path to the file within the tools directory
        lines: Number of lines to show (default: 10)
    """
    base_path = _get_tools_base_path()
    target_file = base_path / file_path

    if not target_file.exists():
        return f"Error: File '{file_path}' does not exist"

    if not target_file.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        with open(target_file, "r") as f:
            content = f.readlines()

        last_lines = content[-lines:] if lines < len(content) else content

        return f"Last {lines} lines of {file_path}:\n\n```python\n{''.join(last_lines)}\n```"
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@mcp.tool()
async def tree(path: str = "", max_depth: int = 3, show_hidden: bool = False) -> str:
    """
    Display directory structure in a tree-like format

    Args:
        path: Starting path within the tools directory (default: root tools dir)
        max_depth: Maximum directory depth to display
        show_hidden: Whether to show hidden and cache files/directories (default: False)
    """
    base_path = _get_tools_base_path()
    start_path = base_path if not path else base_path / path

    if not start_path.exists():
        return f"Error: Path '{path}' does not exist"

    if not start_path.is_dir():
        return f"Error: '{path}' is not a directory"

    result = []
    rel_start = start_path.relative_to(base_path)
    result.append(f"📁 {rel_start}/")

    # Patterns to exclude if show_hidden is False
    excluded_patterns = [
        "__pycache__",
        ".pytest_cache",
        ".pyc",
        ".pyo",
        ".pyd",
        ".coverage",
        ".git",
        ".DS_Store",
        ".idea",
        ".vscode",
        ".egg-info",
        "__MACOSX",
    ]

    def should_exclude(entry):
        if not show_hidden:
            name = entry.name
            # Check if the name is in excluded patterns
            return any(pattern in name for pattern in excluded_patterns)
        return False

    def add_tree(current_path, prefix="", depth=0):
        if depth >= max_depth:
            return

        try:
            # Get all entries in the directory
            all_entries = list(current_path.iterdir())

            # Filter out excluded entries
            filtered_entries = [e for e in all_entries if not should_exclude(e)]

            # Sort directories first, then files
            entries = sorted(filtered_entries, key=lambda x: (not x.is_dir(), x.name))

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "

                icon = "📁" if entry.is_dir() else "📄"
                result.append(f"{prefix}{connector}{icon} {entry.name}")

                if entry.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    add_tree(entry, new_prefix, depth + 1)
        except PermissionError:
            result.append(f"{prefix}└── ⚠️ Permission denied")
        except Exception as e:
            result.append(f"{prefix}└── ⚠️ Error: {str(e)}")

    add_tree(start_path)

    # Add a note about excluded files if any were excluded
    if not show_hidden:
        excluded_count = sum(1 for _ in start_path.rglob("__pycache__"))
        if excluded_count > 0:
            result.append(
                f"\nNote: {excluded_count} __pycache__ directories were excluded. Use show_hidden=True to show them."
            )

    return "\n".join(result)


@mcp.tool()
async def man(command: str) -> str:
    """
    Display the manual/documentation for a Factorio tool

    Args:
        command: Name of the tool to get documentation for: e.g "inspect_inventory", "craft_item", etc
    """
    base_path = _get_tools_base_path()
    agent_path = base_path / "agent"
    admin_path = base_path / "admin"

    # Check if it's an agent tool
    agent_dir = agent_path / command
    if agent_dir.exists() and agent_dir.is_dir():
        # Check for agent.md documentation
        doc_file = agent_dir / "agent.md"
        if doc_file.exists():
            try:
                with open(doc_file, "r") as f:
                    content = f.read()
                return f"Manual for '{command}':\n\n{content}"
            except Exception as e:
                return f"Error reading documentation for '{command}': {str(e)}"

        # If no dedicated doc file, try to generate from the implementation
        try:
            execution_path = (
                Path(os.path.dirname(os.path.realpath(__file__))).parent
                / Path("env")
                / Path("src")
            )
            generator = SystemPromptGenerator(str(execution_path))
            manual = generator.manual(command)
            if manual:
                return f"Manual for '{command}':\n\n{manual}"
            else:
                return f"No documentation found for '{command}'"
        except Exception as e:
            return f"Error generating documentation for '{command}': {str(e)}"

    # If not found, try admin tools
    admin_dir = admin_path / command
    if admin_dir.exists() and admin_dir.is_dir():
        # Similar logic for admin tools
        doc_file = admin_dir / "agent.md"
        if doc_file.exists():
            try:
                with open(doc_file, "r") as f:
                    content = f.read()
                return f"Manual for admin tool '{command}':\n\n{content}"
            except Exception as e:
                return (
                    f"Error reading documentation for admin tool '{command}': {str(e)}"
                )

    return f"No documentation found for tool '{command}'"


@mcp.tool()
async def whereis(keyword: str) -> str:
    """
    Find all occurrences related to a keyword in the tools directory

    Args:
        keyword: Keyword to search for in filenames, directories and code
    """
    base_path = _get_tools_base_path()

    results = {"directories": [], "files": [], "code_references": []}

    # Find directories matching the keyword
    for dir_path in base_path.glob(f"**/*{keyword}*"):
        if dir_path.is_dir():
            results["directories"].append(str(dir_path.relative_to(base_path)))

    # Find files with names matching the keyword
    for file_path in base_path.glob(f"**/*{keyword}*.*"):
        if file_path.is_file():
            results["files"].append(str(file_path.relative_to(base_path)))

    # Find source code references (limit to avoid huge searches)
    code_matches = []
    count = 0
    limit = 20

    for file_path in base_path.glob("**/*.py"):
        if count >= limit:
            break

        try:
            with open(file_path, "r") as f:
                content = f.read()

            if keyword.lower() in content.lower():
                rel_path = str(file_path.relative_to(base_path))
                code_matches.append(rel_path)
                count += 1
        except:
            pass

    for file_path in base_path.glob("**/*.lua"):
        if count >= limit:
            break

        try:
            with open(file_path, "r") as f:
                content = f.read()

            if keyword.lower() in content.lower():
                rel_path = str(file_path.relative_to(base_path))
                if rel_path not in code_matches:
                    code_matches.append(rel_path)
                    count += 1
        except:
            pass

    results["code_references"] = code_matches

    # Format the output
    output = f"Results for keyword '{keyword}':\n\n"

    if results["directories"]:
        output += "Directories:\n"
        for d in sorted(results["directories"]):
            output += f"  📁 {d}\n"
        output += "\n"

    if results["files"]:
        output += "Files:\n"
        for f in sorted(results["files"]):
            output += f"  📄 {f}\n"
        output += "\n"

    if results["code_references"]:
        output += "Code References:\n"
        for ref in sorted(results["code_references"]):
            output += f"  💻 {ref}\n"

        if count >= limit:
            output += f"  ... and potentially more (limited to {limit} results)\n"
        output += "\n"

    if not any(results.values()):
        output += f"No matches found for '{keyword}'\n"

    return output
