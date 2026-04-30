from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.query import find_article_by_title, format_article_detail, get_article_by_id
from journal_pulse.storage.memory import InMemoryObjectStore


def test_get_article_by_id_reads_article_record_from_store():
    store = InMemoryObjectStore()
    article = ArticleRecord(
        source='crossref',
        source_type='api',
        article_id='10.1000-crossref-1',
        title='Crossref paper',
        url='https://doi.org/10.1000/crossref-1',
        doi='10.1000/crossref-1',
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary='summary',
    )
    store.put_json('articles/doi-10.1000-crossref-1.json', article.model_dump(mode='json'))

    loaded = get_article_by_id(store=store, article_id='doi-10.1000-crossref-1')

    assert loaded.article_id == '10.1000-crossref-1'
    assert loaded.title == 'Crossref paper'
    assert loaded.doi == '10.1000/crossref-1'


def test_find_article_by_title_returns_best_case_insensitive_match():
    store = InMemoryObjectStore()
    cancer = ArticleRecord(
        source='nature',
        source_type='rss',
        article_id='nature-1',
        title='Cancer breakthrough in mice',
        url='https://example.com/nature-1',
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary='summary',
    )
    protein = ArticleRecord(
        source='science',
        source_type='rss',
        article_id='science-1',
        title='Protein folding benchmark',
        url='https://example.com/science-1',
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary='summary',
    )
    store.put_json('articles/url-1.json', cancer.model_dump(mode='json'))
    store.put_json('articles/url-2.json', protein.model_dump(mode='json'))

    matched = find_article_by_title(store=store, title_query='protein folding')

    assert matched is not None
    assert matched.article_id == 'science-1'


def test_format_article_detail_includes_key_metadata_for_mention_reply():
    article = ArticleRecord(
        source='science',
        source_type='rss',
        article_id='science-2',
        title='Protein folding benchmark',
        url='https://example.com/science-2',
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        doi='10.1000/science-2',
        summary='English summary',
        abstract='Detailed abstract',
        metadata={'journal': 'Science'},
    )

    detail = format_article_detail(article, zh_summary='中文摘要內容')

    assert 'Protein folding benchmark' in detail
    assert '中文摘要：中文摘要內容' in detail
    assert 'DOI：10.1000/science-2' in detail
    assert 'URL：https://example.com/science-2' in detail
