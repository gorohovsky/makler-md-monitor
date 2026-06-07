"""Category-page URL construction from search criteria."""

from makler_monitor.models import SearchCriteria
from makler_monitor.urls import category_url

WALL_UNITS = 'furniture-and-interior/furniture/wall-units'


def _criteria(**overrides):
    return SearchCriteria(**{'category': WALL_UNITS, **overrides})


def test_category_url_uses_language_region_and_category():
    expected = 'https://makler.md/ru/transnistria/furniture-and-interior/furniture/wall-units'
    assert category_url(_criteria()) == expected


def test_category_url_first_page_has_no_page_param():
    assert '?page=' not in category_url(_criteria(), page=1)


def test_category_url_second_page_adds_page_param():
    expected = 'https://makler.md/ru/transnistria/furniture-and-interior/furniture/wall-units?page=2'
    assert category_url(_criteria(), page=2) == expected


def test_category_url_supports_city_as_region_segment():
    url = category_url(_criteria(region='tiraspol', category='furniture-and-interior'))
    assert url == 'https://makler.md/ru/tiraspol/furniture-and-interior'


def test_category_url_normalises_stray_slashes():
    url = category_url(_criteria(category='/furniture-and-interior/'))
    assert url == 'https://makler.md/ru/transnistria/furniture-and-interior'
