from datetime import date
from django.test import TestCase

from apps.lotto.models import Draw
from apps.lotto.services.analytics import compute_analysis, get_draws
from apps.lotto.services.recommender import RecommendationEngine, jaccard


class AnalyticsTests(TestCase):
    def setUp(self):
        Draw.objects.create(game='max', date=date(2025, 12, 30), numbers=[1, 2, 3, 4, 5, 6, 7], bonus=8, source_url='', hash='a')
        Draw.objects.create(game='max', date=date(2025, 12, 27), numbers=[10, 11, 12, 13, 14, 15, 16], bonus=17, source_url='', hash='b')

    def test_compute_analysis_counts(self):
        draws = get_draws(window=2, game='max')
        result = compute_analysis(draws, rolling_window=1)
        freq_map = {item['number']: item['count'] for item in result.main_frequency}
        assert freq_map[1] == 1
        assert freq_map[10] == 1
        assert result.meta['total_draws'] == 2


class RecommendationTests(TestCase):
    def setUp(self):
        for idx in range(1, 15):
            Draw.objects.create(
                game='max',
                date=date(2025, 1, idx),
                numbers=[idx, idx + 1, idx + 2, idx + 3, idx + 4, idx + 5, idx + 6],
                bonus=(idx + 7),
                source_url='',
                hash=str(idx),
            )

    def test_recommendations_valid(self):
        draws = list(Draw.objects.filter(game='max'))
        engine = RecommendationEngine(draws, seed='42')
        recs = engine.generate(count=3)
        assert recs
        for rec in recs:
            assert len(rec.numbers) == 7
            assert len(set(rec.numbers)) == 7
            assert all(1 <= n <= 50 for n in rec.numbers)
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                assert jaccard(set(recs[i].numbers), set(recs[j].numbers)) <= 0.6
