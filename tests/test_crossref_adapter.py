from journal_pulse.sources.adapters import APIQueryAdapter
from journal_pulse.sources.base import SourceDefinition


class StubResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class StubHttpClient:
    def __init__(self, payloads: dict[str, dict]):
        self.payloads = payloads
        self.requested_urls: list[str] = []
        self.requested_params: list[dict] = []

    def get(self, url: str, params: dict | None = None, timeout: float | None = None) -> StubResponse:
        self.requested_urls.append(url)
        self.requested_params.append(params or {})
        return StubResponse(self.payloads[url])


def test_crossref_adapter_fetches_article_records_with_metadata():
    definition = SourceDefinition(
        name='crossref',
        source_type='api',
        endpoint='https://api.crossref.org/works',
        metadata={'query_container_title': 'Nature', 'rows': 2},
    )
    client = StubHttpClient(
        {
            'https://api.crossref.org/works': {
                'message': {
                    'items': [
                        {
                            'DOI': '10.1000/crossref-1',
                            'type': 'journal-article',
                            'title': ['Crossref paper'],
                            'URL': 'https://doi.org/10.1000/crossref-1',
                            'published-print': {'date-parts': [[2026, 4, 25]]},
                            'container-title': ['Nature'],
                            'publisher': 'Springer Nature',
                            'abstract': '<jats:p>Abstract text</jats:p>',
                        }
                    ]
                }
            }
        }
    )

    adapter = APIQueryAdapter(definition, http_client=client)
    articles = adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == 'crossref'
    assert articles[0].doi == '10.1000/crossref-1'
    assert articles[0].title == 'Crossref paper'
    assert articles[0].metadata['journal'] == 'Nature'
    assert articles[0].metadata['publisher'] == 'Springer Nature'
    assert articles[0].metadata['content_type'] == 'journal-article'
    assert articles[0].abstract == 'Abstract text'
    assert client.requested_params[0]['query.container-title'] == 'Nature'
    assert client.requested_params[0]['rows'] == 2
