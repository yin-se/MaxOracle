from __future__ import annotations

import re
from datetime import date
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseScraper, DrawRecord, ScrapeError, logger

NUMBER_PATTERN = re.compile(r'\b\d+\b')
DATE_PATTERNS = [
    re.compile(r'\b\w+\s+\d{1,2},\s*\d{4}\b'),
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
]
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/123.0 Safari/537.36'
)


class LotteryPostScraper(BaseScraper):
    name = 'lotterypost'

    def __init__(self, base_url: str, game_config=None):
        super().__init__(base_url, game_config)
        parsed = urlparse(base_url)
        parts = [p for p in parsed.path.split('/') if p]
        self._path_hint = '/'.join(parts[-2:]) if len(parts) >= 2 else ''
        self._current_url: Optional[str] = None

    def fetch_draws(self, max_pages: int | None = None) -> List[DrawRecord]:
        html = self._fetch_html(self.base_url)
        self._current_url = self.base_url
        records = self.parse_draws(html)

        page_urls = self._extract_page_urls(html)
        if max_pages is not None:
            if max_pages <= 1:
                page_urls = []
            else:
                page_urls = page_urls[:max_pages - 1]

        for page_url in page_urls:
            try:
                page_html = self._fetch_html(page_url)
            except ScrapeError as exc:
                logger.warning('LotteryPost page fetch failed: %s', exc)
                continue
            self._current_url = page_url
            records.extend(self.parse_draws(page_html))

        deduped = {record.date: record for record in records}
        results = list(deduped.values())
        if not results:
            raise ScrapeError('No draws parsed from LotteryPost page', self.name, 'Check page structure')
        return results

    def parse_draws(self, html: str) -> List[DrawRecord]:
        soup = BeautifulSoup(html, 'html.parser')
        records: List[DrawRecord] = []

        rows = soup.select('tr')
        rows.extend(self._result_containers(soup))

        for row in rows:
            text = row.get_text(' ', strip=True)
            if not text:
                continue
            draw_date = self._extract_date(text)
            if not draw_date:
                continue
            numbers = self._extract_numbers(row, text)
            if len(numbers) < self.main_count:
                continue
            bonus = self._extract_bonus(row, numbers)
            if bonus is None:
                continue
            records.append(
                DrawRecord(
                    date=draw_date,
                    numbers=numbers[: self.main_count],
                    bonus=bonus,
                    source_url=self._current_url or self.base_url,
                )
            )

        return records

    def _fetch_html(self, url: str) -> str:
        try:
            response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
            if response.status_code == 200 and not self._is_blocked(response.text):
                return response.text
        except requests.RequestException as exc:
            logger.debug('LotteryPost request failed: %s', exc)

        logger.info('LotteryPost blocked, attempting browser fetch')
        return self._fetch_with_playwright(url)

    def _fetch_with_playwright(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScrapeError(
                'Playwright not installed',
                self.name,
                'Install with: pip install playwright && playwright install chromium',
            ) from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled'],
            )
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()

        if self._is_blocked(html):
            raise ScrapeError('LotteryPost blocked by Cloudflare', self.name, 'Browser fetch still blocked')
        return html

    def _is_blocked(self, html: str) -> bool:
        lowered = html.lower()
        return 'cloudflare' in lowered or 'just a moment' in lowered or 'attention required' in lowered

    def _result_containers(self, soup: BeautifulSoup) -> List[BeautifulSoup]:
        containers = []
        for div in soup.find_all('div', class_=True):
            classes = ' '.join(div.get('class', []))
            if 'result' in classes or 'draw' in classes:
                containers.append(div)
        return containers

    def _extract_numbers(self, row, text: str) -> List[int]:
        balls = []
        for node in row.select('.ball, .balls li, .results__ball, .result__ball, .number'):
            value = node.get_text(strip=True)
            if value.isdigit():
                balls.append(int(value))
        if len(balls) >= self.main_count:
            return [n for n in balls if 1 <= n <= self.max_number]
        return [int(n) for n in NUMBER_PATTERN.findall(text) if 1 <= int(n) <= self.max_number]

    def _extract_bonus(self, row, numbers: List[int]) -> Optional[int]:
        bonus_nodes = row.select('.bonus, .ball.bonus, .results__bonus')
        for node in bonus_nodes:
            value = node.get_text(strip=True)
            if value.isdigit():
                return int(value)
        return numbers[self.main_count] if len(numbers) >= self.main_count + 1 else None

    def _extract_date(self, text: str) -> Optional[date]:
        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                return self._parse_date(match.group(0))
        return None

    def _parse_date(self, text: str) -> Optional[date]:
        try:
            return date_parser.parse(text, fuzzy=True, dayfirst=False).date()
        except (ValueError, TypeError) as exc:
            logger.debug('LotteryPost date parse failed for %s: %s', text, exc)
            return None

    def _extract_page_urls(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        urls = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if self._path_hint and self._path_hint not in href:
                continue
            if href.startswith('/'):
                href = f"https://www.lotterypost.com{href}"
            if 'page=' in href or href.rstrip('/').split('/')[-1].isdigit():
                urls.add(href)
        urls.discard(self.base_url)
        return sorted(urls)
