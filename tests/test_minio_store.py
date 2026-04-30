from journal_pulse.storage.minio_store import MinIOStore


class DummyResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class DummyObjectInfo:
    def __init__(self, object_name: str):
        self.object_name = object_name


class DummyMinioClient:
    def __init__(self):
        self.created_buckets: list[str] = []
        self.objects: dict[str, bytes] = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.created_buckets

    def make_bucket(self, bucket_name: str) -> None:
        self.created_buckets.append(bucket_name)

    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str) -> None:
        self.objects[object_name] = data.read()

    def get_object(self, bucket_name: str, object_name: str) -> DummyResponse:
        return DummyResponse(self.objects[object_name])

    def list_objects(self, bucket_name: str, prefix: str = '', recursive: bool = True):
        return [DummyObjectInfo(name) for name in sorted(self.objects) if name.startswith(prefix)]

    def stat_object(self, bucket_name: str, object_name: str) -> object:
        if object_name not in self.objects:
            raise RuntimeError('not found')
        return object()


def test_minio_store_round_trips_json_with_bucket_management():
    store = MinIOStore.__new__(MinIOStore)
    store.client = DummyMinioClient()
    store.bucket_name = 'journal-raw'

    store.put_json('articles/demo.json', {'title': 'demo'})

    assert store.client.created_buckets == ['journal-raw']
    assert store.exists('articles/demo.json') is True
    assert store.get_json('articles/demo.json') == {'title': 'demo'}
    assert store.list_keys('articles/') == ['articles/demo.json']
