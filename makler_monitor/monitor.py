"""Run one check cycle: catch new listings on page 1 and advance the backlog sweep.

Page 1 is scanned every run so newly-posted listings (which appear at the top) are caught
within one interval. A persisted cursor also sweeps the rest of the category a few pages
per run (``pages_per_batch``), wrapping at the end, so the whole backlog is covered over
time. ``max_pages`` optionally caps the sweep depth; unset means the entire category.

Each listing is processed once (tracked by ID), wherever the sweep finds it; already-seen
listings are skipped before any detail fetch. Full backlog coverage assumes the sweep keeps
pace with new postings — on a very busy category set ``max_pages`` to force regular wraps.
Recording happens in a ``finally`` so a mid-batch failure never loses prior progress; a card
whose detail fetch fails transiently is retried next cycle.
"""

from .client import FetchError
from .filters import card_matches, detail_matches


class Monitor:
    def __init__(self, catalog, store, cursor, notifier, criteria):
        self._catalog = catalog
        self._store = store
        self._cursor = cursor
        self._notifier = notifier
        self._criteria = criteria

    def check(self):
        """Return (and notify) the new listings that match the criteria."""
        start_page = self._cursor.page()
        found = []
        handled = []
        seen_now = set()
        reached_end = False
        try:
            for page in self._pages_to_scan(start_page):
                cards = self._catalog.listings_on_page(self._criteria, page)
                if not cards and page != 1:
                    reached_end = True  # past the last page: the sweep has covered the category
                    break

                for card in cards:
                    if card.listing_id in seen_now or self._store.is_seen(card.listing_id):
                        continue

                    seen_now.add(card.listing_id)
                    try:
                        listing = self._evaluate(card)
                    except FetchError:
                        continue  # not recorded -> retried next cycle

                    if listing is not None:
                        self._notifier.notify(listing)
                        found.append(listing)

                    handled.append(card.listing_id)
        finally:
            self._store.add_many(handled)

        # Only advance the cursor on a clean pass; a failed page fetch retries the same batch.
        self._cursor.set_page(self._next_page(start_page, reached_end))
        return found

    def _pages_to_scan(self, start_page):
        cap = self._criteria.max_pages
        batch = range(start_page, start_page + self._criteria.pages_per_batch)
        pages = [1] + [page for page in batch if cap is None or page <= cap]
        return sorted(set(pages))

    def _next_page(self, start_page, reached_end):
        cap = self._criteria.max_pages
        following = start_page + self._criteria.pages_per_batch
        if reached_end or (cap is not None and following > cap):
            return 1

        return following

    def _evaluate(self, card):
        """The matching detailed listing, or None if it does not match; may raise FetchError."""
        if not card_matches(card, self._criteria):
            return None

        listing = self._catalog.with_details(card)
        return listing if detail_matches(listing, self._criteria) else None
