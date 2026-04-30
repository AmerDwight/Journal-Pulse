from typer.testing import CliRunner

from journal_pulse import cli
from journal_pulse.models import ArticleRecord


runner = CliRunner()


class DummyStore:
    pass


def test_show_article_command_renders_article_details(monkeypatch):
    article = ArticleRecord.model_validate(
        {
            'source': 'crossref',
            'source_type': 'api',
            'article_id': '10.1000-crossref-1',
            'title': 'Crossref paper',
            'url': 'https://doi.org/10.1000/crossref-1',
            'doi': '10.1000/crossref-1',
            'published_at': '2026-04-25T00:00:00+00:00',
            'summary': 'summary',
            'abstract': 'abstract',
            'metadata': {'journal': 'Nature'},
        }
    )
    monkeypatch.setattr(cli, 'build_runtime_store', lambda settings: DummyStore())
    monkeypatch.setattr(cli, 'get_article_by_id', lambda store, article_id: article)

    result = runner.invoke(cli.app, ['show-article', 'doi-10.1000-crossref-1'])

    assert result.exit_code == 0
    assert 'Crossref paper' in result.output
    assert '10.1000/crossref-1' in result.output
    assert 'Nature' in result.output
