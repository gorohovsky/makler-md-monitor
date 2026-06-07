"""Monitor: one check cycle — find unseen listings, filter, notify, record."""

import dataclasses

from makler_monitor.client import FetchError
from makler_monitor.models import Dimensions, Listing, SearchCriteria
from makler_monitor.monitor import Monitor
from makler_monitor.storage import SeenStore


class FakeCatalog:
    def __init__(self, cards, details):
        self._cards = cards
        self._details = details
        self.detailed_ids = []

    def recent_listings(self, criteria):
        return list(self._cards)

    def with_details(self, card):
        self.detailed_ids.append(card.listing_id)
        if card.listing_id not in self._details:
            raise FetchError(f'detail fetch failed for {card.listing_id}')

        return self._details[card.listing_id]


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def notify(self, listing):
        self.sent.append(listing)


def make_card(listing_id, **overrides):
    base = {
        'listing_id': listing_id,
        'title': 'Шкаф',
        'url': f'https://makler.md/ru/x/an/{listing_id}',
        'city': 'Тирасполь',
        'price': 100.0,
        'currency': 'usd',
        'snippet': 'шкаф'
    }
    return Listing(**{**base, **overrides})


def detailed(card, dimensions):
    return dataclasses.replace(card, description='шкаф', dimensions=dimensions)


def make_criteria():
    return SearchCriteria(
        category='c',
        cities=frozenset({'Тирасполь'}),
        price_min=50,
        price_max=200,
        price_currency='usd',
        max_width_cm=130,
        max_height_cm=230,
        max_depth_cm=50,
        keywords=('шкаф',)
    )


def build(cards, details, tmp_path):
    catalog = FakeCatalog(cards, details)
    notifier = FakeNotifier()
    store = SeenStore(tmp_path / 'seen.json')
    return Monitor(catalog, store, notifier, make_criteria()), catalog, notifier, store


def test_notifies_new_matching_listing(tmp_path):
    card = make_card('1')
    match = detailed(card, Dimensions(120, 220, 45))
    monitor, catalog, notifier, store = build([card], {'1': match}, tmp_path)

    result = monitor.check()

    assert [listing.listing_id for listing in result] == ['1']
    assert notifier.sent == [match]
    assert catalog.detailed_ids == ['1']
    assert store.is_seen('1')


def test_skips_already_seen_listing(tmp_path):
    card = make_card('1')
    monitor, catalog, notifier, store = build([card], {'1': detailed(card, Dimensions(120, 220, 45))}, tmp_path)
    store.mark_seen('1')

    assert monitor.check() == []
    assert notifier.sent == []
    assert catalog.detailed_ids == []


def test_oversized_listing_is_recorded_but_not_notified(tmp_path):
    card = make_card('2')
    too_wide = detailed(card, Dimensions(140, 220, 45))
    monitor, catalog, notifier, store = build([card], {'2': too_wide}, tmp_path)

    assert monitor.check() == []
    assert notifier.sent == []
    assert catalog.detailed_ids == ['2']
    assert store.is_seen('2')


def test_wrong_city_is_skipped_without_fetching_detail(tmp_path):
    card = make_card('3', city='Рыбница')
    monitor, catalog, notifier, store = build([card], {}, tmp_path)

    assert monitor.check() == []
    assert catalog.detailed_ids == []
    assert store.is_seen('3')


def test_second_check_does_not_renotify(tmp_path):
    card = make_card('1')
    monitor, _, notifier, _ = build([card], {'1': detailed(card, Dimensions(120, 220, 45))}, tmp_path)

    monitor.check()
    monitor.check()

    assert len(notifier.sent) == 1


def test_a_new_run_does_not_renotify_a_persisted_listing(tmp_path):
    card = make_card('1')
    details = {'1': detailed(card, Dimensions(120, 220, 45))}

    first_monitor, _, first_notifier, _ = build([card], details, tmp_path)
    assert len(first_monitor.check()) == 1
    assert len(first_notifier.sent) == 1

    # A separate process run: fresh monitor, store and notifier over the same state file.
    second_monitor, second_catalog, second_notifier, _ = build([card], details, tmp_path)
    assert second_monitor.check() == []
    assert second_notifier.sent == []
    assert second_catalog.detailed_ids == []


def test_a_failed_detail_fetch_does_not_drop_progress_for_other_cards(tmp_path):
    good = make_card('1')
    failing = make_card('2')  # no detail entry -> with_details raises FetchError
    details = {'1': detailed(good, Dimensions(120, 220, 45))}
    monitor, _, notifier, store = build([good, failing], details, tmp_path)

    assert [listing.listing_id for listing in monitor.check()] == ['1']
    assert [listing.listing_id for listing in notifier.sent] == ['1']
    assert store.is_seen('1')        # the good card is recorded despite the later failure
    assert not store.is_seen('2')    # the failed card stays unseen, to be retried

    # A new run must not re-notify the good card, and retries only the failed one.
    monitor2, _, notifier2, _ = build([good, failing], details, tmp_path)
    assert monitor2.check() == []
    assert notifier2.sent == []
