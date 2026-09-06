"""Filesystem-backed object storage abstraction. Swappable for a
MinIO/S3-compatible backend later without touching callers — everything goes
through put_object/get_object."""

import os
from pathlib import Path

from app.core.config import get_settings


class ObjectStore:
    def __init__(self, base_path: str | None = None):
        self._base = Path(base_path or get_settings().object_store_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def put_object(self, key: str, content: str) -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def get_object(self, key: str) -> str:
        path = self._base / key
        return path.read_text(encoding="utf-8")

    def exists(self, key: str) -> bool:
        return (self._base / key).exists()


_store: ObjectStore | None = None


def get_object_store() -> ObjectStore:
    global _store
    if _store is None:
        _store = ObjectStore()
    return _store
