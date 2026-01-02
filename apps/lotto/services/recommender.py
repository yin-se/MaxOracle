from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import List, Tuple

from .analytics import _compute_omissions
from ..models import Draw


@dataclass
class Recommendation:
    numbers: List[int]
    odd_count: int
    even_count: int
    small_count: int
    large_count: int
    total_sum: int
    hot_count: int
    cold_count: int
    pair_boost: int
    explanation: List[str]


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(len(a | b), 1)


class RecommendationEngine:
    def __init__(self, draws: List[Draw], seed: str | None = None):
        self.draws = draws
        self.random = random.Random(seed)
        self.main_counts = Counter()
        for draw in draws:
            self.main_counts.update(draw.numbers)

        omissions = _compute_omissions(draws)
        self.hot_numbers = [num for num, _ in self.main_counts.most_common(10)]
        self.cold_numbers = [item['number'] for item in sorted(omissions, key=lambda i: i['omission'], reverse=True)[:10]]
        if not self.hot_numbers:
            self.hot_numbers = list(range(1, 11))
        if not self.cold_numbers:
            self.cold_numbers = list(range(41, 51))
        self.neutral_pool = [n for n in range(1, 51) if n not in set(self.hot_numbers + self.cold_numbers)]

        odd_counts = [sum(1 for n in draw.numbers if n % 2 == 1) for draw in draws]
        size_counts = [sum(1 for n in draw.numbers if n <= 25) for draw in draws]
        sums = [sum(draw.numbers) for draw in draws]

        self.target_odd = _mode(odd_counts) if odd_counts else 3
        self.target_small = _mode(size_counts) if size_counts else 3
        self.sum_range = _percentile_range(sums, 0.25, 0.75) if sums else (60, 240)
        self.common_pairs = _top_pairs(draws, top_n=15)

    def generate(self, count: int = 5, max_similarity: float = 0.4) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        attempts = 0
        while len(recommendations) < count and attempts < count * 300:
            attempts += 1
            numbers = self._build_candidate()
            if not self._passes_constraints(numbers):
                continue
            if any(jaccard(set(numbers), set(rec.numbers)) > max_similarity for rec in recommendations):
                continue
            recommendations.append(self._build_recommendation(numbers))
        return recommendations

    def _build_candidate(self) -> List[int]:
        selection = set()
        hot_pick = min(3, len(self.hot_numbers))
        cold_pick = min(2, len(self.cold_numbers))
        if hot_pick:
            selection.update(self.random.sample(self.hot_numbers, hot_pick))
        cold_candidates = [n for n in self.cold_numbers if n not in selection]
        if cold_pick and len(cold_candidates) >= cold_pick:
            selection.update(self.random.sample(cold_candidates, cold_pick))

        # Encourage one common pair when possible
        if self.common_pairs:
            pair = self.random.choice(self.common_pairs)
            selection.update(pair)

        pool = [n for n in range(1, 51) if n not in selection]
        while len(selection) < 7:
            selection.add(self.random.choice(pool))
        return sorted(selection)

    def _passes_constraints(self, numbers: List[int]) -> bool:
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        small_count = sum(1 for n in numbers if n <= 25)
        total_sum = sum(numbers)
        if abs(odd_count - self.target_odd) > 2:
            return False
        if abs(small_count - self.target_small) > 2:
            return False
        if not (self.sum_range[0] <= total_sum <= self.sum_range[1]):
            return False
        hot_count = sum(1 for n in numbers if n in self.hot_numbers)
        cold_count = sum(1 for n in numbers if n in self.cold_numbers)
        if self.hot_numbers and hot_count < 1:
            return False
        if self.cold_numbers and cold_count < 1:
            return False
        return True

    def _build_recommendation(self, numbers: List[int]) -> Recommendation:
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        even_count = 7 - odd_count
        small_count = sum(1 for n in numbers if n <= 25)
        large_count = 7 - small_count
        total_sum = sum(numbers)
        hot_count = sum(1 for n in numbers if n in self.hot_numbers)
        cold_count = sum(1 for n in numbers if n in self.cold_numbers)
        pair_boost = sum(1 for pair in self.common_pairs if set(pair).issubset(numbers))

        explanation = [
            f"热号 {hot_count} 个 + 冷号 {cold_count} 个的平衡组合",
            f"奇偶比 {odd_count}:{7 - odd_count} 接近历史常见区间",
            f"大小比 {small_count}:{7 - small_count} 与历史分布一致",
            f"和值 {total_sum} 落在常见区间 {self.sum_range[0]}-{self.sum_range[1]}",
        ]
        if pair_boost:
            explanation.append("包含历史高共现号码对")

        return Recommendation(
            numbers=numbers,
            odd_count=odd_count,
            even_count=even_count,
            small_count=small_count,
            large_count=large_count,
            total_sum=total_sum,
            hot_count=hot_count,
            cold_count=cold_count,
            pair_boost=pair_boost,
            explanation=explanation,
        )


def _mode(values: List[int]) -> int:
    if not values:
        return 3
    counts = Counter(values)
    return counts.most_common(1)[0][0]


def _percentile_range(values: List[int], low: float, high: float) -> Tuple[int, int]:
    sorted_values = sorted(values)
    if not sorted_values:
        return 60, 240
    low_idx = int(len(sorted_values) * low)
    high_idx = int(len(sorted_values) * high) - 1
    low_value = sorted_values[max(low_idx, 0)]
    high_value = sorted_values[max(high_idx, 0)]
    return low_value, high_value


def _top_pairs(draws: List[Draw], top_n: int = 10) -> List[Tuple[int, int]]:
    counter = Counter()
    for draw in draws:
        for combo in combinations(sorted(draw.numbers), 2):
            counter[combo] += 1
    return [pair for pair, _ in counter.most_common(top_n)]
