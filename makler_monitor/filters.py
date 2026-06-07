"""Pure predicates deciding whether a listing matches the search criteria.

Each predicate owns one criterion and returns ``True`` when that criterion is not
configured, so :func:`matches` is simply their conjunction. Add a criterion by adding a
predicate here and a clause to :func:`matches`.
"""


def price_matches(listing, criteria):
    if criteria.price_min is None and criteria.price_max is None:
        return True

    if listing.price is None:
        return False

    if criteria.price_currency and listing.currency != criteria.price_currency:
        return False

    return _within(listing.price, criteria.price_min, criteria.price_max)


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
        _axis_within(dimensions.width_cm, criteria.max_width_cm, unknown_ok)
        and _axis_within(dimensions.height_cm, criteria.max_height_cm, unknown_ok)
        and _axis_within(dimensions.depth_cm, criteria.max_depth_cm, unknown_ok)
    )


def matches(listing, criteria):
    """True when ``listing`` satisfies every configured criterion."""
    return (
        price_matches(listing, criteria)
        and city_matches(listing, criteria)
        and keywords_match(listing, criteria)
        and dimensions_match(listing, criteria)
    )


def _within(value, minimum, maximum):
    return (minimum is None or value >= minimum) and (maximum is None or value <= maximum)


def _axis_within(value, maximum, unknown_ok):
    if maximum is None:
        return True

    if value is None:
        return unknown_ok

    return value <= maximum


def _normalise(name):
    return name.strip().casefold()
