"""Browser-like HTTP client for makler.md, built to avoid bot detection.

A real browser keeps one identity per session, paces requests like a human, and
retries transient failures. ``BrowserClient`` does the same: it picks one browser
profile (User-Agent + matching client hints) per instance, sends a consistent set of
Russian-locale browser headers, reuses cookies, waits a randomised delay before each
request, and backs off on 429/5xx and connection errors.

The session, sleep function and random source are injectable so the behaviour can be
tested without real network or real waiting.
"""

import math
import random
import time

import requests

_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'

_COMMON_HEADERS = {
    'Accept': _ACCEPT,
    'Accept-Language': 'ru-RU,ru;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1'
}

_CHROME_WINDOWS_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)
_CHROME_MAC_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
)
_FIREFOX_WINDOWS_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'

# Each profile keeps its User-Agent and client hints consistent, like a real browser.
_BROWSER_PROFILES = (
    {
        'User-Agent': _CHROME_WINDOWS_USER_AGENT,
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    },
    {
        'User-Agent': _CHROME_MAC_USER_AGENT,
        'sec-ch-ua': '"Chromium";v="123", "Google Chrome";v="123", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    },
    {
        'User-Agent': _FIREFOX_WINDOWS_USER_AGENT
    }
)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_RETRYABLE_EXCEPTIONS = (requests.ConnectionError, requests.Timeout)
_BACKOFF_BASE_SECONDS = 2.0
_BACKOFF_JITTER_SECONDS = 1.0
_MAX_RETRY_AFTER_SECONDS = 300.0


class FetchError(Exception):
    """Raised when a URL cannot be fetched after exhausting retries."""


class BrowserClient:
    def __init__(self, settings, session=None, sleep=time.sleep, rng=random, profile=None):
        self._settings = settings
        self._sleep = sleep
        self._rng = rng
        self._session = session if session is not None else requests.Session()
        self._session.headers.update({**_COMMON_HEADERS, **(profile or rng.choice(_BROWSER_PROFILES))})
        if settings.proxy:
            self._session.proxies = {'http': settings.proxy, 'https': settings.proxy}

    def get(self, url, referer=None):
        """Fetch ``url`` and return its HTML, retrying transient failures."""
        self._wait_before_request()
        headers = {'Sec-Fetch-Site': 'same-origin', 'Referer': referer} if referer else {'Sec-Fetch-Site': 'none'}
        reason = None
        wait_hint = None
        for attempt in range(self._settings.max_retries + 1):
            if attempt:
                self._back_off(attempt, wait_hint)

            try:
                response = self._session.get(url, headers=headers, timeout=self._settings.request_timeout_seconds)
            except _RETRYABLE_EXCEPTIONS as error:
                reason, wait_hint = repr(error), None
                continue

            if response.status_code < 400:
                return response.text

            if response.status_code not in _RETRYABLE_STATUS:
                raise FetchError(f'GET {url} -> HTTP {response.status_code}')

            reason, wait_hint = f'HTTP {response.status_code}', _retry_after_seconds(response)

        raise FetchError(f'GET {url} failed after {self._settings.max_retries + 1} attempts ({reason})')

    def _wait_before_request(self):
        self._sleep(self._rng.uniform(self._settings.min_delay_seconds, self._settings.max_delay_seconds))

    def _back_off(self, attempt, wait_hint):
        base = wait_hint if wait_hint is not None else _BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
        self._sleep(base + self._rng.uniform(0, _BACKOFF_JITTER_SECONDS))


def _retry_after_seconds(response):
    try:
        seconds = float(response.headers.get('Retry-After'))
    except (TypeError, ValueError):
        return None

    if not math.isfinite(seconds) or seconds <= 0:
        return None

    return min(seconds, _MAX_RETRY_AFTER_SECONDS)
