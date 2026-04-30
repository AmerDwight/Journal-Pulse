from typer.testing import CliRunner

from journal_pulse import cli


class DummyDigest:
    def __init__(self):
        self.articles = [object(), object()]


class DummyStore:
    def list_keys(self, prefix: str = '') -> list[str]:
        return []


runner = CliRunner()


def test_crawl_once_command_runs_ingest_flow(monkeypatch):
    monkeypatch.setattr(cli, 'build_default_sources', lambda: [])
    monkeypatch.setattr(cli, 'build_runtime_registry', lambda: object())
    monkeypatch.setattr(cli, 'build_runtime_store', lambda settings: DummyStore())
    monkeypatch.setattr(cli, 'crawl_sources_once', lambda **kwargs: DummyDigest())

    result = runner.invoke(cli.app, ['crawl-once'])

    assert result.exit_code == 0
    assert 'Ingested 2 deduplicated articles' in result.output


def test_monitor_once_command_reports_only_new_articles(monkeypatch):
    current_digest = type('Digest', (), {'articles': [object()], 'generated_at': None})()
    delta_digest = type('Digest', (), {'articles': [object(), object()]})()

    monkeypatch.setattr(cli, 'build_default_sources', lambda: [])
    monkeypatch.setattr(cli, 'build_runtime_registry', lambda: object())
    monkeypatch.setattr(cli, 'build_runtime_store', lambda settings: DummyStore())
    monkeypatch.setattr(cli, 'crawl_sources_once', lambda **kwargs: current_digest)
    monkeypatch.setattr(cli, 'load_latest_digest', lambda store: None)
    monkeypatch.setattr(cli, 'build_new_articles_digest', lambda current_digest, previous_digest: delta_digest)
    monkeypatch.setattr(cli, 'summarize_new_articles', lambda delta_digest: '2 new articles detected')

    result = runner.invoke(cli.app, ['monitor-once'])

    assert result.exit_code == 0
    assert '2 new articles detected' in result.output


def test_monitor_discord_once_command_sends_update_to_discord(monkeypatch):
    monkeypatch.setattr(cli, 'run_discord_monitor_cycle', lambda: 'Sent Discord update: 2 new articles detected')

    result = runner.invoke(cli.app, ['monitor-discord-once'])

    assert result.exit_code == 0
    assert 'Sent Discord update: 2 new articles detected' in result.output


def test_monitor_discord_once_command_reports_missing_config_cleanly(monkeypatch):
    def fake_run():
        raise RuntimeError('Discord bot token/channel id not configured')

    monkeypatch.setattr(cli, 'run_discord_monitor_cycle', fake_run)

    result = runner.invoke(cli.app, ['monitor-discord-once'])

    assert result.exit_code == 1
    assert 'Discord bot token/channel id not configured' in result.output
    assert 'Traceback' not in result.output


def test_run_discord_bot_command_starts_gateway_bot(monkeypatch):
    monkeypatch.setattr(cli, 'run_discord_gateway_bot', lambda: 'Discord gateway bot started')

    result = runner.invoke(cli.app, ['run-discord-bot'])

    assert result.exit_code == 0
    assert 'Discord gateway bot started' in result.output



def test_show_config_masks_sensitive_values(monkeypatch):
    settings_cls = cli.Settings
    monkeypatch.setattr(
        cli,
        'Settings',
        lambda: settings_cls.model_construct(
            discord_bot_token='super-secret-token',
            minio_secret_key='super-secret-minio-key',
            llm_api_key='super-secret-llm-key',
            discord_channel_id='1498974591845142650',
        ),
    )

    result = runner.invoke(cli.app, ['show-config'])

    assert result.exit_code == 0
    assert 'super-secret-token' not in result.output
    assert 'super-secret-minio-key' not in result.output
    assert 'super-secret-llm-key' not in result.output
    assert "'discord_bot_token': '***'" in result.output
    assert "'minio_secret_key': '***'" in result.output
    assert "'llm_api_key': '***'" in result.output
