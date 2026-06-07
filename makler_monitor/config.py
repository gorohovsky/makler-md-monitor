"""Load search criteria and monitor settings from a TOML config file.

TOML keys mirror the dataclass field names, so loading is mostly a typed copy.
Unknown keys raise (to catch typos), and the only required key is ``[search].category``.
"""

import dataclasses
import tomllib
from pathlib import Path

from .models import MonitorSettings, SearchCriteria

_BLANK_MEANS_UNSET = ('proxy', 'telegram_bot_token', 'telegram_chat_id')


def load_config(path):
    """Return ``(SearchCriteria, MonitorSettings)`` parsed from the TOML at ``path``."""
    with Path(path).open('rb') as config_file:
        data = tomllib.load(config_file)

    search = dict(data.get('search', {}))
    if 'category' not in search:
        raise ValueError("config section [search] must set 'category'")

    if 'cities' in search:
        search['cities'] = frozenset(search['cities'])
    if 'keywords' in search:
        search['keywords'] = tuple(search['keywords'])

    monitor = dict(data.get('monitor', {}))
    for key in _BLANK_MEANS_UNSET:
        if monitor.get(key) == '':
            monitor[key] = None

    criteria = _build(SearchCriteria, search, 'search')
    _validate_criteria(criteria)
    return criteria, _build(MonitorSettings, monitor, 'monitor')


def _build(dataclass_type, values, section):
    known = {field.name for field in dataclasses.fields(dataclass_type)}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f'unknown keys in [{section}]: {", ".join(sorted(unknown))}')

    return dataclass_type(**values)


def _validate_criteria(criteria):
    for currency, rate in criteria.price_rates.items():
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
            raise ValueError(f"price_rates['{currency}'] must be a positive number, got {rate!r}")

    _require_positive_int('pages_per_batch', criteria.pages_per_batch)
    if criteria.max_pages is not None:
        _require_positive_int('max_pages', criteria.max_pages)

    _check_range('price_min', criteria.price_min, 'price_max', criteria.price_max)
    for axis in ('width', 'height', 'depth'):
        _check_range(f'min_{axis}_cm', getattr(criteria, f'min_{axis}_cm'),
                     f'max_{axis}_cm', getattr(criteria, f'max_{axis}_cm'))


def _check_range(min_name, minimum, max_name, maximum):
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(f'{min_name} ({minimum}) must not exceed {max_name} ({maximum})')


def _require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'{name} must be a positive integer, got {value!r}')
