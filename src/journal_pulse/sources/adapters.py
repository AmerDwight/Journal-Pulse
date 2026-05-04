from __future__ import annotations

from datetime import UTC, datetime
from re import sub
from time import struct_time
from typing import Any
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError

import httpx

from journal_pulse.models import ArticleRecord
from journal_pulse.sources.base import SourceDefinition, SourceRegistry

try:
    import feedparser  # type: ignore
except ModuleNotFoundError:
    class _FallbackFeedParser:
        @staticmethod
        def parse(url: str) -> dict[str, Any]:
            response = httpx.get(url, timeout=20.0)
            response.raise_for_status()
            root = ElementTree.fromstring(response.text)
            entries: list[dict[str, Any]] = []
            for item in root.findall('.//item'):
                entries.append(
                    {
                        'id': item.findtext('guid') or item.findtext('link') or item.findtext('title') or '',
                        'title': item.findtext('title') or '',
                        'link': item.findtext('link') or '',
                        'summary': item.findtext('description') or '',
                        'published': item.findtext('pubDate') or '',
                    }
                )
            return {'entries': entries}

    feedparser = _FallbackFeedParser()


class RSSFeedAdapter:
    def __init__(self, definition: SourceDefinition):
        self.definition = definition
        self.endpoint = definition.endpoint

    def fetch(self) -> list[ArticleRecord]:
        feed = feedparser.parse(self.endpoint)
        articles: list[ArticleRecord] = []
        for entry in feed.get('entries', []):
            url = entry.get('link', '')
            article_id = entry.get('id') or url or entry.get('title') or ''
            published_at = _coerce_datetime(entry.get('published_parsed') or entry.get('updated_parsed') or entry.get('published') or entry.get('updated'))
            articles.append(
                ArticleRecord(
                    source=self.definition.name,
                    source_type=self.definition.source_type,
                    article_id=str(article_id),
                    title=str(entry.get('title', '')),
                    url=str(url),
                    published_at=published_at,
                    summary=str(entry.get('summary', '')),
                )
            )
        return articles


