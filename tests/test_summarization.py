from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.summarization import build_brief_summary_zh, build_detail_summary_zh


class DummySummarizer:
    def __init__(self, summarized_text: str):
        self.summarized_text = summarized_text
        self.calls = []

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str:
        self.calls.append({'title': title, 'source_text': source_text, 'max_chars': max_chars})
        return self.summarized_text


def test_build_brief_summary_zh_summarizes_clean_text_and_truncates_for_broadcast():
    article = ArticleRecord(
        source='nature',
        article_id='nature-1',
        title='Cancer discovery',
        url='https://example.com/nature-1',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='This paper explains a new cancer treatment pathway in detail.',
    )
    summarizer = DummySummarizer('這篇論文說明一種新的癌症治療路徑，並展示初步成果與限制。')

    result = build_brief_summary_zh(article, summarizer=summarizer, max_length=22)

    assert result == '這篇論文說明一種新的癌症治療路徑，並展示初步…'
    assert summarizer.calls == [
        {
            'title': 'Cancer discovery',
            'source_text': 'This paper explains a new cancer treatment pathway in detail.',
            'max_chars': 160,
        }
    ]


def test_build_detail_summary_zh_prefers_cached_summary_without_calling_summarizer():
    article = ArticleRecord(
        source='nature',
        article_id='nature-cached',
        title='Cached summary paper',
        url='https://example.com/nature-cached',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='English summary that should not be used.',
        summary_zh='已快取的中文摘要。',
        brief_summary_zh='快取短摘要。',
    )
    summarizer = DummySummarizer('不應被呼叫')

    detail = build_detail_summary_zh(article, summarizer=summarizer)
    brief = build_brief_summary_zh(article, summarizer=summarizer)

    assert detail == '已快取的中文摘要。'
    assert brief == '快取短摘要。'
    assert summarizer.calls == []


def test_build_detail_summary_zh_uses_abstract_when_summary_missing():
    article = ArticleRecord(
        source='science',
        article_id='science-1',
        title='Protein folding update',
        url='https://example.com/science-1',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        abstract='Researchers report a more efficient protein folding benchmark and discuss evaluation trade-offs.',
    )
    summarizer = DummySummarizer('研究團隊提出更有效率的蛋白質摺疊基準，並討論評估上的取捨。')

    result = build_detail_summary_zh(article, summarizer=summarizer)

    assert result == '研究團隊提出更有效率的蛋白質摺疊基準，並討論評估上的取捨。'


def test_build_detail_summary_zh_strips_html_and_metadata_before_summarization():
    article = ArticleRecord(
        source='nature',
        article_id='nature-2',
        title='Policy update',
        url='https://example.com/nature-2',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='''<p>Nature, Published online: 28 April 2026; <a href="https://www.nature.com/articles/d41586-026-01301-5">doi:10.1038/d41586-026-01301-5</a></p><p>A Nature analysis shows that the Trump administration has terminated more than 100 advisory committees to science agencies — and reduced the transparency and independence of those that remain.</p>''',
    )
    summarizer = DummySummarizer('川普政府已終止逾百個科學諮詢委員會。')

    result = build_detail_summary_zh(article, summarizer=summarizer)

    assert result == '川普政府已終止逾百個科學諮詢委員會。'
    assert summarizer.calls == [
        {
            'title': 'Policy update',
            'source_text': 'A Nature analysis shows that the Trump administration has terminated more than 100 advisory committees to science agencies — and reduced the transparency and independence of those that remain.',
            'max_chars': 160,
        }
    ]


def test_build_detail_summary_zh_fallback_text_is_clean_when_summarizer_missing():
    article = ArticleRecord(
        source='nature',
        article_id='nature-3',
        title='Octopus brains',
        url='https://example.com/nature-3',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='<p>Nature, Published online: 29 April 2026; <a href="https://www.nature.com/articles/d41586-026-01234-5">doi:10.1038/d41586-026-01234-5</a></p><p>Do octopus brains work like humans — or is there another way to be smart?</p>',
    )

    result = build_detail_summary_zh(article, summarizer=None)

    assert result == '中文摘要待補：Do octopus brains work like humans — or is there another way to be smart?'



def test_build_detail_summary_zh_does_not_treat_title_only_feed_text_as_real_summary():
    article = ArticleRecord(
        source='nature',
        article_id='nature-title-only',
        title='The equity paradox of environmental DNA for biodiversity monitoring',
        url='https://example.com/nature-title-only',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='''<p>Nature, Published online: 28 April 2026; <a href="https://www.nature.com/articles/d41586-026-01349-3">doi:10.1038/d41586-026-01349-3</a></p>The equity paradox of environmental DNA for biodiversity monitoring''',
    )
    summarizer = DummySummarizer('不應被呼叫')

    result = build_detail_summary_zh(article, summarizer=summarizer)

    assert result == '中文摘要待補：The equity paradox of environmental DNA for biodiversity monitoring'
    assert summarizer.calls == []


def test_build_detail_summary_zh_prefers_abstract_when_summary_collapses_to_title():
    article = ArticleRecord(
        source='nature',
        article_id='nature-title-plus-abstract',
        title='The equity paradox of environmental DNA for biodiversity monitoring',
        url='https://example.com/nature-title-plus-abstract',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='''<p>Nature, Published online: 28 April 2026; <a href="https://www.nature.com/articles/d41586-026-01349-3">doi:10.1038/d41586-026-01349-3</a></p>The equity paradox of environmental DNA for biodiversity monitoring''',
        abstract='Researchers examine how environmental DNA monitoring can widen biodiversity coverage while still amplifying resource inequities across regions.',
    )
    summarizer = DummySummarizer('應優先使用 abstract')

    result = build_detail_summary_zh(article, summarizer=summarizer)

    assert result == '應優先使用 abstract'
    assert summarizer.calls == [
        {
            'title': 'The equity paradox of environmental DNA for biodiversity monitoring',
            'source_text': 'Researchers examine how environmental DNA monitoring can widen biodiversity coverage while still amplifying resource inequities across regions.',
            'max_chars': 160,
        }
    ]
