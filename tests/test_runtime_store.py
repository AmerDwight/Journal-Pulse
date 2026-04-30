from pathlib import Path

from journal_pulse import cli
from journal_pulse.storage.local_store import LocalObjectStore
from journal_pulse.storage.memory import InMemoryObjectStore


class FailingMinIOStore:
    def __init__(self, *args, **kwargs):
        raise RuntimeError('minio unavailable')


def test_build_runtime_store_falls_back_to_local_store_if_minio_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr('journal_pulse.storage.minio_store.MinIOStore', FailingMinIOStore)
    settings = cli.Settings(data_root=Path(tmp_path))

    store = cli.build_runtime_store(settings)

    assert isinstance(store, LocalObjectStore)
    assert not isinstance(store, InMemoryObjectStore)
