from datetime import datetime, timezone

from journal_pulse.models import ArticleRecord
from journal_pulse.services.summarization import build_brief_summary_zh, build_detail_summary_zh


class DummyTranslator:
    def __init__(self, translated_text: str):
        self.translated_text = translated_text
        self.calls = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        return self.translated_text


def test_build_brief_summary_zh_translates_summary_and_truncates_for_broadcast():
    article = ArticleRecord(
        source='nature',
        article_id='nature-1',
        title='Cancer discovery',
        url='https://example.com/nature-1',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        summary='This paper explains a new cancer treatment pathway in detail.',
    )
    translator = DummyTranslator('這篇論文說明一種新的癌症治療路徑，並展示初步成果與限制。')

    result = build_brief_summary_zh(article, translator=translator, max_length=22)

    assert result == '這篇論文說明一種新的癌症治療路徑，並展示初步…'
    assert translator.calls == ['This paper explains a new cancer treatment pathway in detail.']


def test_build_detail_summary_zh_uses_abstract_when_summary_missing():
    article = ArticleRecord(
        source='science',
        article_id='science-1',
        title='Protein folding update',
        url='https://example.com/science-1',
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        abstract='Researchers report a more efficient protein folding benchmark and discuss evaluation trade-offs.',
    )
    translator = DummyTranslator('研究團隊提出更有效率的蛋白質摺疊基準，並討論評估上的取捨。')

    result = build_detail_summary_zh(article, translator=translator)

    assert result == '研究團隊提出更有效率的蛋白質摺疊基準，並討論評估上的取捨。'
