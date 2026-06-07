"""Price parsing and HTML -> Listing parsing against real saved makler.md pages."""

from pathlib import Path

import pytest

from makler_monitor.parser import parse_description, parse_listings, parse_price

FIXTURES = Path(__file__).parent / 'fixtures'
LISTING_HTML = (FIXTURES / 'listing_page.html').read_text(encoding='utf-8')
DETAIL_HTML = (FIXTURES / 'detail_page.html').read_text(encoding='utf-8')

PRICE_CASES = [
    ('100 USD', 100.0, 'usd'),
    ('1 300 руб', 1300.0, 'rub'),
    ('80 USD', 80.0, 'usd'),
    ('500 руб', 500.0, 'rub'),
    ('1 200 lei', 1200.0, 'lei'),
    ('250 €', 250.0, 'eur'),
    ('300 евро', 300.0, 'eur'),
    ('100 $', 100.0, 'usd'),
    ('1 300 000 руб', 1300000.0, 'rub'),
    ('1 000 - 2 000 lei', 1000.0, 'lei'),
    ('450,50 lei', 450.0, 'lei'),
    ('Договорная', None, None),
    ('', None, None),
    (None, None, None),
]


@pytest.mark.parametrize('text, amount, currency', PRICE_CASES)
def test_parse_price(text, amount, currency):
    assert parse_price(text) == (amount, currency)


def test_parse_listings_returns_only_real_cards():
    listings = parse_listings(LISTING_HTML)

    assert len(listings) == 36
    for listing in listings:
        assert listing.listing_id.isdigit()
        assert listing.url.startswith('https://makler.md/ru/')
        assert listing.title


def test_listing_card_fields():
    card = {listing.listing_id: listing for listing in parse_listings(LISTING_HTML)}['65036']

    assert card.title == 'Продам стенку в идеальном состоянии'
    assert card.url == 'https://makler.md/ru/furniture-and-interior/furniture/wall-units/an/65036'
    assert (card.price, card.currency) == (100.0, 'usd')
    assert card.city == 'Тирасполь'
    assert card.image_url == 'https://media.makler.md/production/an/thumb/000/072/614/000072614297.jpg'
    assert 'ширина 190 см высота 215 см' in card.snippet
    # Dimensions are parsed later, from the fuller detail-page description.
    assert card.dimensions.is_empty


def test_listing_title_falls_back_to_link_text_when_title_attr_is_blank():
    card_html = (
        '<article id="tr_an-9">'
        '<a class="ls-detail_anUrl" href="/ru/x/an/9" title="   "><span>Реальный шкаф</span></a>'
        '</article>'
    )
    assert parse_listings(card_html)[0].title == 'Реальный шкаф'


def test_parse_description_from_detail_page():
    expected = 'Покупалась в Кишинёве за 900 евро 3 года назад. размеры ширина 190 см высота 215 см'
    assert parse_description(DETAIL_HTML) == expected


def test_card_snippet_space_separates_block_elements():
    card = (
        '<article id="tr_an-9">'
        '<a class="ls-detail_anUrl" href="/ru/x/an/9" title="t"><span>t</span></a>'
        '<p class="ls-detail_anText"><div class="subfir">отличное<br/>Высота 230 см</div></p>'
        '</article>'
    )
    assert parse_listings(card)[0].snippet == 'отличное Высота 230 см'


def test_parse_description_space_separates_block_elements():
    html = '<div id="anText"><div>В отличном состоянии</div><div>Высота 230 см</div><div>Ширина 160 см</div></div>'
    assert parse_description(html) == 'В отличном состоянии Высота 230 см Ширина 160 см'


def test_parse_description_falls_back_to_og_meta():
    html = '<html><head><meta property="og:description" content="Шкаф 120x220x50"></head><body></body></html>'
    assert parse_description(html) == 'Шкаф 120x220x50'


def test_parse_description_missing_returns_empty():
    assert parse_description('<html><body><p>нет описания</p></body></html>') == ''
