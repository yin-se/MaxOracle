from pathlib import Path
from django.test import SimpleTestCase

from apps.lotto.services.scrapers.lotto8 import Lotto8Scraper
from apps.lotto.services.scrapers.lotterypost import LotteryPostScraper


class Lotto8ScraperTests(SimpleTestCase):
    def test_parse_sample_html(self):
        html = Path(__file__).parent / 'fixtures' / 'lotto8_sample.html'
        scraper = Lotto8Scraper('https://example.com')
        records = scraper.parse_draws(html.read_text(encoding='utf-8'))
        assert len(records) == 2
        assert records[0].date.isoformat() == '2025-12-30'
        assert records[0].numbers == [5, 21, 32, 38, 43, 44, 45]
        assert records[0].bonus == 49


class LotteryPostScraperTests(SimpleTestCase):
    def test_parse_sample_html(self):
        html = Path(__file__).parent / 'fixtures' / 'lotterypost_sample.html'
        scraper = LotteryPostScraper('https://example.com')
        records = scraper.parse_draws(html.read_text(encoding='utf-8'))
        assert len(records) == 1
        assert records[0].date.isoformat() == '2009-09-25'
        assert records[0].numbers == [1, 2, 3, 4, 5, 6, 7]
        assert records[0].bonus == 8
