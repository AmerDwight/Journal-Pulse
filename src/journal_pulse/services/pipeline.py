from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord, DailyDigest
from journal_pulse.services.quality import article_quality_score, filter_articles


def _select_preferred_article(current: ArticleRecord, candidate: ArticleRecord) -> ArticleRecord:
    if candidate.published_at >= current.published_at:
        return candidate
    return current


def build_digest(articles: list[ArticleRecord], generated_at: datetime | None = None) -> DailyDigest:
    generated_at = generated_at or datetime.now(timezone.utc)

    deduplicated: dict[str, ArticleRecord] = {}
    for article in filter_articles(articles):
        existing = deduplicated.get(article.dedup_key)
        if existing is None:
            deduplicated[article.dedup_key] = article
            continue
        deduplicated[article.dedup_key] = _select_preferred_article(existing, article)

    ordered = sorted(
        deduplicated.values(),
        key=lambda article: (article_quality_score(article), article.published_at),
        reverse=True,
    )
    return DailyDigest(generated_at=generated_at, articles=ordered)
