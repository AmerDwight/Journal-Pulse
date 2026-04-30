from typer.testing import CliRunner

from journal_pulse import cli


runner = CliRunner()


class DummyScheduler:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True


def test_run_scheduler_command_builds_and_starts_scheduler(monkeypatch):
    scheduler = DummyScheduler()
    recorded = {}
    settings_cls = cli.Settings

    def fake_build_scheduler(settings, job):
        recorded['job'] = job
        return scheduler

    monkeypatch.setattr(cli, 'Settings', lambda: settings_cls.model_construct(discord_bot_token='', discord_channel_id=''))
    monkeypatch.setattr(cli, 'build_scheduler', fake_build_scheduler)

    result = runner.invoke(cli.app, ['run-scheduler'])

    assert result.exit_code == 0
    assert scheduler.started is True
    assert recorded['job'] is cli.run_monitor_cycle
    assert 'Scheduler started' in result.output


def test_run_scheduler_uses_discord_delivery_job_when_bot_configured(monkeypatch):
    scheduler = DummyScheduler()
    recorded = {}
    settings_cls = cli.Settings

    def fake_build_scheduler(settings, job):
        recorded['job'] = job
        return scheduler

    monkeypatch.setattr(cli, 'Settings', lambda: settings_cls.model_construct(discord_bot_token='bot-token', discord_channel_id='12345'))
    monkeypatch.setattr(cli, 'build_scheduler', fake_build_scheduler)

    result = runner.invoke(cli.app, ['run-scheduler'])

    assert result.exit_code == 0
    assert scheduler.started is True
    assert recorded['job'] is cli.run_discord_monitor_cycle
