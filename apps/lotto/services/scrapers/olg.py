from __future__ import annotations

import json
import re
from datetime import date
from typing import List

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseScraper, DrawRecord, ScrapeError, logger

NUMBER_PATTERN = re.compile(r'\b([1-9]|[1-4][0-9]|50)\b')
DATE_PATTERNS = [
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
    re.compile(r'\b\w+\s+\d{1,2},\s*\d{4}\b'),
]


class OlgScraper(BaseScraper):
    name = 'olg'

    def fetch_draws(self, max_pages: int | None = None) -> List[DrawRecord]:
        html = self._get(self.base_url)
        return self.parse_draws(html)

    def parse_draws(self, html: str) -> List[DrawRecord]:
        soup = BeautifulSoup(html, 'html.parser')
        draws: List[DrawRecord] = []
        draws.extend(self._parse_json_blocks(soup))
        draws.extend(self._parse_table_rows(soup))

        deduped = {draw.date: draw for draw in draws}
        results = list(deduped.values())
        if not results:
            raise ScrapeError('No draws parsed from OLG page', self.name, 'Check page structure')
        return results

    def _parse_json_blocks(self, soup: BeautifulSoup) -> List[DrawRecord]:
        records: List[DrawRecord] = []
        scripts = soup.find_all('script')
        for script in scripts:
            content = script.string
            if not content:
                continue
            if 'drawDate' not in content and 'winningNumbers' not in content:
                continue
            for payload in self._extract_json_candidates(content):
                records.extend(self._extract_from_json(payload))
        return records

    def _extract_json_candidates(self, content: str) -> List[object]:
        candidates: List[object] = []
        try:
            if content.strip().startswith('{'):
                candidates.append(json.loads(content))
        except json.JSONDecodeError:
            pass
        # Try to find JSON objects inside the script
        for match in re.finditer(r'(\{.*\})', content):
            snippet = match.group(1)
            try:
                candidates.append(json.loads(snippet))
            except json.JSONDecodeError:
                continue
        return candidates

    def _extract_from_json(self, data: object) -> List[DrawRecord]:
        records: List[DrawRecord] = []
        if isinstance(data, dict):
            if 'drawDate' in data and ('winningNumbers' in data or 'numbers' in data or 'mainNumbers' in data):
                record = self._record_from_mapping(data)
                if record:
                    records.append(record)
            for value in data.values():
                records.extend(self._extract_from_json(value))
        elif isinstance(data, list):
            for item in data:
                records.extend(self._extract_from_json(item))
        return records

    def _record_from_mapping(self, data: dict) -> DrawRecord | None:
        date_value = data.get('drawDate') or data.get('date')
        numbers_value = data.get('winningNumbers') or data.get('numbers') or data.get('mainNumbers')
        bonus_value = data.get('bonusNumber') or data.get('bonus') or data.get('bonusNumberValue')

        if not date_value or not numbers_value or bonus_value is None:
            return None

        draw_date = self._parse_date(str(date_value))
        numbers = self._parse_numbers(numbers_value)
        bonus = int(bonus_value)
        if draw_date is None or not numbers:
            return None
        return DrawRecord(date=draw_date, numbers=numbers, bonus=bonus, source_url=self.base_url)

    def _parse_table_rows(self, soup: BeautifulSoup) -> List[DrawRecord]:
        records: List[DrawRecord] = []
        for row in soup.select('table tr'):
            row_text = row.get_text(' ', strip=True)
            if not row_text:
                continue
            draw_date = self._extract_date_from_text(row_text)
            if not draw_date:
                continue
            numbers = [int(m) for m in NUMBER_PATTERN.findall(row_text)]
            if len(numbers) < 8:
                continue
            record = DrawRecord(
                date=draw_date,
                numbers=numbers[:7],
                bonus=numbers[7],
                source_url=self.base_url,
            )
            records.append(record)
        return records

    def _extract_date_from_text(self, text: str) -> date | None:
        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            return self._parse_date(match.group(0))
        return None

    def _parse_date(self, text: str) -> date | None:
        try:
            return date_parser.parse(text, fuzzy=True).date()
        except (ValueError, TypeError) as exc:
            logger.debug('Failed to parse date from %s: %s', text, exc)
            return None

    def _parse_numbers(self, value: object) -> List[int]:
        if isinstance(value, list):
            return [int(n) for n in value if str(n).isdigit()]
        if isinstance(value, str):
            return [int(n) for n in NUMBER_PATTERN.findall(value)]
        return []
