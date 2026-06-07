"""Run one check cycle: find unseen listings, keep the matches, notify, record.

Detail pages are fetched only for cards that already pass the card-level filters
(city and price), so a wrong-city or over-budget listing never costs a request.
Keyword and dimension filters need the full description, so they run after the
detail fetch.

Pages are scanned newest-first and only as far as needed: scanning stops at the first
page with no unseen listings (the rest are older and already seen), so a multi-page
burst of new listings is caught without raising ``max_pages``, which is only a safety cap.

Every fully-evaluated card is recorded as seen (matched or not) so it is notified
only once, even across separate runs. Recording happens in a ``finally`` so a
mid-batch failure never loses prior progress; a card whose detail fetch fails
transiently is left unseen and retried on the next cycle.
"""

from .client import FetchError
from .filters import card_matches, detail_matches


class Monitor:
    def __init__(self, catalog, store, notifier, criteria):
        self._catalog = catalog
        self._store = store
        self._notifier = notifier
        self._criteria = criteria

    def check(self):
        """Return (and notify) the new listings that match the criteria."""
        found = []
        handled = []
        try:
            for card in self._unseen_cards():
                try:
                    listing = self._evaluate(card)
                except FetchError:
                    continue  # transient fetch failure: stay unseen, retry next cycle

                if listing is not None:
                    self._notifier.notify(listing)
                    found.append(listing)

                handled.append(card.listing_id)
        finally:
            self._store.add_many(handled)

        return found

    def _unseen_cards(self):
        """Yield unseen cards page by page, stopping at the first page that has none."""
        yielded = set()
        for page in range(1, self._criteria.max_pages + 1):
            fresh = [card for card in self._catalog.listings_on_page(self._criteria, page)
                     if card.listing_id not in yielded and not self._store.is_seen(card.listing_id)]
            if not fresh:
                return

            for card in fresh:
                yielded.add(card.listing_id)
                yield card

    def _evaluate(self, card):
        """The matching detailed listing, or None if it does not match; may raise FetchError."""
        if not card_matches(card, self._criteria):
            return None

        listing = self._catalog.with_details(card)
        return listing if detail_matches(listing, self._criteria) else None
