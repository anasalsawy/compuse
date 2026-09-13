from compuse.storage import EventIntegrityError, EventStore

def test_event_chain_is_verified_and_detects_tampering():
    store = EventStore()
    store.append("run", "created", {"value": 1}, "2026-01-01T00:00:00+00:00")
    store.append("run", "next", {"value": 2}, "2026-01-01T00:00:01+00:00")
    assert store.verify("run")
    store.db.execute("UPDATE events SET payload='{}' WHERE run_id='run' AND seq=1")
    store.db.commit()
    assert not store.verify("run")
    try:
        store.assert_integrity("run")
    except EventIntegrityError:
        pass
    else:
        raise AssertionError("tampered chain was accepted")

def test_sequence_gaps_are_rejected():
    store = EventStore()
    store.append("run", "created", {}, "2026-01-01T00:00:00+00:00")
    store.db.execute("UPDATE events SET seq=2 WHERE run_id='run' AND seq=1")
    store.db.commit()
    assert not store.verify("run")
