from typing import Any

from fle.envd.blueprints import (
    BlueprintError,
    BlueprintStore,
)
from fle.env.tools import Tool


class Blueprint(Tool):
    """Agent-facing blueprint library: save, place, list, get.

    Content lives in the generation-scoped store; agents normally reference
    blueprints by name rather than re-emitting exchange strings.
    """

    def _store(self) -> BlueprintStore:
        namespace = self.game_state
        store = getattr(namespace, "_blueprint_store", None)
        if store is None:
            # Ephemeral per-lease library when no scope was provisioned.
            store = getattr(namespace, "_ephemeral_blueprints", None)
            if store is None:
                store = BlueprintStore(scope=None)
                namespace._ephemeral_blueprints = store
        return store

    def _tick(self) -> int | None:
        getter = getattr(self.game_state, "get_elapsed_ticks", None) if hasattr(
            self.game_state, "get_elapsed_ticks"
        ) else getattr(self.game_state, "elapsed_ticks", None)
        try:
            return int(getter()) if callable(getter) else None
        except Exception:
            return None

    def __call__(self, command: str = "list", *args: Any, **kwargs: Any):
        handler = {
            "save": self.save,
            "place": self.place,
            "list": self.list_blueprints,
            "get": self.get,
        }.get(command)
        if handler is None:
            return {"error": f"unknown command: {command}"}
        return handler(*args, **kwargs)

    def save(self, name: str = "", x: float = 0, y: float = 0, radius: float = 0):
        capture, _ = self.execute(self.player_index, "capture", x, y, radius)
        if not isinstance(capture, dict) or capture.get("error"):
            return capture if isinstance(capture, dict) else {"error": str(capture)}
        content = str(capture.get("blueprint") or "").strip()
        # Undo the literal-quote wrapping applied Lua-side to survive the
        # RCON dump parser.
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        store = self._store()
        resolved_name = name or f"bp-{store.count() + 1}"
        record = store.save(
            resolved_name,
            content,
            entity_count=int(capture.get("entity_count") or 0),
            center_x=capture.get("center_x"),
            center_y=capture.get("center_y"),
            created_tick=self._tick(),
        )
        return {"saved": record.name, **record.summary()}

    def place(self, source: str = "", x: float = 0, y: float = 0):
        if not source:
            return {"error": "place requires a blueprint name or string"}
        store = self._store()
        record = store.try_get(source)
        content = record.content if record is not None else source
        from_store = record is not None
        result, _ = self.execute(self.player_index, "place", content, x, y)
        if isinstance(result, dict) and not result.get("error"):
            # Invoking a stored design counts as library use even when every
            # entity dedupes against existing world state.
            if from_store:
                store.record_use(record.name, self._tick())
            return {**result, "source": "library" if from_store else "inline"}
        return result if isinstance(result, dict) else {"error": str(result)}

    def list_blueprints(self):
        return {"blueprints": self._store().list_summaries()}

    def get(self, name: str = ""):
        try:
            record = self._store().get(name)
        except BlueprintError as exc:
            return {"error": str(exc)}
        return {
            "name": record.name,
            "content": record.content,
            "entity_count": record.entity_count,
        }
