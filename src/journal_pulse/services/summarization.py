from __future__ import annotations

from journal_pulse.models import ArticleRecord


def _source_text(article: ArticleRecord) -> str:
    summary = getattr(article, 'summary', '')
    abstract = getattr(article, 'abstract', '')
    title = getattr(article, 'title', '')
    return (summary or abstract or title).strip()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '…'


def build_detail_summary_zh(article: ArticleRecord, *, translator=None) -> str:
    source_text = _source_text(article)
    if translator is not None:
        try:
            translated = translator.translate(source_text)
            if translated:
                return translated.strip()
        except Exception:
            pass
    return f'中文摘要待補：{_truncate(source_text, 120)}'


def build_brief_summary_zh(article: ArticleRecord, *, translator=None, max_length: int = 80) -> str:
    detail_summary = build_detail_summary_zh(article, translator=translator)
    if detail_summary.startswith('中文摘要待補：'):
        detail_summary = detail_summary.removeprefix('中文摘要待補：').strip()
    return _truncate(detail_summary, max_length)


def build_runtime_translator():
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source='auto', target='zh-TW')
