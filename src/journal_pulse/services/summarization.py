from __future__ import annotations

from html import unescape
from re import IGNORECASE, search, sub

from journal_pulse.models import ArticleRecord


_BLOCK_ENDINGS_PATTERN = r'</(?:p|div|section|article|li|ul|ol|br|h[1-6])\s*>'
_METADATA_PATTERN = r'(published online:|doi:\s*10\.|^nature,\s|^science,\s|^cell,\s|^pnas,\s)'


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
    return (summary or abstract or title).strip()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '…'


def build_detail_summary_zh(article: ArticleRecord, *, summarizer=None, max_chars: int = 160) -> str:
    source_text = _source_text(article)
    if summarizer is not None:
        try:
            summarized = summarizer.summarize(title=article.title, source_text=source_text, max_chars=max_chars)
            if summarized:
                return summarized.strip()
        except Exception:
            pass
    return f'中文摘要待補：{_truncate(source_text, 120)}'


def build_brief_summary_zh(article: ArticleRecord, *, summarizer=None, max_length: int = 80) -> str:
    detail_summary = build_detail_summary_zh(article, summarizer=summarizer)
    if detail_summary.startswith('中文摘要待補：'):
        detail_summary = detail_summary.removeprefix('中文摘要待補：').strip()
    return _truncate(detail_summary, max_length)
