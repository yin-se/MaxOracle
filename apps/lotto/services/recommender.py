from __future__ import annotations

import random
import hashlib
import math
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
    algorithm: str
    algorithm_label: str
    algorithm_summary: str


def _lang_text(lang: str, zh: str, en: str) -> str:
    return en if lang == 'en' else zh


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(len(a | b), 1)


class RecommendationEngine:
    def __init__(self, draws: List[Draw], seed: str | None = None, lang: str = 'zh'):
        self.draws = draws
        self.random = random.Random(seed)
        self.lang = 'en' if lang == 'en' else 'zh'
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

    def build_recommendation(
        self,
        numbers: List[int],
        algorithm: str,
        algorithm_label: str | None = None,
        summary: str | None = None,
        explanation: List[str] | None = None,
        lang: str | None = None,
    ) -> Recommendation:
        return self._build_recommendation(numbers, algorithm, algorithm_label, summary, explanation, lang)

    def _build_recommendation(
        self,
        numbers: List[int],
        algorithm: str = 'BalancedHotColdMix',
        algorithm_label: str | None = None,
        summary: str | None = None,
        explanation: List[str] | None = None,
        lang: str | None = None,
    ) -> Recommendation:
        lang = 'en' if (lang or self.lang) == 'en' else 'zh'
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        even_count = 7 - odd_count
        small_count = sum(1 for n in numbers if n <= 25)
        large_count = 7 - small_count
        total_sum = sum(numbers)
        hot_count = sum(1 for n in numbers if n in self.hot_numbers)
        cold_count = sum(1 for n in numbers if n in self.cold_numbers)
        pair_boost = sum(1 for pair in self.common_pairs if set(pair).issubset(numbers))

        if algorithm_label is None:
            algorithm_label = _lang_text(lang, '热冷平衡综合策略', 'Balanced Hot/Cold Mix')
        if summary is None:
            summary = _lang_text(
                lang,
                '热冷平衡 + 结构约束 + 高频共现组合',
                'Hot/cold balance + structure constraints + common pairs',
            )
        if explanation is None:
            explanation = [
                _lang_text(
                    lang,
                    f"热号 {hot_count} 个 + 冷号 {cold_count} 个的平衡组合",
                    f"Balanced {hot_count} hot + {cold_count} cold numbers",
                ),
                _lang_text(
                    lang,
                    f"奇偶比 {odd_count}:{even_count} 接近历史常见区间",
                    f"Odd-even ratio {odd_count}:{even_count} within typical range",
                ),
                _lang_text(
                    lang,
                    f"大小比 {small_count}:{large_count} 与历史分布一致",
                    f"Low-high ratio {small_count}:{large_count} matches history",
                ),
                _lang_text(
                    lang,
                    f"和值 {total_sum} 落在常见区间 {self.sum_range[0]}-{self.sum_range[1]}",
                    f"Sum {total_sum} within typical band {self.sum_range[0]}-{self.sum_range[1]}",
                ),
            ]
            if pair_boost:
                explanation.append(_lang_text(lang, '包含历史高共现号码对', 'Includes historically common pairs'))

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
            algorithm=algorithm,
            algorithm_label=algorithm_label,
            algorithm_summary=summary,
        )


