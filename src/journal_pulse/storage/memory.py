class InMemoryObjectStore:
    def __init__(self) -> None:
        self._objects: dict[str, dict] = {}

    def put_json(self, key: str, payload: dict) -> None:
        self._objects[key] = payload.copy()

    def get_json(self, key: str) -> dict:
        return self._objects[key].copy()

    def list_keys(self, prefix: str = '') -> list[str]:
        return sorted(key for key in self._objects if key.startswith(prefix))

    def exists(self, key: str) -> bool:
        return key in self._objects
