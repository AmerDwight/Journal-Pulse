from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord, DailyDigest
from journal_pulse.services.monitoring import (
    build_new_articles_digest,
    format_discord_broadcast,
    summarize_new_articles,
)


def test_build_new_articles_digest_returns_only_articles_not_seen_in_previous_report():
    old_article = ArticleRecord(
        source='nature',
        article_id='nature-1',
        title='Known paper',
        url='https://example.com/nature-1',
        published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )
    new_article = ArticleRecord(
        source='science',
        article_id='science-1',
        title='Fresh paper',
        url='https://example.com/science-1',
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    previous_digest = DailyDigest(
        generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        articles=[old_article],
    )
    current_digest = DailyDigest(
        generated_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        articles=[new_article, old_article],
    )

    delta = build_new_articles_digest(current_digest=current_digest, previous_digest=previous_digest)

    assert [article.article_id for article in delta.articles] == ['science-1']


def test_summarize_new_articles_reports_no_updates_when_delta_is_empty():
    empty_delta = DailyDigest(
        generated_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        articles=[],
    )

    summary = summarize_new_articles(empty_delta)

    assert 'No new articles' in summary


def test_format_discord_broadcast_keeps_broadcast_concise_with_title_and_chinese_summary_only():
    delta = DailyDigest(
        generated_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        articles=[
            ArticleRecord(
                source='nature',
                article_id='nature-2',
                title='Cancer breakthrough',
                url='https://example.com/nature-2',
                published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
                summary='English summary 1',
            ),
            ArticleRecord(
                source='science',
                article_id='science-2',
                title='Protein folding update',
                url='https://example.com/science-2',
                published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
                summary='English summary 2',
            ),
        ],
    )

    translated = iter(['中文摘要一', '中文摘要二'])
    message = format_discord_broadcast(delta, summary_builder=lambda article: next(translated))

    assert '2 new articles detected' in message
    assert '- Cancer breakthrough' in message
    assert '  中文摘要：中文摘要一' in message
    assert 'https://example.com/science-2' not in message
    assert '[nature]' not in message