def build_recommendations(draws: List[Draw], seed: str | None = None, lang: str = 'zh') -> List[Recommendation]:
    if not draws:
        return []

    lang = 'en' if lang == 'en' else 'zh'
    engine = RecommendationEngine(draws, seed=seed, lang=lang)
    recommendations: List[Recommendation] = []

    balanced = engine.generate(count=1)
    if balanced:
        recommendations.append(balanced[0])

    counts = engine.main_counts
    freq_numbers = _top_numbers(counts, 7)
    recommendations.append(
        engine.build_recommendation(
            freq_numbers,
            algorithm='PureFrequencyTop7',
            algorithm_label=_lang_text(lang, '高频直选 Top7', 'Pure Frequency Top 7'),
            summary=_lang_text(lang, '仅按历史出现频率取前 7 个号码', 'Top 7 by historical frequency only'),
            explanation=[
                _lang_text(lang, '统计所有历史主号出现次数，按频次降序取前 7 个', 'Count main-number frequencies and take the top 7'),
                _lang_text(lang, '不做平滑、结构约束或随机扰动', 'No smoothing, structure constraints, or randomization'),
            ],
        )
    )

    draw_numbers = _draw_numbers(draws)
    rng = _seeded_random(seed, 'algorithms')

    # Algorithm 1: Dirichlet smoothed probabilities
    p_hat = _dirichlet_probabilities(draw_numbers, alpha=1.0)
    alg1_ticket = _weighted_sample_without_replacement(p_hat, 7, rng)
    recommendations.append(
        engine.build_recommendation(
            alg1_ticket,
            algorithm='BayesianSmoothedNumberProbabilities_Dirichlet',
            algorithm_label=_lang_text(lang, 'Dirichlet 平滑概率', 'Dirichlet Smoothed Probabilities'),
            summary=_lang_text(lang, 'Dirichlet 平滑后验概率抽样', 'Sample from Dirichlet-smoothed posteriors'),
            explanation=[
                _lang_text(lang, '用 Dirichlet 先验平滑频次，得到后验概率', 'Apply a Dirichlet prior to smooth frequencies'),
                _lang_text(lang, '按后验概率进行无放回抽样生成号码', 'Sample without replacement using posterior weights'),
            ],
        )
    )

    # Algorithm 2: Binomial z-score
    z_stats = _binomial_z_scores(draw_numbers)
    alg2_ticket = [num for num, _ in sorted(z_stats.items(), key=lambda item: item[1], reverse=True)[:7]]
    recommendations.append(
        engine.build_recommendation(
            sorted(alg2_ticket),
            algorithm='SingleNumberSignificanceTest_BinomialZ',
            algorithm_label=_lang_text(lang, '二项显著性 Z 分数', 'Binomial Z-Score Significance'),
            summary=_lang_text(lang, '二项分布 z-score 最高的号码', 'Top numbers by binomial z-score'),
            explanation=[
                _lang_text(lang, '计算每个号码的出现次数与理论期望的 z-score', 'Compute z-scores vs. theoretical expectation'),
                _lang_text(lang, '选取 z-score 最高的 7 个号码（偏高频显著）', 'Pick the 7 highest z-scores (significantly high frequency)'),
            ],
        )
    )

    # Algorithm 3: Windowed Bayesian + EWMA
    ewma_scores = _ewma_scores(draw_numbers, window=200, alpha=1.0, decay=0.2)
    alg3_ticket = [num for num, _ in sorted(ewma_scores.items(), key=lambda item: item[1], reverse=True)[:7]]
    recommendations.append(
        engine.build_recommendation(
            sorted(alg3_ticket),
            algorithm='WindowedBayesianHotness_EWMA',
            algorithm_label=_lang_text(lang, 'EWMA 近期热度', 'EWMA Recent Hotness'),
            summary=_lang_text(lang, '滑动窗口 + EWMA 的近期热度', 'Windowed Bayesian + EWMA recency score'),
            explanation=[
                _lang_text(lang, '在最近窗口内做 Dirichlet 平滑', 'Apply Dirichlet smoothing within a rolling window'),
                _lang_text(lang, '对窗口概率做 EWMA 更新，强调近期走势', 'EWMA update emphasizes recent trends'),
            ],
        )
    )

    # Algorithm 4: Feature distribution Monte Carlo
    alg4_ticket = _feature_distribution_ticket(draw_numbers, rng)
    recommendations.append(
        engine.build_recommendation(
            sorted(alg4_ticket),
            algorithm='FeatureDistributionTest_MonteCarlo',
            algorithm_label=_lang_text(lang, 'Monte Carlo 特征匹配', 'Monte Carlo Feature Match'),
            summary=_lang_text(lang, 'Monte Carlo 选择特征分布最接近历史的组合', 'Pick tickets whose features match history'),
            explanation=[
                _lang_text(lang, '模拟大量随机票，计算和值/奇偶/大小/连号等特征', 'Simulate many tickets and compute feature stats'),
                _lang_text(lang, '选择特征最接近历史分布的组合', 'Choose the ticket closest to historical distributions'),
            ],
        )
    )

    # Algorithm 5: Anti-crowd selection
    alg5_ticket = _anti_crowd_ticket(rng)
    recommendations.append(
        engine.build_recommendation(
            sorted(alg5_ticket),
            algorithm='AntiCrowdNumberSelection_PopularityPenalty',
            algorithm_label=_lang_text(lang, '反热门防撞号', 'Anti-Crowd Selection'),
            summary=_lang_text(lang, '降低撞号概率的反热门组合', 'Reduce shared picks with popularity penalties'),
            explanation=[
                _lang_text(lang, '惩罚生日号偏多、连号、尾号集中、等差数列等模式', 'Penalize birthday-heavy, consecutive, same-tail, and patterned sets'),
                _lang_text(lang, '在大量候选中选择惩罚分最低的组合', 'Choose the lowest-penalty ticket from many candidates'),
            ],
        )
    )

    # Algorithm 6: Change point detection
    segment_probs = _change_point_segment_probabilities(draw_numbers)
    alg6_ticket = [num for num, _ in sorted(segment_probs.items(), key=lambda item: item[1], reverse=True)[:7]]
    recommendations.append(
        engine.build_recommendation(
            sorted(alg6_ticket),
            algorithm='ChangePointDetection_NumberFrequencies',
            algorithm_label=_lang_text(lang, '变点检测分段概率', 'Change-Point Segment Probabilities'),
            summary=_lang_text(lang, '变点检测后，使用最新区段概率', 'Use smoothed probabilities from the latest segment'),
            explanation=[
                _lang_text(lang, '用变点检测把历史分段，取最新段的平滑概率', 'Segment history via change-point detection'),
                _lang_text(lang, '按该段概率排序选取 7 个号码', 'Select 7 numbers from the latest segment ranking'),
            ],
        )
    )

    # Algorithm 7: Weighted sampling without replacement
    alg7_ticket = _weighted_sample_without_replacement(ewma_scores, 7, _seeded_random(seed, 'alg7'))
    recommendations.append(
        engine.build_recommendation(
            sorted(alg7_ticket),
            algorithm='WeightedSamplingWithoutReplacement_TicketGenerator',
            algorithm_label=_lang_text(lang, '加权无放回抽样', 'Weighted Sampling (No Replacement)'),
            summary=_lang_text(lang, '基于权重的无放回抽样生成', 'Sample without replacement from weighted scores'),
            explanation=[
                _lang_text(lang, '使用 EWMA 权重进行无放回抽样', 'Use EWMA weights for sampling'),
                _lang_text(lang, '保持随机性同时体现权重偏好', 'Keeps randomness while reflecting weights'),
            ],
        )
    )

    return recommendations


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


