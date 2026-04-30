from __future__ import annotations

import json
from collections.abc import Callable
from re import escape, sub
from typing import Protocol

import httpx

from journal_pulse.config import Settings

OPENROUTER_API_BASE_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_DEFAULT_MODEL = 'nvidia/nemotron-3-super-120b-a12b:free'


class SummaryAgent(Protocol):
    provider_name: str

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str: ...


class OpenRouterSummaryAgent:
    provider_name = 'openrouter'

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        api_base_url: str = OPENROUTER_API_BASE_URL,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.http_client = http_client or httpx.Client()
        self.extra_headers = extra_headers or {}

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str:
        response = self.http_client.post(
            f'{self.api_base_url}/chat/completions',
            headers=self._headers(),
            json={
                'model': self.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': "You are Journal Pulse's summarization agent. Convert the supplied paper blurb into exactly one concise Traditional Chinese sentence for a Discord digest. The Discord format already shows the English title separately, so never repeat the English title. Output exactly one Traditional Chinese sentence only: no markdown, no HTML, no bullet points, no labels, no preamble, no quoted title, and no line breaks. Prefer concrete findings over filler like「本文指出」或「研究顯示」. Stay within the requested character budget and keep the tone crisp like a news brief.",
                    },
                    {
                        'role': 'user',
                        'content': (
                            f'Paper title (shown separately, do not repeat it): {title}\n'
                            f'Character budget: {max_chars}\n'
                            'Write one concise Traditional Chinese sentence summarizing this paper blurb:\n'
                            f'{source_text}'
                        ),
                    },
                ],
                'temperature': 0.2,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get('choices', [{}])[0].get('message', {}).get('content', '')
        return _normalize_summary_output(str(content), title=title, max_chars=max_chars)

    def _headers(self) -> dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            **self.extra_headers,
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers


class AgentAllocator:
    def __init__(
        self,
        *,
        agent_factories: dict[str, Callable[[], SummaryAgent]],
        provider_order: tuple[str, ...] | None = None,
    ) -> None:
        self.agent_factories = agent_factories
        self.provider_order = provider_order or tuple(agent_factories.keys())

    def allocate(self, *, excluded_providers: tuple[str, ...] = ()) -> SummaryAgent:
        for provider_name in self.provider_order:
            if provider_name in excluded_providers:
                continue
            factory = self.agent_factories.get(provider_name)
            if factory is None:
                continue
            try:
                return factory()
            except Exception:
                continue
        raise RuntimeError('No summary agents available')


class FailoverSummaryBackend:
    def __init__(self, *, allocator: AgentAllocator, agent: SummaryAgent) -> None:
        self.allocator = allocator
        self.agent = agent

    @property
    def active_provider(self) -> str:
        return self.agent.provider_name

    def summarize(self, *, title: str, source_text: str, max_chars: int) -> str:
        attempted = []
        while True:
            current_agent = self.agent
            try:
                return current_agent.summarize(title=title, source_text=source_text, max_chars=max_chars)
            except Exception as exc:
                attempted.append(current_agent.provider_name)
                try:
                    self.agent = self.allocator.allocate(excluded_providers=tuple(attempted))
                except RuntimeError:
                    raise exc


def build_runtime_summarizer(settings: Settings | None = None) -> FailoverSummaryBackend | None:
    settings = settings or Settings()
    backend = settings.llm_backend.strip().lower()
    if backend in {'', 'none', 'disabled'}:
        return None

    provider_order = _parse_provider_order(settings)
    agent_factories = _build_agent_factories(settings, provider_order)
    allocator = AgentAllocator(agent_factories=agent_factories, provider_order=provider_order)
    return FailoverSummaryBackend(allocator=allocator, agent=allocator.allocate())


def _build_agent_factories(settings: Settings, provider_order: tuple[str, ...]) -> dict[str, Callable[[], SummaryAgent]]:
    factories: dict[str, Callable[[], SummaryAgent]] = {}
    extra_headers = _parse_extra_headers(settings.llm_extra_headers_json)

    for provider_name in provider_order:
        if provider_name == 'openrouter':
            if not settings.llm_api_key.strip():
                raise ValueError('LLM_API_KEY is required for provider: openrouter')
            model = settings.llm_model.strip() or OPENROUTER_DEFAULT_MODEL
            api_base_url = settings.llm_api_base_url.strip() or OPENROUTER_API_BASE_URL
            factories[provider_name] = lambda provider_name=provider_name, model=model, api_base_url=api_base_url: OpenRouterSummaryAgent(
                api_key=settings.llm_api_key,
                model=model,
                api_base_url=api_base_url,
                timeout=settings.llm_timeout_seconds,
                extra_headers=extra_headers,
            )
            continue
        raise ValueError(f'Unsupported LLM provider: {provider_name}')

    return factories


def _parse_provider_order(settings: Settings) -> tuple[str, ...]:
    raw_value = settings.llm_provider_order.strip() or settings.llm_backend.strip()
    providers = tuple(part.strip().lower() for part in raw_value.split(',') if part.strip())
    return providers or ('openrouter',)


def _parse_extra_headers(raw_value: str) -> dict[str, str]:
    if not raw_value.strip():
        return {}
    payload = json.loads(raw_value)
    if not isinstance(payload, dict):
        raise ValueError('LLM extra headers must be a JSON object')
    return {str(key): str(value) for key, value in payload.items()}


def _normalize_summary_output(text: str, *, title: str, max_chars: int) -> str:
    normalized = ' '.join(text.split())
    normalized = sub(r'^中文摘要[:：]\s*', '', normalized)
    normalized = normalized.replace(f'「{title}」', '').replace(f'“{title}”', '').replace(f'"{title}"', '')
    normalized = sub(rf'^{escape(title)}\s*[:：\-–—]\s*', '', normalized)
    normalized = sub(r'^(本文指出|研究顯示|研究指出|文章指出|指出)', '', normalized).lstrip(' ，；：:')
    normalized = normalized.strip()
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 1].rstrip(' ，；：:')
    return truncated + '…'
