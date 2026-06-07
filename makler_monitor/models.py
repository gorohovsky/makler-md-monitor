"""Immutable domain models passed between layers."""

from dataclasses import dataclass, field

from .constants import (
    DEFAULT_CHECK_INTERVAL_MAX_SECONDS,
    DEFAULT_CHECK_INTERVAL_MIN_SECONDS,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_DELAY_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGES_PER_BATCH,
    DEFAULT_MIN_DELAY_SECONDS,
    DEFAULT_REGION,
    DEFAULT_REQUEST_TIMEOUT_SECONDS
)


@dataclass(frozen=True)
class Dimensions:
    """Physical size extracted from free-text, normalised to centimetres."""

    width_cm: float | None = None
    height_cm: float | None = None
    depth_cm: float | None = None

    @property
    def is_empty(self) -> bool:
        return self.width_cm is None and self.height_cm is None and self.depth_cm is None


@dataclass(frozen=True)
class Listing:
    """A single classified announcement."""

    listing_id: str
    title: str
    url: str
    price: float | None = None
    currency: str | None = None
    city: str | None = None
    posted_at: str | None = None
    snippet: str = ''
    description: str | None = None
    image_url: str | None = None
    dimensions: Dimensions = field(default_factory=Dimensions)

    @property
    def description_text(self) -> str:
        """Full description when fetched, otherwise the listing-card snippet."""
        return self.description or self.snippet


@dataclass(frozen=True)
class SearchCriteria:
    """What the user is looking for. Drives both URL building and filtering."""

    category: str
    region: str = DEFAULT_REGION
    language: str = DEFAULT_LANGUAGE
    cities: frozenset[str] = frozenset()
    keywords: tuple[str, ...] = ()
    price_min: float | None = None
    price_max: float | None = None
    price_currency: str | None = None
    price_rates: dict[str, float] = field(default_factory=dict)
    min_width_cm: float | None = None
    max_width_cm: float | None = None
    min_height_cm: float | None = None
    max_height_cm: float | None = None
    min_depth_cm: float | None = None
    max_depth_cm: float | None = None
    unknown_dimension_ok: bool = True
    pages_per_batch: int = DEFAULT_PAGES_PER_BATCH
    max_pages: int | None = None


@dataclass(frozen=True)
class MonitorSettings:
    """Runtime/infrastructure configuration, separate from search intent."""

    check_interval_min_seconds: float = DEFAULT_CHECK_INTERVAL_MIN_SECONDS
    check_interval_max_seconds: float = DEFAULT_CHECK_INTERVAL_MAX_SECONDS
    state_path: str = 'seen.json'
    min_delay_seconds: float = DEFAULT_MIN_DELAY_SECONDS
    max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    proxy: str | None = None
    notifier: str = 'console'
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
