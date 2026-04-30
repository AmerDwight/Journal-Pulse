from __future__ import annotations

from journal_pulse.models import ArticleRecord

_LOW_SIGNAL_AGGREGATOR_TYPES = {
    'book',
    'book-chapter',
    'book-part',
    'book-section',
    'book-set',
    'component',
    'dataset',
    'dissertation',
    'edited-book',
    'journal-issue',
    'journal-volume',
    'monograph',
    'peer-review',
    'posted-content',
    'proceedings',
    'proceedings-article',
    'reference-book',
    'reference-entry',
    'report',
    'report-series',
    'standard',
}

_PRIMARY_SOURCE_WEIGHTS = {
    'nature': 120,
    'science': 120,
    'cell': 120,
    'pnas': 120,
    'lancet': 120,
    'nejm': 120,
    'pubmed': 70,
    'crossref': 50,
}


def should_include_article(article: ArticleRecord) -> bool:
    content_type = article.metadata.get('content_type', '').strip().lower()
    if article.source in {'crossref', 'pubmed'} and content_type in _LOW_SIGNAL_AGGREGATOR_TYPES:
        return False
    return True


def article_quality_score(article: ArticleRecord) -> int:
    score = _PRIMARY_SOURCE_WEIGHTS.get(article.source, 80 if article.source_type == 'rss' else 60)

    if article.doi:
        score += 15
    if article.metadata.get('journal'):
        score += 10
    if article.summary:
        score += 10
    if article.abstract:
        score += 10

    content_type = article.metadata.get('content_type', '').strip().lower()
    if content_type == 'journal-article':
        score += 10

    return score


def filter_articles(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    return [article for article in articles if should_include_article(article)]
