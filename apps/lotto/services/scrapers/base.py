from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List
import logging
import requests

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0 Safari/537.36'
    ),
}

logger = logging.getLogger('lotto')


class ScrapeError(RuntimeError):
    def __init__(self, message: str, source: str, detail: str | None = None):
        super().__init__(message)
        self.source = source
        self.detail = detail or ''


@dataclass(frozen=True)
class DrawRecord:
    date: date
    numbers: List[int]
    bonus: int
    source_url: str


class BaseScraper:
    name = 'base'

    def __init__(self, base_url: str, game_config=None):
        self.base_url = base_url
        self.main_count = getattr(game_config, 'main_count', 7)
        self.max_number = getattr(game_config, 'max_number', 50)

    def fetch_draws(self, max_pages: int | None = None) -> List[DrawRecord]:
        html = self._get(self.base_url)
        return self.parse_draws(html)

    def parse_draws(self, html: str) -> List[DrawRecord]:
        raise NotImplementedError

    def _get(self, url: str) -> str:
        logger.info('Fetching %s from %s', self.name, url)
        try:
            response = requests.get(url, timeout=20, headers=DEFAULT_HEADERS)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ScrapeError('Failed to fetch data', self.name, str(exc)) from exc
        return response.text
