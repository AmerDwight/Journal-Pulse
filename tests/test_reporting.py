from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord, DailyDigest
from journal_pulse.reporting.markdown import MarkdownReporter


def test_markdown_report_groups_articles_by_source():
    reporter = MarkdownReporter()
    digest = DailyDigest(
        generated_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        articles=[
            ArticleRecord(
                source="nature",
                article_id="nature-1",
                title="A discovery",
                url="https://example.com/nature-1",
                published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
                summary="Nature summary",
                abstract="Detailed abstract",
            ),
            ArticleRecord(
                source="science",
                article_id="science-1",
                title="Another paper",
                url="https://example.com/science-1",
                published_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
                summary="Science summary",
                abstract="Detailed abstract",
            ),
        ],
    )

    rendered = reporter.render(digest)

    assert "# Daily Journal Digest" in rendered
    assert "## nature" in rendered
    assert "## science" in rendered
    assert "A discovery" in rendered
    assert "Science summary" in rendered
