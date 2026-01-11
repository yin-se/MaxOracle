from __future__ import annotations

import re
from datetime import date
from typing import List

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseScraper, DrawRecord, ScrapeError, logger

NUMBER_PATTERN = re.compile(r'\d+')
DATE_PATTERN = re.compile(r'(\d{2}/\d{2}\s+\d{2}|\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2})')


class Lotto8Scraper(BaseScraper):
    name = 'lotto8'

    def fetch_draws(self, max_pages: int | None = None) -> List[DrawRecord]:
        html = self._get(self.base_url)
        max_index = self._extract_max_index(html)
        if max_pages is not None:
            max_index = min(max_index, max_pages)
        fallback_mode = False
        if max_index <= 1 and max_pages is None:
            max_index = 60
            fallback_mode = True

        records = self.parse_draws(html)
        seen_dates = {record.date for record in records}
        for page in range(2, max_index + 1):
            page_url = f"{self.base_url}?indexpage={page}&orderby=new"
            try:
                page_html = self._get(page_url)
            except ScrapeError as exc:
                logger.warning('Failed to fetch page %s: %s', page, exc)
                continue
            page_records = self.parse_draws(page_html)
            new_records = [record for record in page_records if record.date not in seen_dates]
            if not new_records and fallback_mode:
                break
            records.extend(new_records)
            for record in new_records:
                seen_dates.add(record.date)

        deduped = {record.date: record for record in records}
        results = list(deduped.values())
        if not results:
            raise ScrapeError('No draws parsed from Lotto-8 page', self.name, 'Check table structure')
        return results

    def parse_draws(self, html: str) -> List[DrawRecord]:
        soup = BeautifulSoup(html, 'html.parser')
        records: List[DrawRecord] = []
        for row in soup.find_all('tr'):
            cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) < 3:
                continue
            draw_date = self._parse_date(cells[0])
            numbers = self._extract_numbers(cells[1])
            bonus_values = self._extract_numbers(cells[2])
            if not draw_date or len(numbers) < self.main_count or not bonus_values:
                continue
            record = DrawRecord(
                date=draw_date,
                numbers=numbers[: self.main_count],
                bonus=bonus_values[0],
                source_url=self.base_url,
            )
            records.append(record)

        return records

    def _parse_date(self, text: str) -> date | None:
        text = text.replace('\xa0', ' ').strip()
        match = DATE_PATTERN.search(text)
        if match:
            value = match.group(0)
            if ' ' in value and len(value.split()) == 2 and '/' in value:
                # Format like 30/12 25
                day, month = value.split()[0].split('/')
                year = value.split()[1]
                year_full = int(year) + (2000 if int(year) < 70 else 1900)
                try:
                    return date(year_full, int(month), int(day))
                except ValueError as exc:
                    logger.debug('Invalid date parts %s: %s', value, exc)
                    return None
        try:
            return date_parser.parse(text, dayfirst=True, fuzzy=True).date()
        except (ValueError, TypeError) as exc:
            logger.debug('Failed to parse date from %s: %s', text, exc)
            return None

    def _extract_numbers(self, text: str) -> List[int]:
        numbers = []
        for value in NUMBER_PATTERN.findall(text):
            try:
                number = int(value)
            except ValueError:
                continue
            if 1 <= number <= self.max_number:
                numbers.append(number)
        return numbers

    def _extract_max_index(self, html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        max_index = 1
        for link in soup.find_all('a', href=True):
            href = link['href']
            match = re.search(r'indexpage=(\d+)', href)
            if match:
                max_index = max(max_index, int(match.group(1)))
        return max_index
