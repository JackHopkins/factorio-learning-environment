"""Verifiers v1 taskset selecting FLE's stable Factorio microtask suite."""

from collections.abc import Iterator
from typing import Literal

import verifiers.v1 as vf
from pydantic import Field

from fle.integrations.prime_v1.taskset import (
    FactorioTask,
    FactorioTaskset,
    FactorioTasksetConfig,
)


class FactorioMicrotasksConfig(FactorioTasksetConfig):
    """Configuration for the published `api_microtasks_v1` benchmark."""

    benchmark_suites: list[str] = Field(default_factory=lambda: ["api_microtasks_v1"])
    benchmark_statuses: list[
        Literal["ready", "calibration_required", "spec_only", "planned"]
    ] = Field(default_factory=lambda: ["ready"])
    task_ids: list[str] = Field(default_factory=list)


class FactorioMicrotasksTaskset(vf.Taskset[FactorioTask, FactorioMicrotasksConfig]):
    """Pinned microtask selection delegating execution to FLE's taskset."""

    def load(self) -> Iterator[FactorioTask]:
        # Reuse the canonical FLE construction path while binding a narrower
        # config type so Verifiers exposes the correct CLI/TOML schema.
        return FactorioTaskset(self.config).load()
