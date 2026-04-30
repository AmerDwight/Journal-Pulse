from journal_pulse.delivery.discord_bot import DiscordBotNotifier


class DummyResponse:
    def __init__(self):
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True

    def json(self):
        return {'id': '123'}


class DummyHttpClient:
    def __init__(self):
        self.calls = []
        self.response = DummyResponse()

    def post(self, url, *, headers, json):
        self.calls.append({'url': url, 'headers': headers, 'json': json})
        return self.response


def test_discord_bot_notifier_posts_message_to_channel_via_bot_api():
    client = DummyHttpClient()
    notifier = DiscordBotNotifier(
        bot_token='token-123',
        channel_id='456789',
        http_client=client,
    )

    result = notifier.send_message('Fresh journal update')

    assert result == {'id': '123'}
    assert client.calls == [
        {
            'url': 'https://discord.com/api/v10/channels/456789/messages',
            'headers': {
                'Authorization': 'Bot token-123',
                'Content-Type': 'application/json',
            },
            'json': {'content': 'Fresh journal update'},
        }
    ]
    assert client.response.status_checked is True
