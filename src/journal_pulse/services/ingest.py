from __future__ import annotations

from datetime import datetime, timezone
from re import sub

from journal_pulse.models import DailyDigest
from journal_pulse.services.pipeline import build_digest
from journal_pulse.services.summarization import populate_cached_summaries
from journal_pulse.sources.base import SourceDefinition, SourceRegistry
from journal_pulse.storage.base import ObjectStore


def _article_storage_key(dedup_key: str) -> str:
    return 'articles/' + sub(r'[^a-zA-Z0-9.]+', '-', dedup_key.lower()).strip('-') + '.json'


def _report_storage_key(generated_at: datetime) -> str:
    return f"reports/daily-digest-{generated_at.date().isoformat()}.json"


def crawl_sources_once(
    *,
    sources: list[SourceDefinition],
    registry: SourceRegistry,
    store: ObjectStore,
    summarizer=None,
    generated_at: datetime | None = None,
) -> DailyDigest:
    generated_at = generated_at or datetime.now(timezone.utc)

    articles = []
    for source in sources:
        if not source.enabled:
            continue
        adapter = registry.build(source)
        articles.extend(adapter.fetch())

    digest = build_digest(articles, generated_at=generated_at)
    enriched_articles = [populate_cached_summaries(article, summarizer=summarizer) for article in digest.articles]
    digest = digest.model_copy(update={'articles': enriched_articles})

    for article in digest.articles:
        store.put_json(_article_storage_key(article.dedup_key), article.model_dump(mode='json'))

    store.put_json(_report_storage_key(digest.generated_at), digest.model_dump(mode='json'))
    return digest
