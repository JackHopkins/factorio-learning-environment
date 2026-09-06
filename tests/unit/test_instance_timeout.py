"""Timeout behavior tests that require no Factorio server."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest

from fle.env import FactorioInstance


def test_timed_out_evaluation_stops_before_later_side_effects() -> None:
    release = Event()
    started = Event()
    changed = Event()

    def delayed_eval(code: str) -> None:
        started.set()
        release.wait()
        changed.set()

    instance = FactorioInstance.__new__(FactorioInstance)
    instance.namespaces = [SimpleNamespace(eval_with_timeout=delayed_eval)]
    instance._executor = ThreadPoolExecutor(max_workers=1)

    try:
        with pytest.raises(TimeoutError):
            instance.eval_with_error("unused", timeout=0.01)
        assert started.is_set()
    finally:
        release.set()
        instance._executor.shutdown(wait=True, cancel_futures=True)

    assert not changed.is_set()
