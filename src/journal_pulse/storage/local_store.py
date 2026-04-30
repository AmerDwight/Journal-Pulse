import json
from pathlib import Path


class LocalObjectStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def put_json(self, key: str, payload: dict) -> None:
        target = self.root_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_json(self, key: str) -> dict:
        target = self.root_dir / key
        return json.loads(target.read_text(encoding='utf-8'))

    def list_keys(self, prefix: str = '') -> list[str]:
        results: list[str] = []
        for path in self.root_dir.rglob('*.json'):
            relative = path.relative_to(self.root_dir).as_posix()
            if relative.startswith(prefix):
                results.append(relative)
        return sorted(results)

    def exists(self, key: str) -> bool:
        return (self.root_dir / key).exists()
