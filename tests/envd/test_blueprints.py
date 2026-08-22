import pytest

from fle.envd.blueprints import (
    DEFAULT_MAX_PER_SCOPE,
    BlueprintInvalid,
    BlueprintNotFound,
    BlueprintQuotaExceeded,
    BlueprintStore,
)

pytestmark = pytest.mark.no_factorio

CONTENT_A = "0eNrd0s0KgzAQBOB3uZmuQm9pL7aIjYp+O4NkVdC7O8CwM5nhzcyBJJrGK1lWgE2ytTAwqNZBhRyqHFTIocJBhRwyHFSiocKBhRwyHFSiocKBhQ=="
CONTENT_B = "0eNrNys0KgCAQBtB3uZkuQnfpLzaKjUp/OoNkdRC7uwEcT2b6MlJIIm2skmUF2CRbCxODaj1UyKHCQYUcKhxUyKHCRYUcMhxUyKHCQYUcMhw="


@pytest.fixture
def store(tmp_path):
    return BlueprintStore(scope="gen-1", db_path=tmp_path / "bp.db")


def test_save_get_roundtrip_persistent(store):
    record = store.save(
        "smelter", CONTENT_A, entity_count=12, center_x=1.0, center_y=-2.0
    )
    assert record.entity_count == 12
    fetched = store.get("smelter")
    assert fetched.content == CONTENT_A
    assert fetched.content_sha256.startswith(record.content_sha256[:12])


def test_scope_isolation(tmp_path):
    db = tmp_path / "bp.db"
    first = BlueprintStore(scope="gen-1", db_path=db)
    second = BlueprintStore(scope="gen-2", db_path=db)
    first.save("shared-name", CONTENT_A)
    with pytest.raises(BlueprintNotFound):
        second.get("shared-name")
    assert second.count() == 0


def test_ephemeral_store_never_touches_disk():
    store = BlueprintStore(scope=None)
    store.save("temp", CONTENT_A)
    assert store.persistent is False
    assert store.count() == 1
    assert store.get("temp").content == CONTENT_A


def test_quota_enforced_on_unique_names(store):
    tiny = BlueprintStore(
        scope="tiny",
        db_path=store._db_path,
        max_per_scope=1,
    )
    tiny.save("one", CONTENT_A)
    with pytest.raises(BlueprintQuotaExceeded):
        tiny.save("two", CONTENT_B)


def test_overwrite_keeps_usage_counters(store):
    store.save("pair", CONTENT_A)
    store.record_use("pair", tick=100)
    store.record_use("pair", tick=200)
    updated = store.save("pair", CONTENT_B)
    assert updated.times_placed == 2
    assert updated.last_used_tick == 200
    assert updated.content == CONTENT_B


def test_record_use_missing_name_is_silent(store):
    store.record_use("ghost", tick=1)
    assert store.count() == 0


def test_invalid_inputs_rejected(store):
    with pytest.raises(BlueprintInvalid):
        store.save("bad name!", CONTENT_A)
    with pytest.raises(BlueprintInvalid):
        store.save("ok-name", "not-a-blueprint")
    with pytest.raises(BlueprintInvalid):
        store.save("ok-name", "0" + "x" * 600_000)


def test_prune_by_min_times_placed(store):
    store.save("used", CONTENT_A)
    store.save("unused", CONTENT_B)
    store.record_use("used", tick=10)
    removed = store.prune(min_times_placed=1)
    assert removed == ["unused"]
    assert store.get("used").name == "used"


def test_prune_keep_newest(store):
    for index in range(5):
        store.save(f"bp-{index}", CONTENT_A if index % 2 else CONTENT_B)
    removed = store.prune(keep_newest=2)
    # Keeps the two most-placed/newest entries; exact tie-break by age.
    assert len(removed) == 3
    assert store.count() == 2


def test_drop_scope(store):
    store.save("a", CONTENT_A)
    store.save("b", CONTENT_B)
    dropped = store.drop_scope()
    assert dropped == 2
    assert store.count() == 0


def test_default_quota_is_generous():
    assert DEFAULT_MAX_PER_SCOPE >= 16
