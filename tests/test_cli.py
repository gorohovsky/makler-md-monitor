"""CLI argument parsing and the randomised watch interval."""

import random

from makler_monitor.cli import next_interval, parse_args
from makler_monitor.models import MonitorSettings


def test_next_interval_falls_within_the_configured_window():
    settings = MonitorSettings(check_interval_min_seconds=600, check_interval_max_seconds=1200)

    value = next_interval(settings, rng=random.Random(0))
    assert 600 <= value <= 1200


def test_next_interval_draws_uniformly_between_min_and_max():
    calls = []

    class StubRng:
        def uniform(self, low, high):
            calls.append((low, high))
            return low

    settings = MonitorSettings(check_interval_min_seconds=600, check_interval_max_seconds=1200)
    next_interval(settings, rng=StubRng())

    assert calls == [(600, 1200)]


def test_parse_args_reads_command_and_config():
    args = parse_args(['watch', '--config', 'my.toml'])

    assert args.command == 'watch'
    assert args.config == 'my.toml'


def test_parse_args_defaults_config_path():
    assert parse_args(['check']).config == 'config.toml'
