"""Pure matching predicates: price, city, keywords, dimensions, and their conjunction."""

from makler_monitor.filters import city_matches, dimensions_match, keywords_match, matches, price_matches
from makler_monitor.models import Dimensions, Listing, SearchCriteria


def make_listing(**overrides):
    return Listing(**{'listing_id': '1', 'title': 'Шкаф-купе', 'url': 'https://makler.md/ru/x/an/1', **overrides})


def make_criteria(**overrides):
    return SearchCriteria(**{'category': 'furniture-and-interior', **overrides})


def dims(width=None, height=None, depth=None):
    return Dimensions(width_cm=width, height_cm=height, depth_cm=depth)


def test_price_no_filter_passes():
    assert price_matches(make_listing(price=999, currency='usd'), make_criteria())


def test_price_within_range_and_matching_currency():
    criteria = make_criteria(price_min=50, price_max=200, price_currency='usd')
    assert price_matches(make_listing(price=100, currency='usd'), criteria)


def test_price_rejects_currency_mismatch():
    criteria = make_criteria(price_min=50, price_max=200, price_currency='usd')
    assert not price_matches(make_listing(price=100, currency='rub'), criteria)


def test_price_rejects_above_maximum():
    criteria = make_criteria(price_max=200, price_currency='usd')
    assert not price_matches(make_listing(price=300, currency='usd'), criteria)


def test_price_rejects_missing_price_when_filtering():
    criteria = make_criteria(price_min=50, price_currency='usd')
    assert not price_matches(make_listing(price=None), criteria)


def test_city_no_filter_passes():
    assert city_matches(make_listing(city='Тирасполь'), make_criteria())


def test_city_in_selected_set_is_case_insensitive():
    criteria = make_criteria(cities=frozenset({'Тирасполь', 'Бендеры'}))
    assert city_matches(make_listing(city='тирасполь'), criteria)


def test_city_outside_selected_set_rejected():
    criteria = make_criteria(cities=frozenset({'Тирасполь'}))
    assert not city_matches(make_listing(city='Рыбница'), criteria)


def test_city_missing_rejected_when_filtering():
    criteria = make_criteria(cities=frozenset({'Тирасполь'}))
    assert not city_matches(make_listing(city=None), criteria)


def test_keywords_no_filter_passes():
    assert keywords_match(make_listing(title='Диван'), make_criteria())


def test_keyword_found_in_description_case_insensitive():
    criteria = make_criteria(keywords=('шкаф',))
    assert keywords_match(make_listing(title='Мебель', description='Большой ШКАФ дубовый'), criteria)


def test_keyword_absent_rejected():
    criteria = make_criteria(keywords=('шкаф',))
    assert not keywords_match(make_listing(title='Диван', description='кожаный'), criteria)


def test_dimensions_no_filter_passes():
    assert dimensions_match(make_listing(dimensions=dims(999, 999, 999)), make_criteria())


def test_dimensions_within_max_pass():
    criteria = make_criteria(max_width_cm=130, max_height_cm=230, max_depth_cm=50)
    assert dimensions_match(make_listing(dimensions=dims(120, 220, 45)), criteria)


def test_dimensions_over_max_rejected():
    criteria = make_criteria(max_width_cm=130)
    assert not dimensions_match(make_listing(dimensions=dims(width=140)), criteria)


def test_dimensions_unknown_allowed_by_default():
    criteria = make_criteria(max_depth_cm=50)
    assert dimensions_match(make_listing(dimensions=dims(120, 220, None)), criteria)


def test_dimensions_unknown_rejected_in_strict_mode():
    criteria = make_criteria(max_depth_cm=50, unknown_dimension_ok=False)
    assert not dimensions_match(make_listing(dimensions=dims(120, 220, None)), criteria)


def test_matches_requires_every_criterion():
    criteria = make_criteria(
        cities=frozenset({'Тирасполь'}),
        keywords=('шкаф',),
        price_min=50,
        price_max=200,
        price_currency='usd',
        max_width_cm=130,
        max_height_cm=230,
        max_depth_cm=50
    )
    listing = make_listing(
        title='Шкаф-купе',
        city='Тирасполь',
        price=100,
        currency='usd',
        description='шкаф 120х220х45',
        dimensions=dims(120, 220, 45)
    )
    assert matches(listing, criteria)


def test_matches_fails_when_single_criterion_fails():
    criteria = make_criteria(cities=frozenset({'Тирасполь'}), max_width_cm=130)
    listing = make_listing(city='Бендеры', dimensions=dims(width=120))
    assert not matches(listing, criteria)
