"""Build makler.md category-page URLs from search criteria."""

from .constants import BASE_URL


def category_url(criteria, page=1):
    """URL of one category listing page: /{language}/{region}/{category}[?page=N]."""
    segments = (criteria.language, criteria.region, criteria.category)
    path = '/'.join(segment.strip('/') for segment in segments)
    url = f'{BASE_URL}/{path}'

    return f'{url}?page={page}' if page > 1 else url
