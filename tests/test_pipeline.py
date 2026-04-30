from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.pipeline import build_digest


def test_build_digest_sorts_articles_by_published_date_desc():
    older = ArticleRecord(
        source="nature",
        article_id="1",
        title="Older",
        url="https://example.com/1",
        published_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        summary="older",
        abstract="older",
    )
    newer = ArticleRecord(
        source="science",
        article_id="2",
        title="Newer",
        url="https://example.com/2",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary="newer",
        abstract="newer",
    )

    digest = build_digest([older, newer], generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc))

    assert [article.article_id for article in digest.articles] == ["2", "1"]


def test_build_digest_deduplicates_articles_by_canonical_key():
    first = ArticleRecord(
        source="nature",
        source_type="rss",
        article_id="nature-1",
        title="Shared discovery",
        url="https://example.com/articles/123?utm_source=rss",
        doi="10.1000/shared",
        published_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
    duplicate = ArticleRecord(
        source="crossref",
        source_type="api",
        article_id="crossref-1",
        title="Shared discovery",
        url="https://example.com/articles/123",
        doi="10.1000/shared",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary="more complete summary",
    )

    digest = build_digest([first, duplicate], generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc))

    assert [article.article_id for article in digest.articles] == ["crossref-1"]
    assert digest.articles[0].summary == "more complete summary"


def test_build_digest_filters_low_signal_aggregator_records():
    crossref_book = ArticleRecord(
        source="crossref",
        source_type="api",
        article_id="crossref-book-1",
        title="Handbook chapter",
        url="https://doi.org/10.1000/book-chapter",
        doi="10.1000/book-chapter",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        metadata={"content_type": "book-chapter", "journal": ""},
    )
    nature_article = ArticleRecord(
        source="nature",
        source_type="rss",
        article_id="nature-1",
        title="Nature discovery",
        url="https://www.nature.com/articles/123",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )

    digest = build_digest([crossref_book, nature_article], generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc))

    assert [article.article_id for article in digest.articles] == ["nature-1"]


def test_build_digest_ranks_high_signal_journal_sources_above_aggregators():
    crossref_article = ArticleRecord(
        source="crossref",
        source_type="api",
        article_id="crossref-2",
        title="Metadata-only article",
        url="https://doi.org/10.1000/crossref-2",
        doi="10.1000/crossref-2",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        metadata={"content_type": "journal-article", "journal": "Nature"},
    )
    nature_article = ArticleRecord(
        source="nature",
        source_type="rss",
        article_id="nature-2",
        title="Primary feed article",
        url="https://www.nature.com/articles/456",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        summary="Richer source context",
    )

    digest = build_digest([crossref_article, nature_article], generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc))

    assert [article.article_id for article in digest.articles] == ["nature-2", "crossref-2"]
