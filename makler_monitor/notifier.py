"""Format matched listings and deliver them to the console or Telegram."""

import requests

_TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
_TELEGRAM_TIMEOUT_SECONDS = 10


def format_listing(listing):
    """A short human-readable summary of a listing for a notification."""
    lines = [listing.title, _format_price(listing)]
    if listing.city:
        lines.append(listing.city)

    dimensions = _format_dimensions(listing.dimensions)
    if dimensions:
        lines.append(dimensions)

    lines.append(listing.url)
    return '\n'.join(lines)


class ConsoleNotifier:
    def __init__(self, output=print):
        self._output = output

    def notify(self, listing):
        self._output(f'\n{format_listing(listing)}\n')


class TelegramNotifier:
    def __init__(self, bot_token, chat_id, send=None):
        self._endpoint = _TELEGRAM_API.format(token=bot_token)
        self._chat_id = chat_id
        self._send = send if send is not None else requests.post

    def notify(self, listing):
        payload = {'chat_id': self._chat_id, 'text': format_listing(listing)}
        response = self._send(self._endpoint, data=payload, timeout=_TELEGRAM_TIMEOUT_SECONDS)
        response.raise_for_status()


def build_notifier(settings):
    """Pick the notifier named in settings; default to the console."""
    if settings.notifier == 'telegram':
        if not (settings.telegram_bot_token and settings.telegram_chat_id):
            raise ValueError('telegram notifier needs telegram_bot_token and telegram_chat_id')

        return TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    return ConsoleNotifier()


def _format_price(listing):
    if not listing.price:
        return 'цена не указана'

    return f'{listing.price:g} {(listing.currency or "").upper()}'.strip()


def _format_dimensions(dimensions):
    labelled = (('Ш', dimensions.width_cm), ('В', dimensions.height_cm), ('Г', dimensions.depth_cm))
    parts = [f'{label}{value:g}' for label, value in labelled if value is not None]
    return f'размеры {" ".join(parts)} см' if parts else ''
