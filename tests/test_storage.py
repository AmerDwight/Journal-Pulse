from journal_pulse.storage.base import ObjectStore
from journal_pulse.storage.memory import InMemoryObjectStore


def test_in_memory_object_store_round_trips_json_payloads():
    store: ObjectStore = InMemoryObjectStore()
    payload = {"article_id": "a-1", "title": "A discovery"}

    store.put_json("articles/a-1.json", payload)

    assert store.exists("articles/a-1.json") is True
    assert store.get_json("articles/a-1.json") == payload


def test_in_memory_object_store_lists_keys_by_prefix():
    store = InMemoryObjectStore()
    store.put_json("articles/a-1.json", {"article_id": "a-1"})
    store.put_json("articles/a-2.json", {"article_id": "a-2"})
    store.put_json("reports/digest.json", {"generated_at": "2026-04-25T00:00:00+00:00"})

    assert store.list_keys(prefix="articles/") == ["articles/a-1.json", "articles/a-2.json"]
