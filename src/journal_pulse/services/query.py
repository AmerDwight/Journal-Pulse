from __future__ import annotations

from difflib import SequenceMatcher

from journal_pulse.models import ArticleRecord
from journal_pulse.storage.base import ObjectStore


def get_article_by_id(*, store: ObjectStore, article_id: str) -> ArticleRecord:
    payload = store.get_json(f'articles/{article_id}.json')
    return ArticleRecord.model_validate(payload)


def find_article_by_title(*, store: ObjectStore, title_query: str) -> ArticleRecord | None:
    normalized_query = title_query.strip().lower()
    if not normalized_query:
        return None

    best_match: ArticleRecord | None = None
    best_score = 0.0
    for key in store.list_keys('articles/'):
        article = ArticleRecord.model_validate(store.get_json(key))
        title = article.title.lower()
        if normalized_query in title:
            score = len(normalized_query) / max(len(title), 1)
        else:
            score = SequenceMatcher(a=normalized_query, b=title).ratio()
        if score > best_score:
            best_score = score
            best_match = article

    if best_score < 0.25:
        return None
    return best_match


def format_article_detail(article: ArticleRecord, *, zh_summary: str) -> str:
    journal = article.metadata.get('journal', 'Unknown')
    lines = [
        f'標題：{article.title}',
        f'來源：{article.source}',
        f'期刊：{journal}',
        f'發表時間：{article.published_at.isoformat()}',
        f'中文摘要：{zh_summary}',
        f'DOI：{article.doi or "N/A"}',
        f'URL：{article.url}',
    ]
    if article.abstract:
        lines.append(f'Abstract：{article.abstract}')
    elif article.summary:
        lines.append(f'Summary：{article.summary}')
    return '\n'.join(lines)
