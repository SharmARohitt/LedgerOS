import hashlib

from app.agents.audit_worker import _canonical_json


def test_canonical_json_is_stable_for_same_content():
    payload = {"b": 2, "a": 1, "nested": {"z": 1, "y": 2}}
    first = _canonical_json(payload)
    second = _canonical_json(dict(reversed(list(payload.items()))))
    assert first == second
    assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(second.encode()).hexdigest()


def test_hash_changes_when_content_changes():
    base = _canonical_json({"decision_type": "AUTO_RESOLVE", "confidence": 91.0})
    changed = _canonical_json({"decision_type": "AUTO_RESOLVE", "confidence": 91.1})
    assert hashlib.sha256(base.encode()).hexdigest() != hashlib.sha256(changed.encode()).hexdigest()
