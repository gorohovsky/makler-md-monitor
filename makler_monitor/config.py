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

    return _build(SearchCriteria, search, 'search'), _build(MonitorSettings, monitor, 'monitor')


def _build(dataclass_type, values, section):
    known = {field.name for field in dataclasses.fields(dataclass_type)}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f'unknown keys in [{section}]: {", ".join(sorted(unknown))}')

    return dataclass_type(**values)
