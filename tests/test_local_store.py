from journal_pulse.storage.local_store import LocalObjectStore


def test_local_object_store_round_trips_json_payloads(tmp_path):
    store = LocalObjectStore(root_dir=tmp_path)
    payload = {'article_id': 'a-1', 'title': 'A discovery'}

    store.put_json('articles/a-1.json', payload)

    assert store.exists('articles/a-1.json') is True
    assert store.get_json('articles/a-1.json') == payload
    assert store.list_keys('articles/') == ['articles/a-1.json']
