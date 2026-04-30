from __future__ import annotations

from journal_pulse.models import DailyDigest
from journal_pulse.services.summarization import build_brief_summary_zh
from journal_pulse.storage.base import ObjectStore


def load_latest_digest(store: ObjectStore) -> DailyDigest | None:
    report_keys = store.list_keys('reports/')
    if not report_keys:
        return None
    payload = store.get_json(report_keys[-1])
    return DailyDigest.model_validate(payload)


def build_new_articles_digest(*, current_digest: DailyDigest, previous_digest: DailyDigest | None) -> DailyDigest:
    if previous_digest is None:
        return current_digest

    seen_keys = {article.dedup_key for article in previous_digest.articles}
    fresh_articles = [article for article in current_digest.articles if article.dedup_key not in seen_keys]
    return DailyDigest(generated_at=current_digest.generated_at, articles=fresh_articles)


def summarize_new_articles(delta_digest: DailyDigest) -> str:
    count = len(delta_digest.articles)
    if count == 0:
        return f'No new articles in this run at {delta_digest.generated_at.isoformat()}'
    top_titles = ', '.join(article.title for article in delta_digest.articles[:3])
    return f'{count} new articles detected at {delta_digest.generated_at.isoformat()}: {top_titles}'


def format_discord_broadcast(delta_digest: DailyDigest, *, summary_builder=build_brief_summary_zh) -> str:
    summary = summarize_new_articles(delta_digest)
    if not delta_digest.articles:
        return summary

    lines = [summary, '']
    for article in delta_digest.articles[:5]:
        lines.append(f'- {article.title}')
        lines.append(f'  中文摘要：{summary_builder(article)}')
    return '\n'.join(lines)
