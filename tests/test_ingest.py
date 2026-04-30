from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.ingest import crawl_sources_once
from journal_pulse.sources.base import SourceDefinition, SourceRegistry
from journal_pulse.storage.memory import InMemoryObjectStore


class StubAdapter:
    def __init__(self, definition: SourceDefinition, articles: list[ArticleRecord]):
        self.definition = definition
        self.endpoint = definition.endpoint
        self._articles = articles

    def fetch(self) -> list[ArticleRecord]:
        return list(self._articles)



def test_crawl_sources_once_fetches_deduplicates_and_persists_articles():
    first = ArticleRecord(
        source="nature",
        source_type="rss",
        article_id="nature-1",
        title="Shared discovery",
        url="https://example.com/articles/1?utm_source=rss",
        doi="10.1000/shared",
        published_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
    duplicate = ArticleRecord(
        source="pubmed",
        source_type="api",
        article_id="pmid-1",
        title="Shared discovery",
        url="https://pubmed.ncbi.nlm.nih.gov/1/",
        doi="10.1000/shared",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary="enriched metadata",
    )

    registry = SourceRegistry()
    registry.register("rss", lambda definition: StubAdapter(definition, [first]))
    registry.register("api", lambda definition: StubAdapter(definition, [duplicate]))

    store = InMemoryObjectStore()
    sources = [
        SourceDefinition(name="nature", source_type="rss", endpoint="https://example.com/feed.xml"),
        SourceDefinition(name="pubmed", source_type="api", endpoint="https://example.com/esummary"),
    ]

    digest = crawl_sources_once(sources=sources, registry=registry, store=store, generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc))

    assert [article.article_id for article in digest.articles] == ["pmid-1"]
    assert store.list_keys("articles/") == ["articles/doi-10.1000-shared.json"]
    stored_article = store.get_json("articles/doi-10.1000-shared.json")
    assert stored_article["article_id"] == "pmid-1"
    assert store.list_keys("reports/") == ["reports/daily-digest-2026-04-25.json"]
