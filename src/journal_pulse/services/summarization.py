from __future__ import annotations

from html import unescape
from re import IGNORECASE, search, sub

from journal_pulse.models import ArticleRecord


_BLOCK_ENDINGS_PATTERN = r'</(?:p|div|section|article|li|ul|ol|br|h[1-6])\s*>'
_METADATA_PATTERN = r'(published online:|doi:\s*10\.|^nature,\s|^science,\s|^cell,\s|^pnas,\s)'
_DETAIL_MAX_CHARS = 160


def clean_summary_text(text: str) -> str:
    if not text:
        return ''

    normalized = sub(_BLOCK_ENDINGS_PATTERN, '\n', text, flags=IGNORECASE)
    normalized = sub(r'<[^>]+>', ' ', normalized)
    normalized = unescape(normalized)
    blocks = [sub(r'\s+', ' ', block).strip() for block in normalized.splitlines()]
    blocks = [block for block in blocks if block]
    if not blocks:
        return ''

    content_blocks = [block for block in blocks if not _looks_like_metadata(block)]
    candidate_blocks = content_blocks or blocks
    return ' '.join(candidate_blocks).strip()


def _looks_like_metadata(block: str) -> bool:
    return bool(block and search(_METADATA_PATTERN, block, flags=IGNORECASE))


def _source_text(article: ArticleRecord) -> str:
    summary = clean_summary_text(getattr(article, 'summary', ''))
    abstract = clean_summary_text(getattr(article, 'abstract', ''))
    title = clean_summary_text(getattr(article, 'title', ''))
    if summary and title and summary == title:
        return abstract or ''
    return (summary or abstract or title).strip()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '…'


def _summarize_to_zh(*, article: ArticleRecord, summarizer, max_chars: int = _DETAIL_MAX_CHARS) -> str:
    if summarizer is None:
        return ''
    source_text = _source_text(article)
    if not source_text:
        return ''
    try:
        summarized = summarizer.summarize(title=article.title, source_text=source_text, max_chars=max_chars)
    except Exception:
        return ''
    return summarized.strip() if summarized else ''


def populate_cached_summaries(article: ArticleRecord, *, summarizer=None, brief_max_length: int = 80) -> ArticleRecord:
    cached_detail = getattr(article, 'summary_zh', '').strip()
    cached_brief = getattr(article, 'brief_summary_zh', '').strip()
    if cached_detail and cached_brief:
        return article

    detail_summary = cached_detail or _summarize_to_zh(article=article, summarizer=summarizer)
    if not detail_summary:
        return article

    brief_summary = cached_brief or _truncate(detail_summary, brief_max_length)
    return article.model_copy(update={'summary_zh': detail_summary, 'brief_summary_zh': brief_summary})


def build_detail_summary_zh(article: ArticleRecord, *, summarizer=None, max_chars: int = _DETAIL_MAX_CHARS) -> str:
    cached = getattr(article, 'summary_zh', '').strip()
    if cached:
        return cached

    summarized = _summarize_to_zh(article=article, summarizer=summarizer, max_chars=max_chars)
    if summarized:
        return summarized

    source_text = _source_text(article) or clean_summary_text(getattr(article, 'title', ''))
    return f'中文摘要待補：{_truncate(source_text, 120)}'


def build_brief_summary_zh(article: ArticleRecord, *, summarizer=None, max_length: int = 80) -> str:
    cached_brief = getattr(article, 'brief_summary_zh', '').strip()
    if cached_brief:
        return _truncate(cached_brief, max_length)

    cached_detail = getattr(article, 'summary_zh', '').strip()
    if cached_detail:
        return _truncate(cached_detail, max_length)

    detail_summary = build_detail_summary_zh(article, summarizer=summarizer)
    if detail_summary.startswith('中文摘要待補：'):
        detail_summary = detail_summary.removeprefix('中文摘要待補：').strip()
    return _truncate(detail_summary, max_length)
