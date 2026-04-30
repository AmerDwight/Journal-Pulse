from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import discord

from journal_pulse.config import Settings
from journal_pulse.services.llm import build_runtime_summarizer
from journal_pulse.services.query import find_article_by_title, format_article_detail, list_articles
from journal_pulse.services.summarization import build_brief_summary_zh, build_detail_summary_zh


MENTION_PATTERN_TEMPLATE = r'<@!?{bot_user_id}>'
DISCORD_MESSAGE_LIMIT = 1900
HISTORY_PROMPT = '想看哪段期間的論文？請直接回覆其中一個選項：1周 / 2周 / 1個月 / All Time'


@dataclass(frozen=True)
class HistoryRange:
    label: str
    since: datetime | None


def extract_title_query(content: str, *, bot_user_id: int) -> str:
    pattern = MENTION_PATTERN_TEMPLATE.format(bot_user_id=bot_user_id)
    return re.sub(pattern, '', content).strip()


def is_history_request(query: str) -> bool:
    normalized = query.strip().lower()
    return normalized in {'history', '歷史', '紀錄', '记录'}


def parse_history_range(choice: str, *, now: datetime | None = None) -> HistoryRange | None:
    now = now or datetime.now(timezone.utc)
    normalized = choice.strip().lower().replace(' ', '')
    aliases = {
        '1周': ('1周', timedelta(days=7)),
        '1週': ('1周', timedelta(days=7)),
        '7天': ('1周', timedelta(days=7)),
        '1week': ('1周', timedelta(days=7)),
        '2周': ('2周', timedelta(days=14)),
        '2週': ('2周', timedelta(days=14)),
        '14天': ('2周', timedelta(days=14)),
        '2weeks': ('2周', timedelta(days=14)),
        '1個月': ('1個月', timedelta(days=30)),
        '1个月': ('1個月', timedelta(days=30)),
        '1month': ('1個月', timedelta(days=30)),
        'alltime': ('All Time', None),
        'all': ('All Time', None),
        '全部': ('All Time', None),
    }
    match = aliases.get(normalized)
    if match is None:
        return None
    label, delta = match
    return HistoryRange(label=label, since=None if delta is None else now - delta)


def _split_message_chunks(lines: list[str], *, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for line in lines:
        line_length = len(line) + (1 if current else 0)
        if current and current_length + line_length > limit:
            chunks.append('\n'.join(current))
            current = [line]
            current_length = len(line)
            continue
        current.append(line)
        current_length += line_length
    if current:
        chunks.append('\n'.join(current))
    return chunks or ['目前沒有可顯示的內容。']


def build_history_reply_messages(*, store, choice: str, summary_builder, now: datetime | None = None) -> list[str]:
    parsed = parse_history_range(choice, now=now)
    if parsed is None:
        return ['我目前支援的 history 範圍是：1周 / 2周 / 1個月 / All Time。請直接回覆其中一個選項。']

    articles = list_articles(store=store, since=parsed.since)
    if not articles:
        scope = parsed.label if parsed.label == 'All Time' else f'最近 {parsed.label}'
        return [f'{scope} 內目前沒有已儲存的論文。']

    header = f'{parsed.label} 共 {len(articles)} 篇論文：' if parsed.label == 'All Time' else f'最近 {parsed.label} 內共 {len(articles)} 篇論文：'
    lines = [header, '']
    for article in articles:
        lines.append(f'- {article.published_at.date().isoformat()} | {article.title}')
        lines.append(f'  摘要：{summary_builder(article)}')
    return _split_message_chunks(lines)


def build_mention_reply(
    *,
    content: str,
    bot_user_id: int,
    store,
    find_article=find_article_by_title,
    format_detail=format_article_detail,
) -> str:
    title_query = extract_title_query(content, bot_user_id=bot_user_id)
    if not title_query:
        return '請在 @我之後貼上論文標題，我會回覆更完整的資訊。'
    if is_history_request(title_query):
        return HISTORY_PROMPT

    article = find_article(store=store, title_query=title_query)
    if article is None:
        return f'我暫時找不到標題接近「{title_query}」的論文。'

    summarizer = None
    try:
        summarizer = build_runtime_summarizer()
    except Exception:
        summarizer = None
    zh_summary = build_detail_summary_zh(article, summarizer=summarizer)
    try:
        return format_detail(article, zh_summary=zh_summary)
    except TypeError:
        return format_detail(article)


class JournalPulseDiscordGatewayBot(discord.Client):
    def __init__(self, *, settings: Settings, store_builder):
        intents = discord.Intents.default()
        intents.message_content = settings.discord_enable_message_content_intent
        super().__init__(intents=intents)
        self.settings = settings
        self.store_builder = store_builder
        self.pending_history_requests: set[tuple[int, int]] = set()

    async def on_ready(self):
        print(f'Discord gateway bot logged in as {self.user}')

    async def on_message(self, message):
        if self.user is None or message.author == self.user:
            return

        request_key = (message.channel.id, message.author.id)
        if request_key in self.pending_history_requests and not self.user.mentioned_in(message):
            store = self.store_builder(self.settings)
            summarizer = None
            try:
                summarizer = build_runtime_summarizer(self.settings)
            except Exception:
                summarizer = None
            replies = build_history_reply_messages(
                store=store,
                choice=message.content,
                summary_builder=lambda article: build_brief_summary_zh(article, summarizer=summarizer),
            )
            if parse_history_range(message.content) is not None:
                self.pending_history_requests.discard(request_key)
            for reply in replies:
                await message.reply(reply)
            return

        if not self.user.mentioned_in(message):
            return

        store = self.store_builder(self.settings)
        reply = build_mention_reply(
            content=message.content,
            bot_user_id=self.user.id,
            store=store,
        )
        if reply == HISTORY_PROMPT:
            self.pending_history_requests.add(request_key)
        await message.reply(reply)


def run_gateway_bot(*, settings: Settings, store_builder) -> str:
    if not settings.discord_bot_token:
        raise RuntimeError('Discord bot token not configured')
    bot = JournalPulseDiscordGatewayBot(settings=settings, store_builder=store_builder)
    asyncio.run(bot.start(settings.discord_bot_token))
    return 'Discord gateway bot started'
