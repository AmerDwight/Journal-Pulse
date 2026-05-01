from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.ingest import crawl_sources_once
from journal_pulse.sources.base import SourceDefinition, SourceRegistry
from journal_pulse.storage.memory import InMemoryObjectStore


class DummySummarizer:
    def __init__(self, summarized_text: str):
        self.summarized_text = summarized_text
        self.calls = []

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str:
        self.calls.append({'title': title, 'source_text': source_text, 'max_chars': max_chars})
        return self.summarized_text


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


def test_crawl_sources_once_persists_cached_chinese_summaries_when_summarizer_is_available():
    article = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-2',
        title='Cancer discovery',
        url='https://example.com/articles/2',
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        summary='This paper explains a new cancer treatment pathway in detail.',
    )
    registry = SourceRegistry()
    registry.register('rss', lambda definition: StubAdapter(definition, [article]))
    store = InMemoryObjectStore()
    summarizer = DummySummarizer('這篇論文說明一種新的癌症治療路徑，並展示初步成果與限制。')

    crawl_sources_once(
        sources=[SourceDefinition(name='nature', source_type='rss', endpoint='https://example.com/feed.xml')],
        registry=registry,
        store=store,
        summarizer=summarizer,
        generated_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )

    stored_article = store.get_json('articles/url-https-example.com-articles-2.json')
    assert stored_article['summary_zh'] == '這篇論文說明一種新的癌症治療路徑，並展示初步成果與限制。'
    assert stored_article['brief_summary_zh'] == '這篇論文說明一種新的癌症治療路徑，並展示初步成果與限制。'
    assert summarizer.calls == [
        {
            'title': 'Cancer discovery',
            'source_text': 'This paper explains a new cancer treatment pathway in detail.',
            'max_chars': 160,
        }
    ]
