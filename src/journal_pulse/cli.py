from datetime import datetime, timezone
from pprint import pformat

import typer

from journal_pulse.config import Settings
from journal_pulse.delivery.discord_bot import DiscordBotNotifier
from journal_pulse.delivery.discord_gateway_bot import run_gateway_bot
from journal_pulse.models import ArticleRecord
from journal_pulse.reporting.markdown import MarkdownReporter
from journal_pulse.scheduler import build_scheduler
from journal_pulse.services.ingest import crawl_sources_once
from journal_pulse.services.llm import build_runtime_summarizer
from journal_pulse.services.monitoring import (
    build_new_articles_digest,
    format_discord_broadcast,
    load_latest_digest,
    summarize_new_articles,
)
from journal_pulse.services.pipeline import build_digest
from journal_pulse.services.query import get_article_by_id
from journal_pulse.services.summarization import build_brief_summary_zh
from journal_pulse.sources.adapters import register_builtin_source_types
from journal_pulse.sources.base import SourceRegistry
from journal_pulse.sources.defaults import build_default_sources
from journal_pulse.storage.local_store import LocalObjectStore

app = typer.Typer(help='Journal Pulse CLI')

_SENSITIVE_SETTING_KEYS = {
    'discord_bot_token',
    'minio_secret_key',
    'minio_access_key',
    'llm_api_key',
}


def _masked_settings_dump(settings: Settings) -> dict:
    payload = settings.model_dump()
    for key in _SENSITIVE_SETTING_KEYS:
        if payload.get(key):
            payload[key] = '***'
    return payload


def build_runtime_registry() -> SourceRegistry:
    registry = SourceRegistry()
    register_builtin_source_types(registry)
    return registry


def build_runtime_store(settings: Settings):
    try:
        from journal_pulse.storage.minio_store import MinIOStore
    except ModuleNotFoundError:
        return LocalObjectStore(settings.data_root)
    try:
        store = MinIOStore(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket_name=settings.raw_bucket,
            secure=settings.minio_secure,
        )
        if hasattr(store, 'ensure_bucket'):
            store.ensure_bucket()
        return store
    except Exception:
        return LocalObjectStore(settings.data_root)


@app.command('show-config')
def show_config() -> None:
    settings = Settings()
    typer.echo(pformat(_masked_settings_dump(settings)))


@app.command('generate-report')
def generate_report() -> None:
    digest = build_digest(
        [
            ArticleRecord(
                source='nature',
                article_id='demo-1',
                title='Bootstrap article',
                url='https://example.com/bootstrap',
                published_at=datetime.now(timezone.utc),
                summary='This is a placeholder summary for the bootstrap report.',
                abstract='Placeholder abstract',
            )
        ]
    )
    typer.echo(MarkdownReporter().render(digest))


def build_monitor_delta(*, settings: Settings | None = None):
    settings = settings or Settings()
    store = build_runtime_store(settings)
    previous_digest = load_latest_digest(store)
    summarizer = None
    try:
        summarizer = build_runtime_summarizer(settings)
    except Exception:
        summarizer = None
    current_digest = crawl_sources_once(
        sources=build_default_sources(),
        registry=build_runtime_registry(),
        store=store,
        summarizer=summarizer,
    )
    return build_new_articles_digest(current_digest=current_digest, previous_digest=previous_digest)


def run_monitor_cycle(*, settings: Settings | None = None) -> str:
    delta_digest = build_monitor_delta(settings=settings)
    return summarize_new_articles(delta_digest)


def run_discord_monitor_cycle(*, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    if not settings.discord_bot_token or not settings.discord_channel_id:
        raise RuntimeError('Discord bot token/channel id not configured')

    delta_digest = build_monitor_delta(settings=settings)
    summarizer = None
    try:
        summarizer = build_runtime_summarizer(settings)
    except Exception:
        summarizer = None
    message = format_discord_broadcast(
        delta_digest,
        summary_builder=lambda article: build_brief_summary_zh(article, summarizer=summarizer),
    )
    notifier = DiscordBotNotifier(
        bot_token=settings.discord_bot_token,
        channel_id=settings.discord_channel_id,
    )
    notifier.send_message(message)
    return f'Sent Discord update: {summarize_new_articles(delta_digest)}'


def run_discord_gateway_bot(*, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    return run_gateway_bot(settings=settings, store_builder=build_runtime_store)


@app.command('crawl-once')
def crawl_once() -> None:
    settings = Settings()
    summarizer = None
    try:
        summarizer = build_runtime_summarizer(settings)
    except Exception:
        summarizer = None
    digest = crawl_sources_once(
        sources=build_default_sources(),
        registry=build_runtime_registry(),
        store=build_runtime_store(settings),
        summarizer=summarizer,
    )
    typer.echo(f'Ingested {len(digest.articles)} deduplicated articles')


@app.command('monitor-once')
def monitor_once() -> None:
    typer.echo(run_monitor_cycle())


@app.command('monitor-discord-once')
def monitor_discord_once() -> None:
    try:
        typer.echo(run_discord_monitor_cycle())
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command('run-discord-bot')
def run_discord_bot() -> None:
    typer.echo(run_discord_gateway_bot())


@app.command('run-scheduler')
def run_scheduler() -> None:
    settings = Settings()
    job = run_discord_monitor_cycle if settings.discord_bot_token and settings.discord_channel_id else run_monitor_cycle
    scheduler = build_scheduler(settings, job=job)
    typer.echo('Scheduler started')
    scheduler.start()


@app.command('show-article')
def show_article(article_id: str) -> None:
    settings = Settings()
    article = get_article_by_id(store=build_runtime_store(settings), article_id=article_id)
    typer.echo(pformat(article.model_dump(mode='json')))


if __name__ == '__main__':
    app()
