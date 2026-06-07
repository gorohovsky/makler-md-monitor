"""Site-wide constants and default settings shared across modules."""

BASE_URL = 'https://makler.md'

# makler.md serves the same listings under /ru, /ro and /en path prefixes.
# Only the Russian locale is in scope for this project.
DEFAULT_LANGUAGE = 'ru'

# Region and city are both encoded as the first path segment after the language:
#   /ru/transnistria/...  -> a region (data-type="region")
#   /ru/tiraspol/...      -> a city   (data-type="city")
# "transnistria" is Приднестровье / Prednistrovie — the project default region.
DEFAULT_REGION = 'transnistria'

# Safety cap on pages scanned per check. Scanning stops earlier — at the first page with
# no new listings — since listings are newest-first, so once a page is fully seen the rest
# are too. This caps the first run and any runaway; steady state usually stops after page 1.
DEFAULT_MAX_PAGES = 5

# Anti-detection HTTP client defaults.
DEFAULT_MIN_DELAY_SECONDS = 3.0
DEFAULT_MAX_DELAY_SECONDS = 8.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3

# Monitor scheduling: each wait is drawn uniformly from this window so the polling
# cadence is not a fixed, fingerprintable interval.
DEFAULT_CHECK_INTERVAL_MIN_SECONDS = 1200
DEFAULT_CHECK_INTERVAL_MAX_SECONDS = 2400
