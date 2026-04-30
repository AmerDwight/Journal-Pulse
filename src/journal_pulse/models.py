from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    filtered_query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.startswith('utm_')]
    normalized_path = parts.path[:-1] if parts.path.endswith('/') and parts.path != '/' else parts.path
    normalized_query = urlencode(filtered_query)
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, normalized_query, ''))


class ArticleRecord(BaseModel):
    source: str
    article_id: str
    title: str
    url: str
    published_at: datetime
    source_type: str = 'rss'
    doi: str = ''
    summary: str = ''
    abstract: str = ''
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        if self.doi:
            return f'doi:{self.doi.lower()}'
        return f'url:{_normalize_url(self.url)}'


class DailyDigest(BaseModel):
    generated_at: datetime
    articles: list[ArticleRecord]
