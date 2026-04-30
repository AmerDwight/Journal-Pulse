from __future__ import annotations

import httpx


class DiscordBotNotifier:
    def __init__(
        self,
        *,
        bot_token: str,
        channel_id: str,
        http_client: httpx.Client | None = None,
        api_base: str = 'https://discord.com/api/v10',
    ) -> None:
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.api_base = api_base.rstrip('/')

    def send_message(self, content: str) -> dict:
        response = self.http_client.post(
            f'{self.api_base}/channels/{self.channel_id}/messages',
            headers={
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json',
            },
            json={'content': content},
        )
        response.raise_for_status()
        return response.json()