class APIQueryAdapter:
    def __init__(self, definition: SourceDefinition, http_client: httpx.Client | None = None):
        self.definition = definition
        self.endpoint = definition.endpoint.rstrip('/')
        self.http_client = http_client or httpx.Client()

    def fetch(self) -> list[ArticleRecord]:
        if self.definition.name == 'pubmed':
            return self._fetch_pubmed()
        if self.definition.name == 'crossref':
            return self._fetch_crossref()
        return []

    def _fetch_pubmed(self) -> list[ArticleRecord]:
        search_params = {
            'db': 'pubmed',
            'retmode': 'json',
            'retmax': self.definition.metadata.get('retmax', 20),
            'sort': 'pub date',
            'term': _build_pubmed_term(self.definition.metadata.get('journal_whitelist', [])),
        }
        search_response = self.http_client.get(f'{self.endpoint}/esearch.fcgi', params=search_params, timeout=20.0)
        search_response.raise_for_status()
        search_payload = search_response.json()
        ids = search_payload.get('esearchresult', {}).get('idlist', [])
        if not ids:
            return []

        summary_params = {
            'db': 'pubmed',
            'retmode': 'json',
            'id': ','.join(ids),
        }
        response = self.http_client.get(f'{self.endpoint}/esummary.fcgi', params=summary_params, timeout=20.0)
        response.raise_for_status()
        payload = response.json()
        result = payload.get('result', {})
        abstracts = self._fetch_pubmed_abstracts(ids)

        articles: list[ArticleRecord] = []
        for uid in result.get('uids', []):
            record = result.get(uid, {})
            doi = _extract_pubmed_doi(record)
            url = f'https://pubmed.ncbi.nlm.nih.gov/{uid}/'
            articles.append(
                ArticleRecord(
                    source=self.definition.name,
                    source_type=self.definition.source_type,
                    article_id=str(record.get('uid', uid)),
                    title=str(record.get('title', '')),
                    url=url,
                    doi=doi,
                    published_at=_parse_pubmed_date(str(record.get('pubdate', ''))),
                    abstract=abstracts.get(str(uid), ''),
                    metadata={'journal': str(record.get('fulljournalname', ''))},
                )
            )
        return articles

    def _fetch_pubmed_abstracts(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        params = {
            'db': 'pubmed',
            'retmode': 'xml',
            'rettype': 'abstract',
            'id': ','.join(ids),
        }
        try:
            response = self.http_client.get(f'{self.endpoint}/efetch.fcgi', params=params, timeout=20.0)
            response.raise_for_status()
        except Exception:
            return {}
        xml_text = getattr(response, 'text', '')
        if not xml_text:
            return {}
        try:
            return _parse_pubmed_abstracts(xml_text)
        except ParseError:
            return {}

    def _fetch_crossref(self) -> list[ArticleRecord]:
        response = self.http_client.get(self.endpoint, params=_build_crossref_params(self.definition.metadata), timeout=20.0)
        response.raise_for_status()
        payload = response.json()
        items = payload.get('message', {}).get('items', [])

        articles: list[ArticleRecord] = []
        for item in items:
            doi = str(item.get('DOI', ''))
            url = str(item.get('URL') or (f'https://doi.org/{doi}' if doi else ''))
            articles.append(
                ArticleRecord(
                    source=self.definition.name,
                    source_type=self.definition.source_type,
                    article_id=doi or url,
                    title=_first_text(item.get('title')),
                    url=url,
                    doi=doi,
                    published_at=_fetch_crossref_date(item),
                    abstract=_strip_jats(str(item.get('abstract', ''))),
                    metadata={
                        'journal': _first_text(item.get('container-title')),
                        'publisher': str(item.get('publisher', '')),
                        'content_type': str(item.get('type', '')),
                    },
                )
            )
        return articles


def _coerce_datetime(value: struct_time | tuple[int, ...] | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, str):
        for fmt in ('%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return datetime.now(UTC)
    return datetime(*value[:6], tzinfo=UTC)


def _build_pubmed_term(journal_whitelist: list[str]) -> str:
    journal_terms = [f'{journal}[jour]' for journal in journal_whitelist]
    if journal_terms:
        return '(' + ' OR '.join(journal_terms) + ')'
    return 'all[sb]'


def _parse_pubmed_date(value: str) -> datetime:
    for fmt in ('%Y %b %d', '%Y %b', '%Y'):
        try:
            parsed = datetime.strptime(value, fmt)
            if fmt == '%Y':
                parsed = parsed.replace(month=1, day=1)
            elif fmt == '%Y %b':
                parsed = parsed.replace(day=1)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime(1970, 1, 1, tzinfo=UTC)


def _extract_pubmed_doi(record: dict[str, Any]) -> str:
    for article_id in record.get('articleids', []):
        if article_id.get('idtype') == 'doi':
            return str(article_id.get('value', ''))
    elocation = str(record.get('elocationid', ''))
    if elocation.lower().startswith('doi:'):
        return elocation.split(':', 1)[1].strip()
    return ''


def _parse_pubmed_abstracts(xml_text: str) -> dict[str, str]:
    root = ElementTree.fromstring(xml_text)
    abstracts: dict[str, str] = {}
    for article in root.findall('.//PubmedArticle'):
        pmid = (article.findtext('.//MedlineCitation/PMID') or '').strip()
        if not pmid:
            continue
        segments: list[str] = []
        for node in article.findall('.//Abstract/AbstractText'):
            text = ''.join(node.itertext()).strip()
            if not text:
                continue
            label = (node.attrib.get('Label') or '').strip()
            segments.append(f'{label}: {text}' if label else text)
        abstracts[pmid] = ' '.join(segments).strip()
    return abstracts


def _fetch_crossref_date(item: dict[str, Any]) -> datetime:
    for key in ('published-print', 'published-online', 'issued', 'created'):
        date_parts = item.get(key, {}).get('date-parts', [])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = parts[0]
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            return datetime(year, month, day, tzinfo=UTC)
    return datetime(1970, 1, 1, tzinfo=UTC)


def _strip_jats(text: str) -> str:
    return sub(r'<[^>]+>', '', text)


def _first_text(values: list[str] | None) -> str:
    if values:
        return str(values[0])
    return ''


def _build_crossref_params(metadata: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {'rows': metadata.get('rows', 20)}
    if metadata.get('query_container_title'):
        params['query.container-title'] = metadata['query_container_title']
    if metadata.get('filter'):
        params['filter'] = metadata['filter']
    return params


def register_builtin_source_types(registry: SourceRegistry) -> None:
    registry.register('rss', RSSFeedAdapter)
    registry.register('api', APIQueryAdapter)