def _top_numbers(counts: Counter, k: int) -> List[int]:
    return [num for num, _ in counts.most_common(k)]


def _draw_numbers(draws: List[Draw]) -> List[List[int]]:
    ordered = sorted(draws, key=lambda d: d.date)
    return [sorted(draw.numbers) for draw in ordered]


def _seeded_random(seed: str | None, salt: str) -> random.Random:
    if seed is None:
        return random.Random()
    payload = f"{seed}:{salt}".encode('utf-8')
    digest = int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big')
    return random.Random(digest)


def _dirichlet_probabilities(draws: List[List[int]], alpha: float = 1.0) -> dict[int, float]:
    counts = Counter()
    for draw in draws:
        counts.update(draw)
    total_events = len(draws) * 7
    denom = total_events + 50 * alpha
    return {i: (counts.get(i, 0) + alpha) / denom for i in range(1, 51)}


def _binomial_z_scores(draws: List[List[int]]) -> dict[int, float]:
    counts = Counter()
    for draw in draws:
        counts.update(draw)
    total_draws = len(draws)
    q = 7 / 50
    expected = total_draws * q
    variance = max(total_draws * q * (1 - q), 1e-9)
    z_stats = {}
    for i in range(1, 51):
        z_stats[i] = (counts.get(i, 0) - expected) / (variance ** 0.5)
    return z_stats


def _ewma_scores(draws: List[List[int]], window: int, alpha: float, decay: float) -> dict[int, float]:
    scores = {i: 1 / 50 for i in range(1, 51)}
    counts = Counter()
    window_draws: List[List[int]] = []

    for draw in draws:
        window_draws.append(draw)
        counts.update(draw)
        if len(window_draws) > window:
            removed = window_draws.pop(0)
            for n in removed:
                counts[n] -= 1
                if counts[n] <= 0:
                    del counts[n]
        total_events = len(window_draws) * 7
        denom = total_events + 50 * alpha
        for i in range(1, 51):
            p_window = (counts.get(i, 0) + alpha) / denom
            scores[i] = (1 - decay) * scores[i] + decay * p_window

    return scores


def _weighted_sample_without_replacement(weights: dict[int, float], k: int, rng: random.Random) -> List[int]:
    keys = []
    for num, weight in weights.items():
        if weight <= 0:
            continue
        u = rng.random()
        key = u ** (1.0 / weight)
        keys.append((key, num))
    keys.sort(reverse=True)
    return sorted([num for _, num in keys[:k]])


def _feature_distribution_ticket(draws: List[List[int]], rng: random.Random) -> List[int]:
    features = [_extract_features(draw) for draw in draws]
    means, stds = _feature_stats(features)

    best_ticket = None
    best_distance = float('inf')
    for _ in range(3000):
        ticket = sorted(rng.sample(range(1, 51), 7))
        f = _extract_features(ticket)
        distance = 0.0
        for key in means:
            std = stds[key] or 1.0
            distance += abs((f[key] - means[key]) / std)
        if distance < best_distance:
            best_distance = distance
            best_ticket = ticket
    return best_ticket or sorted(rng.sample(range(1, 51), 7))


