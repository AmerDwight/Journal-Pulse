from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord


def test_article_record_prefers_doi_for_dedup_key():
    article = ArticleRecord(
        source="nature",
        source_type="rss",
        article_id="nature-1",
        title="A discovery",
        url="https://example.com/articles/123?utm_source=rss",
        doi="10.1000/xyz123",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )

    assert article.dedup_key == "doi:10.1000/xyz123"


def test_article_record_falls_back_to_normalized_url_for_dedup_key():
    article = ArticleRecord(
        source="crossref",
        source_type="api",
        article_id="crossref-1",
        title="A discovery",
        url="https://example.com/articles/123/?utm_source=rss&utm_medium=email",
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )

    assert article.dedup_key == "url:https://example.com/articles/123"
