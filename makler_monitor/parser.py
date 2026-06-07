"""Parse makler.md HTML into :class:`Listing` models. Pure functions, no network."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import BASE_URL
from .models import Listing

_HTML_PARSER = 'lxml'
_LISTING_ID_IN_HREF = re.compile(r'/an/(\d+)')

# Order matters only in that every token maps to a single normalised currency code.
_CURRENCY_TOKENS = (
    ('руб', 'rub'), ('rub', 'rub'),
    ('лей', 'lei'), ('lei', 'lei'), ('mdl', 'lei'),
    ('евро', 'eur'), ('eur', 'eur'), ('€', 'eur'),
    ('usd', 'usd'), ('$', 'usd'),
)


def parse_price(text):
    """Return ``(amount, currency_code)`` from a price label like ``'1 300 руб'``."""
    if not text:
        return (None, None)

    lowered = text.lower()
    currency = next((code for token, code in _CURRENCY_TOKENS if token in lowered), None)
    # makler prices are space-grouped integers ("1 300 руб"); take the first number and
    # drop any trailing range/cents fragment ("1 000 - 2 000" -> 1000, "450,50" -> 450).
    number = re.search(r'\d[\d\s]*', text)
    amount = float(re.sub(r'\s', '', number.group())) if number else None
    return (amount, currency)


def _node_text(node):
    """Text of a node, with block/inline boundaries space-joined so words never glue."""
    return node.get_text(separator=' ', strip=True)


def _text_or_none(node):
    if node is None:
        return None

    return _node_text(node) or None


def _card_to_listing(article, base_url):
    link = article.find('a', class_='ls-detail_anUrl', href=True)
    match = _LISTING_ID_IN_HREF.search(link['href']) if link else None
    if match is None:
        return None

    href = link['href']
    price, currency = parse_price(_text_or_none(article.find('span', class_='ls-detail_price')))
    image_block = article.find('div', class_='ls-detail_imgBlock')
    image_tag = image_block.find('img') if image_block else None
    return Listing(
        listing_id=match.group(1),
        title=(link.get('title') or '').strip() or link.get_text(strip=True),
        url=urljoin(base_url, href),
        price=price,
        currency=currency,
        city=_text_or_none(article.find(id='pointer_icon')),
        posted_at=_text_or_none(article.find('div', class_='ls-detail_time')),
        snippet=_text_or_none(article.find('div', class_='subfir')) or '',
        image_url=image_tag.get('src') if image_tag else None
    )


def parse_listings(html, base_url=BASE_URL):
    """Parse every real announcement card on a category page into a ``Listing``."""
    soup = BeautifulSoup(html, _HTML_PARSER)
    cards = (_card_to_listing(article, base_url) for article in soup.find_all('article'))
    return [card for card in cards if card is not None]


def parse_description(html):
    """Return the full free-text description from an announcement detail page."""
    soup = BeautifulSoup(html, _HTML_PARSER)
    node = soup.find(id='anText') or soup.find(attrs={'itemprop': 'description'}) or soup.find('div', class_='ittext')
    if node is not None:
        return _node_text(node)

    meta = soup.find('meta', attrs={'property': 'og:description'}) or soup.find('meta', attrs={'name': 'description'})
    return meta.get('content', '').strip() if meta else ''