def _anti_crowd_ticket(rng: random.Random) -> List[int]:
    best_ticket = None
    best_score = float('inf')
    for _ in range(3000):
        ticket = sorted(rng.sample(range(1, 51), 7))
        score = _popularity_penalty(ticket)
        if score < best_score:
            best_score = score
            best_ticket = ticket
    return best_ticket or sorted(rng.sample(range(1, 51), 7))


def _popularity_penalty(ticket: List[int]) -> float:
    penalty = 0.0
    count_low31 = sum(1 for n in ticket if n <= 31)
    penalty += 1.5 * max(0, count_low31 - 3)

    consec = sum(1 for a, b in zip(ticket, ticket[1:]) if b == a + 1)
    penalty += 1.0 * consec

    last_digits = [n % 10 for n in ticket]
    max_dup = max(last_digits.count(d) for d in set(last_digits))
    penalty += 1.0 * max(0, max_dup - 2)

    if _is_arithmetic_progression(ticket):
        penalty += 2.5

    if sum(1 for n in ticket if n % 5 == 0) >= 4:
        penalty += 1.5

    return penalty


def _is_arithmetic_progression(ticket: List[int]) -> bool:
    if len(ticket) < 3:
        return False
    diffs = [b - a for a, b in zip(ticket, ticket[1:])]
    return all(d == diffs[0] for d in diffs)


def _extract_features(draw: List[int]) -> dict[str, float]:
    sorted_draw = sorted(draw)
    sumv = sum(sorted_draw)
    odd = sum(1 for n in sorted_draw if n % 2 == 1)
    small = sum(1 for n in sorted_draw if n <= 25)
    consec = sum(1 for a, b in zip(sorted_draw, sorted_draw[1:]) if b == a + 1)
    gaps = [b - a for a, b in zip(sorted_draw, sorted_draw[1:])]
    gap_entropy = _entropy(gaps)
    return {
        'sum': sumv,
        'odd': odd,
        'small': small,
        'consec': consec,
        'gap_entropy': gap_entropy,
    }


def _feature_stats(features: List[dict[str, float]]) -> tuple[dict[str, float], dict[str, float]]:
    keys = features[0].keys() if features else []
    means = {}
    stds = {}
    for key in keys:
        values = [f[key] for f in features]
        mean = sum(values) / max(len(values), 1)
        variance = sum((v - mean) ** 2 for v in values) / max(len(values), 1)
        means[key] = mean
        stds[key] = variance ** 0.5
    return means, stds


def _entropy(values: List[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = sum(counts.values())
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * (0.0 if p <= 0 else math.log(p))
    return entropy


def _change_point_segment_probabilities(draws: List[List[int]]) -> dict[int, float]:
    if not draws:
        return {i: 1 / 50 for i in range(1, 51)}
    max_draws = min(len(draws), 600)
    segment_draws = draws[-max_draws:]
    n = len(segment_draws)
    min_segment = 120 if n >= 240 else max(20, n // 4)
    penalty = 150.0

    prefix = [[0] * 51]
    for draw in segment_draws:
        prev = prefix[-1][:]
        for nnum in draw:
            prev[nnum] += 1
        prefix.append(prev)

    def segment_cost(start: int, end: int) -> float:
        counts = [prefix[end][i] - prefix[start - 1][i] for i in range(1, 51)]
        total = sum(counts)
        epsilon = 1e-6
        cost = 0.0
        denom = total + 50 * epsilon
        for count in counts:
            if count == 0:
                continue
            p = (count + epsilon) / denom
            cost -= count * math.log(p)
        return cost

    change_points: List[int] = []

    def recurse(start: int, end: int):
        if end - start + 1 < 2 * min_segment:
            return
        best_split = None
        best_gain = 0.0
        cost_full = segment_cost(start, end)
        for split in range(start + min_segment, end - min_segment + 1):
            cost_left = segment_cost(start, split)
            cost_right = segment_cost(split + 1, end)
            gain = cost_full - (cost_left + cost_right)
            if gain > best_gain:
                best_gain = gain
                best_split = split
        if best_split and best_gain > penalty:
            change_points.append(best_split)
            recurse(start, best_split)
            recurse(best_split + 1, end)

    recurse(1, n)
    change_points.sort()

    last_start = (change_points[-1] + 1) if change_points else 1
    last_segment = segment_draws[last_start - 1 :]
    return _dirichlet_probabilities(last_segment, alpha=1.0)
