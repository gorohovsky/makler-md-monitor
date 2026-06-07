"""Pure predicates deciding whether a listing matches the search criteria.

Each predicate owns one criterion and returns ``True`` when that criterion is not
configured. :func:`matches` is their conjunction, partitioned into :func:`card_matches`
(decidable from a listing card) and :func:`detail_matches` (needs the full description).
"""


def price_matches(listing, criteria):
    if criteria.price_min is None and criteria.price_max is None:
        return True

    if listing.price is None:
        return False

    amount = _in_target_currency(listing, criteria)
    if amount is None:
        return False

    return _within(amount, criteria.price_min, criteria.price_max)


def city_matches(listing, criteria):
    if not criteria.cities:
        return True

    if not listing.city:
        return False

    return _normalise(listing.city) in {_normalise(city) for city in criteria.cities}


def keywords_match(listing, criteria):
    if not criteria.keywords:
        return True

    haystack = f'{listing.title} {listing.description_text}'.casefold()
    return any(keyword.casefold() in haystack for keyword in criteria.keywords)


def dimensions_match(listing, criteria):
    dimensions = listing.dimensions
    unknown_ok = criteria.unknown_dimension_ok
    return (
        _axis_within(dimensions.width_cm, criteria.min_width_cm, criteria.max_width_cm, unknown_ok)
        and _axis_within(dimensions.height_cm, criteria.min_height_cm, criteria.max_height_cm, unknown_ok)
        and _axis_within(dimensions.depth_cm, criteria.min_depth_cm, criteria.max_depth_cm, unknown_ok)
    )


def card_matches(listing, criteria):
    """Criteria decidable from a listing card alone, before fetching its detail page."""
    return city_matches(listing, criteria) and price_matches(listing, criteria)


def detail_matches(listing, criteria):
    """Criteria that need the full description: keywords and dimensions."""
    return keywords_match(listing, criteria) and dimensions_match(listing, criteria)


def matches(listing, criteria):
    """True when ``listing`` satisfies every configured criterion."""
    return card_matches(listing, criteria) and detail_matches(listing, criteria)


def _within(value, minimum, maximum):
    return (minimum is None or value >= minimum) and (maximum is None or value <= maximum)


def _in_target_currency(listing, criteria):
    """The listing price expressed in criteria.price_currency, or None if it can't be."""
    target = criteria.price_currency
    if target is None or listing.currency == target:
        return listing.price

    rate = criteria.price_rates.get(listing.currency)
    return round(listing.price * rate, 2) if rate is not None else None


def _axis_within(value, minimum, maximum, unknown_ok):
    if minimum is None and maximum is None:
        return True

    if value is None:
        return unknown_ok

    return _within(value, minimum, maximum)


def _normalise(name):
    return name.strip().casefold()
