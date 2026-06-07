"""Notification formatting and delivery (console and Telegram)."""

import pytest

from makler_monitor.models import Dimensions, Listing, MonitorSettings
from makler_monitor.notifier import ConsoleNotifier, TelegramNotifier, build_notifier, format_listing


def make_listing(**overrides):
    base = {
        'listing_id': '1',
        'title': 'Шкаф-купе',
        'url': 'https://makler.md/ru/x/an/1',
        'price': 100.0,
        'currency': 'usd',
        'city': 'Тирасполь',
        'dimensions': Dimensions(120, 220, 45)
    }
    return Listing(**{**base, **overrides})


def test_format_includes_title_price_city_and_url():
    text = format_listing(make_listing())

    assert 'Шкаф-купе' in text
    assert '100 USD' in text
    assert 'Тирасполь' in text
    assert 'https://makler.md/ru/x/an/1' in text


def test_format_shows_known_dimensions():
    text = format_listing(make_listing())

    assert '120' in text and '220' in text and '45' in text


def test_format_handles_missing_price():
    assert 'цена не указана' in format_listing(make_listing(price=None, currency=None))


def test_console_notifier_writes_formatted_text():
    written = []
    ConsoleNotifier(output=written.append).notify(make_listing())

    assert len(written) == 1
    assert 'Шкаф-купе' in written[0]


def test_telegram_notifier_posts_message():
    sent = []

    class Response:
        def raise_for_status(self):
            pass

    def fake_send(url, data=None, timeout=None):
        sent.append((url, data, timeout))
        return Response()

    TelegramNotifier('TOKEN', 'CHAT', send=fake_send).notify(make_listing())

    url, data, timeout = sent[0]
    assert url == 'https://api.telegram.org/botTOKEN/sendMessage'
    assert data['chat_id'] == 'CHAT'
    assert 'Шкаф-купе' in data['text']
    assert timeout is not None


def test_build_notifier_defaults_to_console():
    assert isinstance(build_notifier(MonitorSettings()), ConsoleNotifier)


def test_build_notifier_returns_telegram_when_configured():
    settings = MonitorSettings(notifier='telegram', telegram_bot_token='T', telegram_chat_id='C')

    assert isinstance(build_notifier(settings), TelegramNotifier)


def test_build_notifier_telegram_requires_credentials():
    with pytest.raises(ValueError):
        build_notifier(MonitorSettings(notifier='telegram'))
