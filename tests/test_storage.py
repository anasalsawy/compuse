from concurrent.futures import ThreadPoolExecutor

import pytest

from compuse.storage import EventIntegrityError, EventStore


def test_event_chain_is_verified_and_detects_tampering():
    store = EventStore()
    store.append("run", "created", {"value": 1}, "2026-01-01T00:00:00+00:00")
    store.append("run", "next", {"value": 2}, "2026-01-01T00:00:01+00:00")
    assert store.verify("run")
    store.db.execute("UPDATE events SET payload='{}' WHERE run_id='run' AND seq=1")
    assert not store.verify("run")
    with pytest.raises(EventIntegrityError):
        store.assert_integrity("run")
    store.close()


def test_sequence_gaps_are_rejected():
    store = EventStore()
    store.append("run", "created", {}, "2026-01-01T00:00:00+00:00")
    store.db.execute("UPDATE events SET seq=2 WHERE run_id='run' AND seq=1")
    assert not store.verify("run")
    store.close()


def test_empty_chain_is_valid():
    with EventStore() as store:
        assert store.verify("missing")


def test_concurrent_appends_are_serialized():
    with EventStore() as store:
        def append(index: int) -> int:
            return store.append("run", "event", {"index": index}, f"2026-01-01T00:00:{index:02d}+00:00")

        with ThreadPoolExecutor(max_workers=8) as pool:
            sequences = list(pool.map(append, range(20)))
        assert sorted(sequences) == list(range(1, 21))
        assert store.verify("run")
