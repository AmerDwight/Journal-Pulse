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



def test_crawl_sources_once_does_not_cache_title_only_summary_text():
    article = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-title-only',
        title='The equity paradox of environmental DNA for biodiversity monitoring',
        url='https://example.com/articles/title-only',
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        summary='''<p>Nature, Published online: 28 April 2026; <a href="https://www.nature.com/articles/d41586-026-01349-3">doi:10.1038/d41586-026-01349-3</a></p>The equity paradox of environmental DNA for biodiversity monitoring''',
    )
    registry = SourceRegistry()
    registry.register('rss', lambda definition: StubAdapter(definition, [article]))
    store = InMemoryObjectStore()
    summarizer = DummySummarizer('這其實只是標題翻譯')

    crawl_sources_once(
        sources=[SourceDefinition(name='nature', source_type='rss', endpoint='https://example.com/feed.xml')],
        registry=registry,
        store=store,
        summarizer=summarizer,
        generated_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )

    stored_article = store.get_json('articles/url-https-example.com-articles-title-only.json')
    assert stored_article.get('summary_zh', '') in {'', None}
    assert stored_article.get('brief_summary_zh', '') in {'', None}
    assert summarizer.calls == []


def test_crawl_sources_once_reuses_cached_summaries_for_existing_articles_before_calling_summarizer():
    article = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-existing',
        title='Existing discovery',
        url='https://example.com/articles/existing',
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        summary='Fresh English summary that would be expensive to re-summarize.',
    )
    registry = SourceRegistry()
    registry.register('rss', lambda definition: StubAdapter(definition, [article]))
    store = InMemoryObjectStore()
    store.put_json(
        'articles/url-https-example.com-articles-existing.json',
        article.model_copy(
            update={
                'summary_zh': '已快取的中文摘要。',
                'brief_summary_zh': '已快取的短摘要。',
            }
        ).model_dump(mode='json')
    )
    summarizer = DummySummarizer('不應被呼叫')

    digest = crawl_sources_once(
        sources=[SourceDefinition(name='nature', source_type='rss', endpoint='https://example.com/feed.xml')],
        registry=registry,
        store=store,
        summarizer=summarizer,
        generated_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )

    assert summarizer.calls == []
    assert digest.articles[0].summary_zh == '已快取的中文摘要。'
    assert digest.articles[0].brief_summary_zh == '已快取的短摘要。'
    stored_article = store.get_json('articles/url-https-example.com-articles-existing.json')
    assert stored_article['summary_zh'] == '已快取的中文摘要。'
    assert stored_article['brief_summary_zh'] == '已快取的短摘要。'


def test_crawl_sources_once_only_calls_summarizer_for_new_articles_missing_cached_summaries():
    existing = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-existing',
        title='Existing discovery',
        url='https://example.com/articles/existing',
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        summary='Existing English summary.',
    )
    new_article = ArticleRecord(
        source='science',
        source_type='rss',
        article_id='science-new',
        title='New discovery',
        url='https://example.com/articles/new',
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary='New English summary that should be summarized once.',
    )
    registry = SourceRegistry()
    registry.register('rss', lambda definition: StubAdapter(definition, [existing] if definition.name == 'nature' else [new_article]))
    store = InMemoryObjectStore()
    store.put_json(
        'articles/url-https-example.com-articles-existing.json',
        existing.model_copy(
            update={
                'summary_zh': '已快取的中文摘要。',
                'brief_summary_zh': '已快取的短摘要。',
            }
        ).model_dump(mode='json')
    )
    summarizer = DummySummarizer('給新文章的中文摘要。')

    digest = crawl_sources_once(
        sources=[
            SourceDefinition(name='nature', source_type='rss', endpoint='https://example.com/nature.xml'),
            SourceDefinition(name='science', source_type='rss', endpoint='https://example.com/science.xml'),
        ],
        registry=registry,
        store=store,
        summarizer=summarizer,
        generated_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )

    assert len(summarizer.calls) == 1
    assert summarizer.calls[0]['title'] == 'New discovery'
    by_title = {article.title: article for article in digest.articles}
    assert by_title['Existing discovery'].summary_zh == '已快取的中文摘要。'
    assert by_title['New discovery'].summary_zh == '給新文章的中文摘要。'


def test_crawl_sources_once_ignores_invalid_cached_article_payloads():
    article = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-invalid-cache',
        title='Recovered after bad cache',
        url='https://example.com/articles/invalid-cache',
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary='Fresh summary text that should be used when cache payload is invalid.',
    )
    registry = SourceRegistry()
    registry.register('rss', lambda definition: StubAdapter(definition, [article]))
    store = InMemoryObjectStore()
    store.put_json('articles/url-https-example.com-articles-invalid-cache.json', {'bad': 'payload'})
    summarizer = DummySummarizer('新的中文摘要。')

    digest = crawl_sources_once(
        sources=[SourceDefinition(name='nature', source_type='rss', endpoint='https://example.com/feed.xml')],
        registry=registry,
        store=store,
        summarizer=summarizer,
        generated_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )

    assert len(summarizer.calls) == 1
    assert digest.articles[0].summary_zh == '新的中文摘要。'
    stored_article = store.get_json('articles/url-https-example.com-articles-invalid-cache.json')
    assert stored_article['summary_zh'] == '新的中文摘要。'
