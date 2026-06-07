"""Catalog: turn category/detail pages into Listings via the HTTP client."""

from pathlib import Path

from makler_monitor.catalog import Catalog
from makler_monitor.models import Listing, SearchCriteria
from makler_monitor.urls import category_url

FIXTURES = Path(__file__).parent / 'fixtures'
LISTING_HTML = (FIXTURES / 'listing_page.html').read_text(encoding='utf-8')
DETAIL_HTML = (FIXTURES / 'detail_page.html').read_text(encoding='utf-8')

DETAIL_URL = 'https://makler.md/ru/furniture-and-interior/furniture/wall-units/an/65036'
CATEGORY_URL = 'https://makler.md/ru/furniture-and-interior/furniture/wall-units'


class FakeClient:
    def __init__(self, pages):
        self._pages = pages
        self.requested = []

    def get(self, url, referer=None):
        self.requested.append((url, referer))
        return self._pages[url]


def test_listings_on_page_parses_the_requested_page():
    criteria = SearchCriteria(category='furniture-and-interior/furniture/wall-units')
    client = FakeClient({category_url(criteria, 1): LISTING_HTML})

    listings = Catalog(client).listings_on_page(criteria, 1)
    assert len(listings) == 36
    assert any(listing.listing_id == '65036' for listing in listings)
    assert client.requested == [(category_url(criteria, 1), None)]


def test_with_details_adds_description_and_dimensions():
    card = Listing(listing_id='65036', title='Стенка', url=DETAIL_URL, snippet='snippet')
    detailed = Catalog(FakeClient({DETAIL_URL: DETAIL_HTML})).with_details(card)

    assert 'Кишинёве' in detailed.description
    assert (detailed.dimensions.width_cm, detailed.dimensions.height_cm) == (190, 215)


def test_with_details_sends_category_page_as_referer():
    card = Listing(listing_id='65036', title='Стенка', url=DETAIL_URL)
    client = FakeClient({DETAIL_URL: DETAIL_HTML})

    Catalog(client).with_details(card)
    assert client.requested[0] == (DETAIL_URL, CATEGORY_URL)
