"""Command-line entry point: check once, watch on a randomised interval, or list cities."""

import argparse
import random
import time

from .catalog import Catalog
from .client import BrowserClient
from .config import load_config
from .monitor import Monitor
from .notifier import build_notifier
from .storage import SeenStore


def main(argv=None):
    args = parse_args(argv)
    criteria, settings = load_config(args.config)
    catalog = Catalog(BrowserClient(settings))

    if args.command == 'list-cities':
        _list_cities(catalog, criteria)
        return

    monitor = Monitor(catalog, SeenStore(settings.state_path), build_notifier(settings), criteria)
    if args.command == 'check':
        found = monitor.check()
        print(f'{len(found)} new match(es).')
    elif args.command == 'watch':
        _watch(monitor, settings)


def next_interval(settings, rng=random):
    """Seconds to wait before the next check, drawn uniformly from the configured window."""
    return rng.uniform(settings.check_interval_min_seconds, settings.check_interval_max_seconds)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog='makler-monitor', description='Monitor makler.md for matching listings.')
    parser.add_argument('command', choices=('check', 'watch', 'list-cities'), help='action to run')
    parser.add_argument('--config', default='config.toml', help='path to the TOML config (default: config.toml)')
    return parser.parse_args(argv)


def _watch(monitor, settings):
    print('Watching makler.md — press Ctrl-C to stop.')
    try:
        while True:
            try:
                found = monitor.check()
                print(f'{len(found)} new match(es).')
            except Exception as error:
                print(f'check failed, will retry next cycle: {error}')

            wait_seconds = next_interval(settings)
            print(f'Next check in {wait_seconds / 60:.0f} min.')
            time.sleep(wait_seconds)
    except KeyboardInterrupt:
        print('\nStopped.')


def _list_cities(catalog, criteria):
    cities = sorted({listing.city for listing in catalog.listings_on_page(criteria, 1) if listing.city})
    print('Cities currently listed in this category and region:')
    for city in cities:
        print(f'  {city}')
