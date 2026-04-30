from __future__ import annotations

import asyncio
import re

import discord

from journal_pulse.config import Settings
from journal_pulse.services.query import find_article_by_title, format_article_detail
from journal_pulse.services.summarization import build_detail_summary_zh, build_runtime_translator


MENTION_PATTERN_TEMPLATE = r'<@!?{bot_user_id}>'


def extract_title_query(content: str, *, bot_user_id: int) -> str:
    pattern = MENTION_PATTERN_TEMPLATE.format(bot_user_id=bot_user_id)
    return re.sub(pattern, '', content).strip()


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

    article = find_article(store=store, title_query=title_query)
    if article is None:
        return f'我暫時找不到標題接近「{title_query}」的論文。'

    translator = None
    try:
        translator = build_runtime_translator()
    except Exception:
        translator = None
    zh_summary = build_detail_summary_zh(article, translator=translator)
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

    async def on_ready(self):
        print(f'Discord gateway bot logged in as {self.user}')

    async def on_message(self, message):
        if self.user is None or message.author == self.user:
            return
        if not self.user.mentioned_in(message):
            return

        store = self.store_builder(self.settings)
        reply = build_mention_reply(
            content=message.content,
            bot_user_id=self.user.id,
            store=store,
        )
        await message.reply(reply)


def run_gateway_bot(*, settings: Settings, store_builder) -> str:
    if not settings.discord_bot_token:
        raise RuntimeError('Discord bot token not configured')
    bot = JournalPulseDiscordGatewayBot(settings=settings, store_builder=store_builder)
    asyncio.run(bot.start(settings.discord_bot_token))
    return 'Discord gateway bot started'
