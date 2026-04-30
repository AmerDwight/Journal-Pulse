from datetime import datetime, timezone

from journal_pulse.sources.adapters import APIQueryAdapter, RSSFeedAdapter
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


def test_rss_feed_adapter_fetches_article_records_from_feed(monkeypatch):
    definition = SourceDefinition(name="nature", source_type="rss", endpoint="https://example.com/feed.xml")
    adapter = RSSFeedAdapter(definition)

    monkeypatch.setattr(
        "journal_pulse.sources.adapters.feedparser.parse",
        lambda url: {
            "entries": [
                {
                    "id": "nature-1",
                    "title": "A discovery",
                    "link": "https://example.com/articles/1?utm_source=rss",
                    "summary": "Feed summary",
                    "published_parsed": (2026, 4, 25, 12, 30, 0, 0, 0, 0),
                }
            ]
        },
    )

    articles = adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == "nature"
    assert articles[0].source_type == "rss"
    assert articles[0].article_id == "nature-1"
    assert articles[0].title == "A discovery"
    assert articles[0].summary == "Feed summary"
    assert articles[0].published_at == datetime(2026, 4, 25, 12, 30, tzinfo=timezone.utc)


def test_pubmed_adapter_fetches_article_records_from_esearch_and_esummary_payloads():
    definition = SourceDefinition(
        name="pubmed",
        source_type="api",
        endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        metadata={"journal_whitelist": ["Nature", "Science"], "retmax": 5},
    )
    client = StubHttpClient(
        {
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi": {
                "esearchresult": {"idlist": ["12345"]}
            },
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi": {
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "PubMed paper",
                        "pubdate": "2026 Apr 25",
                        "articleids": [{"idtype": "doi", "value": "10.1000/pubmed-12345"}],
                        "elocationid": "doi: 10.1000/pubmed-12345",
                        "fulljournalname": "Nature",
                    },
                }
            },
        }
    )
    adapter = APIQueryAdapter(definition, http_client=client)

    articles = adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == "pubmed"
    assert articles[0].source_type == "api"
    assert articles[0].article_id == "12345"
    assert articles[0].doi == "10.1000/pubmed-12345"
    assert articles[0].title == "PubMed paper"
    assert articles[0].metadata["journal"] == "Nature"
    assert client.requested_urls == [
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
    ]
    assert client.requested_params[0]["db"] == "pubmed"
    assert 'Nature[jour]' in client.requested_params[0]["term"]
    assert client.requested_params[1]["id"] == "12345"
