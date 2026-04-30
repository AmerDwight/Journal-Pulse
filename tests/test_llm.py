from journal_pulse.config import Settings
from journal_pulse.services.llm import (
    AgentAllocator,
    FailoverSummaryBackend,
    OpenRouterSummaryAgent,
    build_runtime_summarizer,
)


class DummyResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class DummyHttpClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def post(self, url: str, *, headers: dict, json: dict, timeout: float):
        self.calls.append(
            {
                'url': url,
                'headers': headers,
                'json': json,
                'timeout': timeout,
            }
        )
        return DummyResponse(self.payload)


class FakeAgent:
    def __init__(self, provider_name: str, result: str | None = None, error: Exception | None = None):
        self.provider_name = provider_name
        self.result = result
        self.error = error
        self.calls = []

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str:
        self.calls.append({'title': title, 'source_text': source_text, 'max_chars': max_chars})
        if self.error is not None:
            raise self.error
        return self.result or ''


class FakeAllocator:
    def __init__(self, agents: list[FakeAgent]):
        self.agents = agents
        self.calls = []

    def allocate(self, *, excluded_providers: tuple[str, ...] = ()):
        self.calls.append(excluded_providers)
        for agent in self.agents:
            if agent.provider_name not in excluded_providers:
                return agent
        raise RuntimeError('No summary agents available')


def test_build_runtime_summarizer_returns_none_when_backend_disabled():
    settings = Settings(llm_backend='none')

    backend = build_runtime_summarizer(settings)

    assert backend is None


def test_build_runtime_summarizer_allocates_openrouter_provider_by_default():
    settings = Settings(llm_api_key='secret-key')

    backend = build_runtime_summarizer(settings)

    assert isinstance(backend, FailoverSummaryBackend)
    assert backend.active_provider == 'openrouter'


def test_build_runtime_summarizer_requires_api_key_for_openrouter_backend():
    settings = Settings(llm_backend='openrouter', llm_api_key='')

    try:
        build_runtime_summarizer(settings)
    except ValueError as exc:
        assert str(exc) == 'LLM_API_KEY is required for provider: openrouter'
    else:
        raise AssertionError('expected ValueError for missing OpenRouter API key')


def test_failover_summary_backend_reallocates_when_current_agent_raises():
    failing_agent = FakeAgent('openrouter', error=RuntimeError('provider timeout'))
    fallback_agent = FakeAgent('backup-provider', result='精簡繁中摘要。')
    allocator = FakeAllocator([failing_agent, fallback_agent])
    backend = FailoverSummaryBackend(allocator=allocator, agent=failing_agent)

    result = backend.summarize(
        title='Example paper',
        source_text='Original abstract text.',
        max_chars=80,
    )

    assert result == '精簡繁中摘要。'
    assert backend.active_provider == 'backup-provider'
    assert allocator.calls == [('openrouter',)]
    assert fallback_agent.calls == [
        {
            'title': 'Example paper',
            'source_text': 'Original abstract text.',
            'max_chars': 80,
        }
    ]


def test_agent_allocator_raises_when_no_provider_can_be_allocated():
    allocator = AgentAllocator(agent_factories={})

    try:
        allocator.allocate()
    except RuntimeError as exc:
        assert str(exc) == 'No summary agents available'
    else:
        raise AssertionError('expected RuntimeError when no providers are registered')


def test_openrouter_agent_posts_chat_completion_request_with_journal_pulse_prompt():
    http_client = DummyHttpClient(
        {
            'choices': [
                {'message': {'content': '川普政府大砍科學顧問委員會，剩餘機制的透明度與獨立性也同步下滑。'}}
            ]
        }
    )
    agent = OpenRouterSummaryAgent(
        api_key='secret-key',
        model='deepseek/deepseek-chat-v3-0324:free',
        timeout=15.0,
        http_client=http_client,
        extra_headers={'HTTP-Referer': 'https://example.com'},
    )

    result = agent.summarize(
        title='Key US science panels are being axed',
        source_text='A Nature analysis shows that the Trump administration has terminated more than 100 advisory committees.',
        max_chars=120,
    )

    assert result == '川普政府大砍科學顧問委員會，剩餘機制的透明度與獨立性也同步下滑。'
    assert http_client.calls == [
        {
            'url': 'https://openrouter.ai/api/v1/chat/completions',
            'headers': {
                'Authorization': 'Bearer secret-key',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://example.com',
            },
            'json': {
                'model': 'deepseek/deepseek-chat-v3-0324:free',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are Journal Pulse\'s summarization agent. Convert the supplied paper blurb into exactly one concise Traditional Chinese sentence for a Discord digest. The Discord format already shows the English title separately, so never repeat the English title. Output exactly one Traditional Chinese sentence only: no markdown, no HTML, no bullet points, no labels, no preamble, no quoted title, and no line breaks. Prefer concrete findings over filler like「本文指出」或「研究顯示」. Stay within the requested character budget and keep the tone crisp like a news brief.',
                    },
                    {
                        'role': 'user',
                        'content': 'Paper title (shown separately, do not repeat it): Key US science panels are being axed\nCharacter budget: 120\nWrite one concise Traditional Chinese sentence summarizing this paper blurb:\nA Nature analysis shows that the Trump administration has terminated more than 100 advisory committees.',
                    },
                ],
                'temperature': 0.2,
            },
            'timeout': 15.0,
        }
    ]


def test_openrouter_agent_normalizes_output_to_single_line_without_labels_or_repeated_title():
    http_client = DummyHttpClient(
        {
            'choices': [
                {
                    'message': {
                        'content': '中文摘要：\n「Key US science panels are being axed」指出川普政府裁撤逾百個科學顧問委員會，並削弱剩餘委員會的透明度。'
                    }
                }
            ]
        }
    )
    agent = OpenRouterSummaryAgent(
        api_key='secret-key',
        model='deepseek/deepseek-chat-v3-0324:free',
        http_client=http_client,
    )

    result = agent.summarize(
        title='Key US science panels are being axed',
        source_text='A Nature analysis shows that the Trump administration has terminated more than 100 advisory committees.',
        max_chars=24,
    )

    assert result == '川普政府裁撤逾百個科學顧問委員會，並削弱剩餘委…'
