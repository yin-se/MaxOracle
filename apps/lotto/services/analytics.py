from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from typing import List, Optional

from ..models import Draw


@dataclass
class AnalysisResult:
    meta: dict
    main_frequency: list
    bonus_frequency: list
    omissions: list
    hot_numbers: list
    cold_numbers: list
    pair_frequency: list
    triplet_frequency: list
    odd_even_distribution: list
    size_distribution: list
    sum_distribution: list
    span_distribution: list
    consecutive_ratio: dict
    rolling_series: dict


def get_draws(window: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Draw]:
    qs = Draw.objects.all().order_by('-date')
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if window:
        qs = qs[:window]
    return list(qs)


def compute_analysis(draws: List[Draw], rolling_window: int = 100, top_pairs: int = 15, top_triplets: int = 15) -> AnalysisResult:
    total_draws = len(draws)
    main_counts: Counter[int] = Counter()
    bonus_counts: Counter[int] = Counter()
    sums = []
    spans = []
    odd_even_counts = Counter()
    size_counts = Counter()
    consecutive_hits = 0

    for draw in draws:
        numbers = sorted(draw.numbers)
        main_counts.update(numbers)
        bonus_counts.update([draw.bonus])
        draw_sum = sum(numbers)
        sums.append(draw_sum)
        spans.append(numbers[-1] - numbers[0])
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        odd_even_counts[odd_count] += 1
        small_count = sum(1 for n in numbers if n <= 25)
        size_counts[small_count] += 1
        if any(b - a == 1 for a, b in zip(numbers, numbers[1:])):
            consecutive_hits += 1

    total_main_numbers = total_draws * 7 if total_draws else 1
    main_frequency = [
        {
            'number': num,
            'count': main_counts.get(num, 0),
            'probability': round(main_counts.get(num, 0) / total_main_numbers, 6),
        }
        for num in range(1, 51)
    ]
    bonus_frequency = [
        {
            'number': num,
            'count': bonus_counts.get(num, 0),
            'probability': round(bonus_counts.get(num, 0) / max(total_draws, 1), 6),
        }
        for num in range(1, 51)
    ]

    omissions = _compute_omissions(draws)
    hot_numbers = sorted(main_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    cold_numbers = sorted(omissions, key=lambda item: item['omission'], reverse=True)[:10]

    pair_frequency = _compute_combinations(draws, 2, top_pairs)
    triplet_frequency = _compute_combinations(draws, 3, top_triplets)

    odd_even_distribution = [
        {'odd_count': odd, 'count': odd_even_counts.get(odd, 0)}
        for odd in range(0, 8)
    ]
    size_distribution = [
        {'small_count': small, 'count': size_counts.get(small, 0)}
        for small in range(0, 8)
    ]

    sum_distribution = _build_histogram(sums, bin_size=10)
    span_distribution = _build_histogram(spans, bin_size=5)

    consecutive_ratio = {
        'ratio': round(consecutive_hits / max(total_draws, 1), 4),
        'count': consecutive_hits,
        'total': total_draws,
    }

    rolling_series = _compute_rolling_series(draws, rolling_window)

    meta = {
        'total_draws': total_draws,
        'latest_draw': draws[0].date.isoformat() if draws else None,
        'window': total_draws,
        'rolling_window': rolling_window,
    }

    return AnalysisResult(
        meta=meta,
        main_frequency=main_frequency,
        bonus_frequency=bonus_frequency,
        omissions=omissions,
        hot_numbers=hot_numbers,
        cold_numbers=cold_numbers,
        pair_frequency=pair_frequency,
        triplet_frequency=triplet_frequency,
        odd_even_distribution=odd_even_distribution,
        size_distribution=size_distribution,
        sum_distribution=sum_distribution,
        span_distribution=span_distribution,
        consecutive_ratio=consecutive_ratio,
        rolling_series=rolling_series,
    )


def _compute_omissions(draws: List[Draw]) -> list:
    latest_index = {num: None for num in range(1, 51)}
    for idx, draw in enumerate(draws):
        for number in draw.numbers:
            if latest_index[number] is None:
                latest_index[number] = idx
    omissions = []
    for num in range(1, 51):
        omission = latest_index[num] if latest_index[num] is not None else len(draws)
        omissions.append({'number': num, 'omission': omission})
    return omissions


def _compute_combinations(draws: List[Draw], size: int, top_n: int) -> list:
    counter: Counter[tuple] = Counter()
    for draw in draws:
        for combo in combinations(sorted(draw.numbers), size):
            counter[combo] += 1
    return [
        {'numbers': list(combo), 'count': count}
        for combo, count in counter.most_common(top_n)
    ]


def _build_histogram(values: List[int], bin_size: int) -> list:
    if not values:
        return []
    min_value = min(values)
    max_value = max(values)
    bins = list(range(min_value - (min_value % bin_size), max_value + bin_size, bin_size))
    counts = Counter()
    for value in values:
        bucket = (value // bin_size) * bin_size
        counts[bucket] += 1
    return [
        {'bin_start': b, 'count': counts.get(b, 0)}
        for b in bins
    ]


def _compute_rolling_series(draws: List[Draw], window: int) -> dict:
    if not draws:
        return {'labels': [], 'series': []}

    chrono_draws = list(sorted(draws, key=lambda d: d.date))
    main_counts = Counter()
    for draw in draws:
        main_counts.update(draw.numbers)
    top_numbers = [num for num, _ in main_counts.most_common(5)]

    prefix = {num: [] for num in top_numbers}
    counts = {num: 0 for num in top_numbers}
    for draw in chrono_draws:
        for num in top_numbers:
            counts[num] += 1 if num in draw.numbers else 0
            prefix[num].append(counts[num])

    labels = [draw.date.isoformat() for draw in chrono_draws]
    series = []
    for num in top_numbers:
        data_points = []
        for idx in range(len(chrono_draws)):
            start_idx = idx - window
            window_total = prefix[num][idx] - (prefix[num][start_idx] if start_idx >= 0 else 0)
            data_points.append(window_total / max(window, 1))
        series.append({'number': num, 'values': data_points})

    return {'labels': labels, 'series': series}
