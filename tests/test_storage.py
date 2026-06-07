"""Persistence of already-seen announcement IDs."""

from makler_monitor.storage import SeenStore


def test_unknown_id_is_not_seen(tmp_path):
    assert not SeenStore(tmp_path / 'seen.json').is_seen('123')


def test_mark_seen_persists_across_instances(tmp_path):
    path = tmp_path / 'seen.json'
    SeenStore(path).mark_seen('123')

    assert SeenStore(path).is_seen('123')


def test_add_many_persists_all(tmp_path):
    path = tmp_path / 'seen.json'
    SeenStore(path).add_many(['1', '2', '3'])

    reloaded = SeenStore(path)
    assert all(reloaded.is_seen(listing_id) for listing_id in ('1', '2', '3'))
    assert len(reloaded) == 3


def test_corrupt_file_is_treated_as_empty(tmp_path):
    path = tmp_path / 'seen.json'
    path.write_text('not valid json {', encoding='utf-8')

    store = SeenStore(path)
    assert not store.is_seen('1')
    store.mark_seen('1')
    assert SeenStore(path).is_seen('1')


def test_no_rewrite_when_id_already_seen(tmp_path):
    path = tmp_path / 'seen.json'
    store = SeenStore(path)
    store.mark_seen('1')
    mtime = path.stat().st_mtime_ns

    store.mark_seen('1')

    assert path.stat().st_mtime_ns == mtime


def test_creates_missing_parent_directories(tmp_path):
    path = tmp_path / 'nested' / 'state' / 'seen.json'
    SeenStore(path).mark_seen('1')

    assert path.exists()
