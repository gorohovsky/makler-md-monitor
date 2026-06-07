"""Monitor: one check cycle — find unseen listings, filter, notify, record."""

import dataclasses

from makler_monitor.client import FetchError
from makler_monitor.models import Dimensions, Listing, SearchCriteria
from makler_monitor.monitor import Monitor
from makler_monitor.storage import BacklogCursor, SeenStore


class FakeCatalog:
    def __init__(self, pages, details):
        self._pages = pages
        self._details = details
        self.detailed_ids = []
        self.fetched_pages = []

    def listings_on_page(self, criteria, page):
        self.fetched_pages.append(page)
        return list(self._pages[page - 1]) if page <= len(self._pages) else []

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


def make_criteria(**overrides):
    base = dict(
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
    return SearchCriteria(**{**base, **overrides})


def build_paged(pages, details, tmp_path, criteria=None):
    catalog = FakeCatalog(pages, details)
    notifier = FakeNotifier()
    store = SeenStore(tmp_path / 'seen.json')
    cursor = BacklogCursor(tmp_path / 'seen.cursor')
    monitor = Monitor(catalog, store, cursor, notifier, criteria or make_criteria())
    return monitor, catalog, notifier, store


def build(page_one_cards, details, tmp_path):
    return build_paged([page_one_cards], details, tmp_path)


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


def test_scans_page_one_plus_the_backfill_batch(tmp_path):
    cards = [make_card(str(index)) for index in range(1, 4)]
    details = {card.listing_id: detailed(card, Dimensions(120, 220, 45)) for card in cards}
    monitor, catalog, _, _ = build_paged([[card] for card in cards], details, tmp_path)

    result = monitor.check()   # cursor at 1, batch of 2 -> pages 1 and 2
    assert {listing.listing_id for listing in result} == {'1', '2'}
    assert catalog.fetched_pages == [1, 2]


def test_backfill_cursor_advances_across_runs(tmp_path):
    cards = [make_card(str(index)) for index in range(1, 6)]
    details = {card.listing_id: detailed(card, Dimensions(120, 220, 45)) for card in cards}
    monitor, catalog, _, _ = build_paged([[card] for card in cards], details, tmp_path)

    monitor.check()   # pages 1, 2
    monitor.check()   # page 1 again (for new) plus backfill 3, 4
    assert catalog.fetched_pages == [1, 2, 1, 3, 4]


def test_cursor_wraps_at_the_end_of_the_category(tmp_path):
    first, second = make_card('1'), make_card('2')
    details = {'1': detailed(first, Dimensions(120, 220, 45)), '2': detailed(second, Dimensions(120, 220, 45))}
    monitor, catalog, _, _ = build_paged([[first], [second]], details, tmp_path)   # 2 real pages

    monitor.check()                  # pages 1, 2 -> cursor advances to 3
    monitor.check()                  # pages 1, 3; page 3 is empty -> wrap to 1
    catalog.fetched_pages.clear()
    monitor.check()                  # restarts at pages 1, 2
    assert catalog.fetched_pages == [1, 2]


def test_max_pages_caps_the_backfill_depth(tmp_path):
    cards = [make_card(str(index)) for index in range(1, 6)]
    details = {card.listing_id: detailed(card, Dimensions(120, 220, 45)) for card in cards}
    monitor, catalog, _, _ = build_paged([[card] for card in cards], details, tmp_path,
                                         criteria=make_criteria(max_pages=2, pages_per_batch=1))

    monitor.check()                  # cursor 1 -> page 1
    monitor.check()                  # cursor 2 -> pages 1, 2; next would be 3 > cap -> wrap
    catalog.fetched_pages.clear()
    monitor.check()                  # cursor 1 -> page 1 only
    assert catalog.fetched_pages == [1]   # page 3 is never scanned (beyond max_pages = 2)


def test_max_pages_drops_batch_pages_beyond_the_cap(tmp_path):
    cards = [make_card(str(index)) for index in range(1, 7)]
    details = {card.listing_id: detailed(card, Dimensions(120, 220, 45)) for card in cards}
    monitor, catalog, _, _ = build_paged([[card] for card in cards], details, tmp_path,
                                         criteria=make_criteria(max_pages=4, pages_per_batch=3))

    monitor.check()                  # cursor 1 -> pages 1,2,3
    catalog.fetched_pages.clear()
    monitor.check()                  # cursor 4 -> batch 4,5,6 but cap 4 keeps only [1, 4]
    assert catalog.fetched_pages == [1, 4]


def test_does_not_process_a_listing_repeated_across_pages(tmp_path):
    card = make_card('1')
    details = {'1': detailed(card, Dimensions(120, 220, 45))}
    monitor, catalog, _, _ = build_paged([[card], [card], []], details, tmp_path)

    assert len(monitor.check()) == 1
    assert catalog.detailed_ids == ['1']   # detailed once, not twice


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
