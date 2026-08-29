from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Dict, List, Optional

from fle.commons.models.technology_state import TechnologyState


@dataclass
class ResearchState:
    """Complete research state including all technologies and current research"""

    technologies: Dict[str, TechnologyState]
    current_research: Optional[str]
    research_progress: float
    research_queue: List[str]
    progress: Dict


RESEARCH_STATE_IDENTITY_VERSION = "research-state-identity-v1"


def _clean_research_name(value: Any) -> str:
    """Normalize names returned by either the full or compact Lua save."""

    name = str(value)
    if len(name) >= 2 and name[0] == name[-1] == '"':
        return name[1:-1]
    return name


def _research_number(value: Any, *, default: float = 0.0) -> int | float:
    """Keep numeric identity fields stable across Lua/Python number types."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if isfinite(number):
            return int(number) if number.is_integer() else number
    return default


def _research_sequence(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        numeric_keys: list[tuple[int, Any]] = []
        for key, item in value.items():
            try:
                numeric_keys.append((int(key), item))
            except (TypeError, ValueError):
                # A malformed queue is not allowed to break state hashing.
                continue
        return [item for _, item in sorted(numeric_keys)]
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _research_mapping(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def research_state_identity(state: ResearchState | Mapping[str, Any] | None) -> dict:
    """Return the compact, dynamic portion that identifies research state.

    Technology prerequisites and science ingredients are static prototype
    metadata. They make full research saves expensive without adding useful
    information to a world-state digest, so identity retains only researched
    levels, disabled technologies, active progress, and queue order. The
    helper accepts both a parsed ``ResearchState`` and the sparse mapping
    returned by ``save_research_state(..., compact=True)``.
    """

    if isinstance(state, ResearchState):
        raw: Mapping[str, Any] = {
            "technologies": state.technologies,
            "current_research": state.current_research,
            "research_progress": state.research_progress,
            "research_queue": state.research_queue,
            "progress": state.progress,
        }
    elif isinstance(state, Mapping):
        # Permit callers to pass an envelope without making the wire format
        # part of the public identity representation.
        nested = state.get("identity")
        raw = nested if isinstance(nested, Mapping) else state
    else:
        raw = {}

    researched: dict[str, int | float] = {}
    disabled: set[str] = set()

    compact_researched = raw.get("researched")
    if isinstance(compact_researched, Mapping):
        for name, level in compact_researched.items():
            clean_name = _clean_research_name(name)
            if clean_name:
                researched[clean_name] = _research_number(level, default=1)
    elif isinstance(compact_researched, (list, tuple)):
        for name in compact_researched:
            clean_name = _clean_research_name(name)
            if clean_name:
                researched[clean_name] = 1

    raw_technologies = raw.get("technologies")
    if isinstance(raw_technologies, Mapping):
        for key, technology in raw_technologies.items():
            clean_name = _clean_research_name(key)
            if not clean_name:
                continue
            if isinstance(technology, Mapping):
                researched_value = technology.get("researched", False)
                enabled_value = technology.get("enabled", True)
                level_value = technology.get("level", 1)
            else:
                researched_value = getattr(technology, "researched", False)
                enabled_value = getattr(technology, "enabled", True)
                level_value = getattr(technology, "level", 1)
            if researched_value:
                researched[clean_name] = _research_number(level_value, default=1)
            if enabled_value is False:
                disabled.add(clean_name)

    compact_disabled = raw.get("disabled")
    if isinstance(compact_disabled, Mapping):
        disabled_names = compact_disabled.keys()
    else:
        disabled_names = _research_sequence(compact_disabled)
    for name in disabled_names:
        clean_name = _clean_research_name(name)
        if clean_name:
            disabled.add(clean_name)

    current_research = raw.get("current_research")
    if current_research in (None, ""):
        current_name = None
    else:
        current_name = _clean_research_name(current_research)

    progress: dict[str, int | float] = {}
    for name, value in _research_mapping(raw.get("progress")).items():
        clean_name = _clean_research_name(name)
        if clean_name:
            progress[clean_name] = _research_number(value)

    queue = []
    for name in _research_sequence(raw.get("research_queue")):
        clean_name = _clean_research_name(name)
        if clean_name:
            queue.append(clean_name)

    return {
        "schema_version": RESEARCH_STATE_IDENTITY_VERSION,
        "researched": {
            name: researched[name] for name in sorted(researched)
        },
        "disabled": sorted(disabled),
        "current_research": current_name,
        "research_progress": _research_number(
            raw.get("research_progress"), default=0.0
        ),
        "research_queue": queue,
        "progress": {name: progress[name] for name in sorted(progress)},
    }
