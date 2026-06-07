"""Read listings from makler.md: category pages (cards) and detail descriptions.

Combines the HTTP client, HTML parser, dimension parser and URL builder. Holds no
filtering or notification logic — it only turns pages into :class:`Listing` objects.
"""

import dataclasses

from .dimensions import parse_dimensions
from .parser import parse_description, parse_listings
from .urls import category_url

_DETAIL_PATH_MARKER = '/an/'


class Catalog:
    def __init__(self, client):
        self._client = client

    def recent_listings(self, criteria):
        """Listing cards from the first ``criteria.max_pages`` category pages."""
        listings = []
        for page in range(1, criteria.max_pages + 1):
            html = self._client.get(category_url(criteria, page))
            listings.extend(parse_listings(html))

        return listings

    def with_details(self, card):
        """Fetch a listing's detail page and fill in its description and dimensions."""
        referer = card.url.split(_DETAIL_PATH_MARKER, 1)[0]
        description = parse_description(self._client.get(card.url, referer=referer))
        dimensions = parse_dimensions(description or card.snippet)

        return dataclasses.replace(card, description=description, dimensions=dimensions)
