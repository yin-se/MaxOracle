from __future__ import annotations

from typing import List, Tuple
from django.conf import settings

from .base import DrawRecord, ScrapeError
from .olg import OlgScraper
from .lotto8 import Lotto8Scraper
from .lotterypost import LotteryPostScraper

SCRAPERS = {
    'olg': OlgScraper,
    'lotto8': Lotto8Scraper,
    'lotterypost': LotteryPostScraper,
}


def get_enabled_scrapers() -> List[Tuple[str, object]]:
    config = settings.LOTTO_CONFIG.get('DATA_SOURCES', {})
    enabled = []
    for name, info in config.items():
        if not info.get('enabled', True):
            continue
        scraper_cls = SCRAPERS.get(name)
        if not scraper_cls:
            continue
        enabled.append((name, scraper_cls(info['past_results_url'])))
    return enabled


def fetch_draws(source: str = 'auto', max_pages: int | None = None) -> tuple[str, List[DrawRecord]]:
    enabled = get_enabled_scrapers()
    if not enabled:
        raise ScrapeError('No data sources configured', 'registry', 'Enable at least one source')

    if source != 'auto':
        for name, scraper in enabled:
            if name == source:
                return name, scraper.fetch_draws(max_pages=max_pages)
        raise ScrapeError('Requested source not configured', source, 'Check LOTTO_CONFIG')

    errors = []
    candidates: List[tuple[str, List[DrawRecord]]] = []
    for name, scraper in enabled:
        try:
            records = scraper.fetch_draws(max_pages=max_pages)
            candidates.append((name, records))
        except ScrapeError as exc:
            errors.append(exc)

    if not candidates:
        last_error = errors[-1]
        raise ScrapeError('All data sources failed', last_error.source, last_error.detail)

    # Choose the source with most draws, then most recent date.
    candidates.sort(key=lambda item: (len(item[1]), max(r.date for r in item[1])), reverse=True)
    return candidates[0]
