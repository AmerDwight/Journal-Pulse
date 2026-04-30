from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from journal_pulse.models import ArticleRecord


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    endpoint: str
    source_type: str = 'rss'
    category: str = 'journal'
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feed_url(self) -> str:
        return self.endpoint


class SourceAdapter(Protocol):
    definition: SourceDefinition
    endpoint: str

    def fetch(self) -> Iterable[ArticleRecord]: ...


class SourceRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[SourceDefinition], SourceAdapter]] = {}

    def register(self, source_type: str, factory: Callable[[SourceDefinition], SourceAdapter]) -> None:
        self._factories[source_type] = factory

    def build(self, definition: SourceDefinition) -> SourceAdapter:
        try:
            factory = self._factories[definition.source_type]
        except KeyError as exc:
            raise KeyError(f'No adapter registered for source_type={definition.source_type!r}') from exc
        return factory(definition)
