from datetime import datetime, timezone

from journal_pulse.delivery.discord_gateway_bot import (
    build_history_reply_messages,
    build_mention_reply,
    extract_title_query,
    parse_history_range,
)
from journal_pulse.models import ArticleRecord
from journal_pulse.storage.memory import InMemoryObjectStore


class DummyStore:
    pass


BOT_USER_ID = 1498976139891445891
NOW = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)


def _article(*, article_id: str, title: str, published_at: datetime, summary: str = 'English summary') -> ArticleRecord:
    return ArticleRecord(
        source='nature',
        source_type='rss',
        article_id=article_id,
        title=title,
        url=f'https://example.com/{article_id}',
        published_at=published_at,
        summary=summary,
    )


def test_extract_title_query_removes_bot_mentions():
    query = extract_title_query('<@1498976139891445891> Protein folding benchmark', bot_user_id=BOT_USER_ID)

    assert query == 'Protein folding benchmark'


def test_build_mention_reply_returns_detailed_article_info_when_match_found():
    article = type('Article', (), {'title': 'Protein folding benchmark'})()

    reply = build_mention_reply(
        content='<@1498976139891445891> Protein folding benchmark',
        bot_user_id=BOT_USER_ID,
        store=DummyStore(),
        find_article=lambda store, title_query: article,
        format_detail=lambda article: '詳細資訊內容',
    )

    assert reply == '詳細資訊內容'


def test_build_mention_reply_guides_user_when_no_title_is_provided():
    reply = build_mention_reply(
        content='<@1498976139891445891>',
        bot_user_id=BOT_USER_ID,
        store=DummyStore(),
        find_article=lambda store, title_query: None,
        format_detail=lambda article: 'unused',
    )

    assert '請在 @我之後貼上論文標題' in reply


def test_build_mention_reply_prompts_for_history_range_when_history_is_requested():
    reply = build_mention_reply(
        content='<@1498976139891445891> history',
        bot_user_id=BOT_USER_ID,
        store=DummyStore(),
        find_article=lambda store, title_query: None,
        format_detail=lambda article: 'unused',
    )

    assert '想看哪段期間的論文' in reply
    assert '1周' in reply
    assert '2周' in reply
    assert '1個月' in reply
    assert 'All Time' in reply


def test_parse_history_range_understands_supported_labels():
    parsed = parse_history_range('2周', now=NOW)

    assert parsed is not None
    assert parsed.label == '2周'
    assert parsed.since == datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)


def test_build_history_reply_messages_filters_articles_by_selected_window_and_includes_summaries():
    store = InMemoryObjectStore()
    recent = _article(article_id='recent', title='Recent paper', published_at=datetime(2026, 4, 28, tzinfo=timezone.utc))
    old = _article(article_id='old', title='Old paper', published_at=datetime(2026, 4, 10, tzinfo=timezone.utc))
    store.put_json('articles/recent.json', recent.model_dump(mode='json'))
    store.put_json('articles/old.json', old.model_dump(mode='json'))

    messages = build_history_reply_messages(
        store=store,
        choice='1周',
        now=NOW,
        summary_builder=lambda article: f'摘要：{article.article_id}',
    )

    combined = '\n'.join(messages)
    assert '最近 1周 內共 1 篇論文' in combined
    assert 'Recent paper' in combined
    assert '摘要：recent' in combined
    assert 'Old paper' not in combined


def test_build_history_reply_messages_supports_all_time_listing():
    store = InMemoryObjectStore()
    older = _article(article_id='older', title='Older paper', published_at=datetime(2026, 3, 1, tzinfo=timezone.utc))
    newest = _article(article_id='newest', title='Newest paper', published_at=datetime(2026, 4, 29, tzinfo=timezone.utc))
    store.put_json('articles/older.json', older.model_dump(mode='json'))
    store.put_json('articles/newest.json', newest.model_dump(mode='json'))

    messages = build_history_reply_messages(
        store=store,
        choice='All Time',
        now=NOW,
        summary_builder=lambda article: article.title,
    )

    combined = '\n'.join(messages)
    assert 'All Time 共 2 篇論文' in combined
    assert combined.index('Newest paper') < combined.index('Older paper')


def test_build_history_reply_messages_reprompts_on_invalid_choice():
    messages = build_history_reply_messages(
        store=InMemoryObjectStore(),
        choice='3天',
        now=NOW,
        summary_builder=lambda article: 'unused',
    )

    assert len(messages) == 1
    assert '我目前支援' in messages[0]
    assert '1周 / 2周 / 1個月 / All Time' in messages[0]
