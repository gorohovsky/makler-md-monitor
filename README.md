# makler-monitor

Monitor [makler.md](https://makler.md) classifieds and get notified when a **new** listing
appears that matches criteria the site itself cannot filter on:

- **Dimensions** (width / height / depth) parsed from the free-text description — makler.md
  has no size fields, so this is the main reason the tool exists.
- **Price range** in a chosen currency (prices in other currencies are converted via rates).
- **City** (multi-select) within a region.
- **Keywords** in the title or description.

The region defaults to **Приднестровье / Transnistria** and the site language is Russian.

## How it works

Each check scans the category newest-first, page by page, until it reaches a page with no
new listings; it drops those in the wrong city or outside the price range, then opens the detail page of each
remaining candidate to read the full description, parse its dimensions, and apply the
keyword and size filters. New matches go to your notifier and are remembered, so you are
notified only once.

To stay below the site's radar it behaves like a real browser: one randomly chosen browser
profile per run (User-Agent + matching client hints), Russian-locale headers, reused
cookies, a random human pause before every request, exponential backoff on errors, and — in
`watch` mode — a **randomised** delay between checks rather than a fixed, fingerprintable
interval. Detail pages are fetched only for listings that already pass the city/price
filters, which keeps the request volume low.

| Module | Responsibility |
|--------|----------------|
| `dimensions.py` | parse width/height/depth from Russian free text |
| `parser.py` | makler.md HTML → `Listing`, price/currency |
| `urls.py` | build category-page URLs |
| `filters.py` | price / city / keyword / dimension predicates |
| `client.py` | browser-like HTTP client (anti-detection, retries) |
| `catalog.py` | pages → `Listing`s |
| `storage.py` | remember seen listing IDs |
| `notifier.py` | console / Telegram delivery |
| `monitor.py` | one check cycle |
| `config.py`, `cli.py` | TOML config and command line |

## Requirements

- [uv](https://docs.astral.sh/uv/) — manages the Python version and dependencies.
  Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Deployment

```bash
git clone https://github.com/gorohovsky/makler-md-monitor.git && cd makler-md-monitor
uv sync                        # create .venv and install dependencies (reproducible via uv.lock)
cp config.example.toml config.toml
$EDITOR config.toml            # set your category, filters and notifier
```

`config.toml` is gitignored because it can hold a Telegram token.

## Configuration

Edit `config.toml`; `config.example.toml` documents every option. There are two sections:
`[search]` (what to look for) and `[monitor]` (how to run).

To set `category`, browse makler.md to the category you want and copy the URL part after the
language and region, e.g. for
`https://makler.md/ru/transnistria/furniture-and-interior/furniture/wall-units`:

```toml
[search]
category = "furniture-and-interior/furniture/wall-units"
region = "transnistria"            # Приднестровье (default)
cities = ["Тирасполь", "Бендеры"]  # optional; exact Russian names from the site
keywords = ["шкаф", "купе"]        # optional
price_max = 8000
price_currency = "rub"             # rub | usd | eur | lei
min_width_cm = 90                  # each axis takes a min, a max, or both (a range)
max_width_cm = 130
max_height_cm = 230
max_depth_cm = 50

# convert other-currency prices into price_currency (price_currency per 1 unit):
[search.price_rates]
usd = 16.3
eur = 19.16
lei = 0.96
```

Invalid config is rejected at startup with a clear message — a non-positive or non-numeric
`price_rates` entry, or a `min_*` greater than its `max_*` (or `price_min > price_max`).

Discover the city names available in your category/region:

```bash
uv run python -m makler_monitor list-cities
```

and copy the exact names it prints into `cities = [...]`.

## Usage

```bash
# check once now and print matches (good for cron)
uv run python -m makler_monitor check

# keep watching, re-checking on a randomised 20–40 min interval
uv run python -m makler_monitor watch

# list cities currently present in the configured category/region
uv run python -m makler_monitor list-cities

# use a different config file
uv run python -m makler_monitor watch --config other.toml
```

The first run reports every current match and remembers those listings; later runs report
only newly-posted ones.

### Running continuously

Either keep `watch` running (under `tmux`, `nohup`, or a `systemd` service), or schedule
`check` with cron. `watch` randomises the gap between checks itself; with cron, rely on the
per-request delays and avoid a perfectly round schedule.

## Telegram notifications

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.
2. Message [@userinfobot](https://t.me/userinfobot) to get your numeric chat id.
3. In `config.toml`:
   ```toml
   [monitor]
   notifier = "telegram"
   telegram_bot_token = "123456:ABC-DEF..."
   telegram_chat_id = "987654321"
   ```

Leave `notifier = "console"` to simply print matches to the terminal.

## Notes and limitations

- **Currency**: listings use different currencies (rub/usd/eur/lei). Set `[search.price_rates]`
  (price_currency units per 1 unit of each other currency) and the filter converts
  foreign-priced listings into your `price_currency` before checking the range; a currency
  with no configured rate is skipped. Rates are static — update them occasionally.
- **Dimensions** come from free text, so parsing is best-effort. Labelled values
  (`ширина 120 см`) are used as-is; an unlabelled `120x220x50` triple is assigned by size
  (largest = height, smallest = depth, middle = width), since the written order varies — this
  suits tall, shallow furniture but can mislabel low, wide pieces. A unit-less value below
  10 is read as metres (`высота 2` → 200 cm, `высота 2.30` → 230 cm), since no furniture
  dimension is a few centimetres. By default a listing is not rejected for an
  axis the seller never stated (set `unknown_dimension_ok = false` to require every limit).
  Each axis takes a `max_*_cm`, a `min_*_cm`, or both for a range.
- **Rate limiting**: if results suddenly come back empty, the site may be throttling — raise
  the delays in `[monitor]` or set a `proxy`.

## Development

```bash
uv run pytest
```

The suite is fully offline: HTML parsing runs against saved fixtures and the HTTP client is
tested with a fake session, so no test touches the network.
