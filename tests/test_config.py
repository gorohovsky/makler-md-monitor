"""Loading SearchCriteria and MonitorSettings from a TOML config file."""

import pytest

from makler_monitor.config import load_config

FULL_CONFIG = """
[search]
category = "furniture-and-interior/furniture/wall-units"
region = "transnistria"
cities = ["Тирасполь", "Бендеры"]
keywords = ["шкаф", "купе"]
price_min = 50
price_max = 200
price_currency = "usd"
min_width_cm = 90
max_width_cm = 130
max_height_cm = 230
max_depth_cm = 50
max_pages = 2

[search.price_rates]
usd = 16.3
eur = 19.16
lei = 0.96

[monitor]
check_interval_min_seconds = 600
check_interval_max_seconds = 1200
notifier = "telegram"
telegram_bot_token = "T"
telegram_chat_id = "C"
"""


def write_config(tmp_path, text):
    path = tmp_path / 'config.toml'
    path.write_text(text, encoding='utf-8')
    return path


def test_loads_full_config(tmp_path):
    criteria, settings = load_config(write_config(tmp_path, FULL_CONFIG))

    assert criteria.category == 'furniture-and-interior/furniture/wall-units'
    assert criteria.cities == frozenset({'Тирасполь', 'Бендеры'})
    assert criteria.keywords == ('шкаф', 'купе')
    assert (criteria.price_min, criteria.price_max, criteria.price_currency) == (50, 200, 'usd')
    assert (criteria.max_width_cm, criteria.max_height_cm, criteria.max_depth_cm) == (130, 230, 50)
    assert criteria.min_width_cm == 90
    assert criteria.max_pages == 2
    assert criteria.price_rates == {'usd': 16.3, 'eur': 19.16, 'lei': 0.96}
    assert (settings.check_interval_min_seconds, settings.check_interval_max_seconds) == (600, 1200)
    assert settings.notifier == 'telegram'
    assert (settings.telegram_bot_token, settings.telegram_chat_id) == ('T', 'C')


def test_minimal_config_applies_defaults(tmp_path):
    criteria, settings = load_config(write_config(tmp_path, '[search]\ncategory = "c"\n'))

    assert criteria.region == 'transnistria'
    assert criteria.language == 'ru'
    assert criteria.cities == frozenset()
    assert criteria.price_rates == {}
    assert criteria.max_pages == 1
    assert settings.notifier == 'console'
    assert settings.check_interval_min_seconds == 1200


def test_missing_category_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, '[search]\nregion = "transnistria"\n'))


def test_unknown_key_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, '[search]\ncategory = "c"\nmax_with_cm = 130\n'))


def test_rejects_non_positive_rate(tmp_path):
    config = '[search]\ncategory = "c"\n\n[search.price_rates]\nusd = 0\n'
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, config))


def test_rejects_non_numeric_rate(tmp_path):
    config = '[search]\ncategory = "c"\n\n[search.price_rates]\nusd = "16.3"\n'
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, config))


def test_rejects_inverted_dimension_range(tmp_path):
    config = '[search]\ncategory = "c"\nmin_width_cm = 150\nmax_width_cm = 130\n'
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, config))


def test_rejects_inverted_price_range(tmp_path):
    config = '[search]\ncategory = "c"\nprice_min = 9000\nprice_max = 8000\n'
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, config))


def test_blank_optional_strings_become_none(tmp_path):
    config = '[search]\ncategory = "c"\n\n[monitor]\nproxy = ""\ntelegram_bot_token = ""\n'
    _, settings = load_config(write_config(tmp_path, config))

    assert settings.proxy is None
    assert settings.telegram_bot_token is None
