from journal_pulse.delivery.discord_gateway_bot import build_mention_reply, extract_title_query


class DummyStore:
    pass


def test_extract_title_query_removes_bot_mentions():
    query = extract_title_query('<@1498976139891445891> Protein folding benchmark', bot_user_id=1498976139891445891)

    assert query == 'Protein folding benchmark'


def test_build_mention_reply_returns_detailed_article_info_when_match_found():
    article = type('Article', (), {'title': 'Protein folding benchmark'})()

    reply = build_mention_reply(
        content='<@1498976139891445891> Protein folding benchmark',
        bot_user_id=1498976139891445891,
        store=DummyStore(),
        find_article=lambda store, title_query: article,
        format_detail=lambda article: '詳細資訊內容',
    )

    assert reply == '詳細資訊內容'


def test_build_mention_reply_guides_user_when_no_title_is_provided():
    reply = build_mention_reply(
        content='<@1498976139891445891>',
        bot_user_id=1498976139891445891,
        store=DummyStore(),
        find_article=lambda store, title_query: None,
        format_detail=lambda article: 'unused',
    )

    assert '請在 @我之後貼上論文標題' in reply
