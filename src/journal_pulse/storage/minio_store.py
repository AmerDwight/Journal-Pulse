import json
from io import BytesIO
from typing import Any

from journal_pulse.storage.base import ObjectStore


class MinIOStore(ObjectStore):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str, secure: bool = False):
        from minio import Minio

        self.client: Any = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket_name = bucket_name

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def put_json(self, key: str, payload: dict) -> None:
        self.ensure_bucket()
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        self.client.put_object(
            self.bucket_name,
            key,
            BytesIO(data),
            length=len(data),
            content_type='application/json',
        )

    def get_json(self, key: str) -> dict:
        response = self.client.get_object(self.bucket_name, key)
        try:
            return json.loads(response.read().decode('utf-8'))
        finally:
            response.close()
            response.release_conn()

    def list_keys(self, prefix: str = '') -> list[str]:
        return sorted(object_info.object_name for object_info in self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True))

    def exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, key)
            return True
        except Exception:
            return False
