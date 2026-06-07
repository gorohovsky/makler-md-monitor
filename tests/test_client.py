"""Anti-detection HTTP client: browser identity, human pacing, retry/backoff."""

import random

import pytest
import requests

from makler_monitor.client import _BROWSER_PROFILES, BrowserClient, FetchError
from makler_monitor.models import MonitorSettings


class FakeResponse:
    def __init__(self, status_code, text='<html>ok</html>', headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class FakeSession:
    """Records calls and replays queued responses or exceptions in order."""

    def __init__(self, outcomes):
        self.headers = {}
        self.proxies = {}
        self.calls = []
        self._outcomes = list(outcomes)

    def get(self, url, headers=None, timeout=None):
        self.calls.append({'url': url, 'headers': headers or {}, 'timeout': timeout})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def build(outcomes, **settings_overrides):
    settings = MonitorSettings(min_delay_seconds=1, max_delay_seconds=2, max_retries=2, **settings_overrides)
    session = FakeSession(outcomes)
    sleeps = []
    client = BrowserClient(settings, session=session, sleep=sleeps.append, rng=random.Random(0))
    return client, session, sleeps


def test_session_uses_a_browser_profile_and_russian_locale():
    _, session, _ = build([FakeResponse(200)])

    assert session.headers['User-Agent'] in {profile['User-Agent'] for profile in _BROWSER_PROFILES}
    assert session.headers['Accept-Language'].startswith('ru')


def test_get_returns_body_and_uses_timeout():
    client, session, _ = build([FakeResponse(200, text='<html>hi</html>')])

    assert client.get('https://makler.md/x') == '<html>hi</html>'
    assert session.calls[0]['url'] == 'https://makler.md/x'
    assert session.calls[0]['timeout'] == 20.0


def test_paces_with_a_randomised_delay_before_the_request():
    client, _, sleeps = build([FakeResponse(200)])

    client.get('https://makler.md/x')
    assert len(sleeps) == 1
    assert 1 <= sleeps[0] <= 2


def test_retries_on_503_then_succeeds():
    client, session, sleeps = build([FakeResponse(503), FakeResponse(200, text='ok')])

    assert client.get('https://makler.md/x') == 'ok'
    assert len(session.calls) == 2
    assert len(sleeps) == 2  # one pace + one backoff


def test_respects_retry_after_header():
    client, _, sleeps = build([FakeResponse(503, headers={'Retry-After': '7'}), FakeResponse(200)])

    client.get('https://makler.md/x')
    assert max(sleeps) >= 7


def test_raises_after_exhausting_retries():
    client, session, _ = build([FakeResponse(503), FakeResponse(503), FakeResponse(503)])

    with pytest.raises(FetchError):
        client.get('https://makler.md/x')
    assert len(session.calls) == 3  # max_retries=2 -> 3 attempts


def test_non_retryable_status_fails_without_retry():
    client, session, _ = build([FakeResponse(404)])

    with pytest.raises(FetchError):
        client.get('https://makler.md/x')
    assert len(session.calls) == 1


def test_retries_on_connection_error():
    client, session, _ = build([requests.ConnectionError('boom'), FakeResponse(200, text='ok')])

    assert client.get('https://makler.md/x') == 'ok'
    assert len(session.calls) == 2


def test_sends_referer_when_provided():
    client, session, _ = build([FakeResponse(200)])

    client.get('https://makler.md/detail', referer='https://makler.md/list')
    assert session.calls[0]['headers']['Referer'] == 'https://makler.md/list'


def test_sets_proxy_when_configured():
    _, session, _ = build([FakeResponse(200)], proxy='http://127.0.0.1:8888')

    assert session.proxies == {'http': 'http://127.0.0.1:8888', 'https': 'http://127.0.0.1:8888'}
