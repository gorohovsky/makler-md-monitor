"""Run one check cycle: find unseen listings, keep the matches, notify, record.

Detail pages are fetched only for cards that already pass the card-level filters
(city and price), so a wrong-city or over-budget listing never costs a request.
Keyword and dimension filters need the full description, so they run after the
detail fetch. Every unseen card is recorded as seen, matched or not, so it is
evaluated only once.
"""

from .filters import card_matches, detail_matches


class Monitor:
    def __init__(self, catalog, store, notifier, criteria):
        self._catalog = catalog
        self._store = store
        self._notifier = notifier
        self._criteria = criteria

    def check(self):
        """Return (and notify) the new listings that match the criteria."""
        new_cards = [card for card in self._catalog.recent_listings(self._criteria)
                     if not self._store.is_seen(card.listing_id)]

        found = []
        for card in new_cards:
            listing = self._matching_detail(card)
            if listing is not None:
                self._notifier.notify(listing)
                found.append(listing)

        self._store.add_many(card.listing_id for card in new_cards)
        return found

    def _matching_detail(self, card):
        if not card_matches(card, self._criteria):
            return None

        listing = self._catalog.with_details(card)
        return listing if detail_matches(listing, self._criteria) else None
