from app.storage.repositories.events_repo import get_by_source_event_id, upsert_event


def test_duplicate_webhook_delivery_does_not_create_second_event(db):
    defaults = {
        "event_type": "PAYMENT_SUCCEEDED",
        "source_mode": "SIMULATED",
        "amount": 48750.00,
        "currency": "USD",
        "event_timestamp": "2026-01-01T00:00:00Z",
        "metadata_json": "{}",
        "raw_reference": "{}",
        "normalized_reference": "{}",
        "processing_state": "RECEIVED",
    }

    first, created_first = upsert_event(db, source="dodo", source_event_id="evt_dup_1", defaults=defaults)
    second, created_second = upsert_event(db, source="dodo", source_event_id="evt_dup_1", defaults=defaults)
    db.commit()

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.retry_count == 1

    stored = get_by_source_event_id(db, "dodo", "evt_dup_1")
    assert stored is not None
    assert stored.id == first.id
