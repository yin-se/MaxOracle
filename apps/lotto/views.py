from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Draw, IngestionLog, RecommendationSnapshot, AiPredictionSnapshot
from .services.ai import predict_next_draw_probabilities
from .services.analytics import compute_analysis, get_draws
from .services.cache import AnalysisCache
from .services.ingestion import ingest_draws
from .services.recommender import build_recommendations, build_recommendation_snapshot_payload

cache = AnalysisCache()

SUPPORTED_LANGS = {'zh', 'zh-hans', 'en'}


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _get_lang(request) -> str:
    requested = request.GET.get('lang')
    if requested in SUPPORTED_LANGS:
        normalized = 'en' if requested == 'en' else 'zh'
        request.session['lang'] = normalized

    lang = request.session.get('lang', 'zh')
    language_code = 'en' if lang == 'en' else 'zh-hans'
    translation.activate(language_code)
    request.LANGUAGE_CODE = language_code
    return lang


def home(request):
    lang = _get_lang(request)
    latest_draw = Draw.objects.order_by('-date').first()
    latest_log = IngestionLog.objects.first()
    total_draws = Draw.objects.count()
    context = {
        'latest_draw': latest_draw,
        'latest_log': latest_log,
        'total_draws': total_draws,
        'disclaimer': _disclaimer_text(lang),
        'lang': lang,
    }
    return render(request, 'lotto/home.html', context)


def rules(request):
    lang = _get_lang(request)
    return render(request, 'lotto/rules.html', {'disclaimer': _disclaimer_text(lang), 'lang': lang})


def data_status(request):
    lang = _get_lang(request)
    latest_draw = Draw.objects.order_by('-date').first()
    logs = IngestionLog.objects.all()[:10]
    recent_draws = Draw.objects.order_by('-date')[:15]
    context = {
        'latest_draw': latest_draw,
        'total_draws': Draw.objects.count(),
        'logs': logs,
        'recent_draws': recent_draws,
        'disclaimer': _disclaimer_text(lang),
        'lang': lang,
    }
    return render(request, 'lotto/data.html', context)


def analysis(request):
    lang = _get_lang(request)
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    context = {
        'window_default': window_default,
        'disclaimer': _disclaimer_text(lang),
        'lang': lang,
    }
    return render(request, 'lotto/analysis.html', context)


def ai_lab(request):
    lang = _get_lang(request)
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    context = {
        'window_default': window_default,
        'disclaimer': _disclaimer_text(lang),
        'lang': lang,
    }
    return render(request, 'lotto/ai.html', context)


def recommendations(request):
    lang = _get_lang(request)
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    seed = request.GET.get('seed') or settings.LOTTO_CONFIG.get('RECOMMENDATION_SEED')
    window = _parse_int(request.GET.get('window'), window_default)
    window_value = window if window > 0 else 0

    latest_two = list(Draw.objects.order_by('-date')[:2])
    latest_draw = latest_two[0] if latest_two else None
    previous_draw = latest_two[1] if len(latest_two) > 1 else None
    base_draw = previous_draw or latest_draw
    base_draw_date = base_draw.date if base_draw else None
    compare_draw = latest_draw if previous_draw else None

    recommendations_list = []
    snapshot = None
    if base_draw_date:
        seed_value = str(seed or f"auto:{base_draw_date.isoformat()}:{window_value}").strip()
        snapshot = RecommendationSnapshot.objects.filter(
            base_draw_date=base_draw_date,
            window=window_value,
            seed=seed_value,
        ).first()
        if snapshot is None:
            draws = get_draws(window=window_value or None, end_date=base_draw_date)
            payload = build_recommendation_snapshot_payload(draws, seed=seed_value)
            snapshot = RecommendationSnapshot.objects.create(
                base_draw_date=base_draw_date,
                window=window_value,
                seed=seed_value,
                payload=payload,
            )

        for item in snapshot.payload:
            texts = item.get('texts', {}).get('en' if lang == 'en' else 'zh', {})
            metrics = item.get('metrics', {})
            numbers = item.get('numbers', [])
            match_count = None
            bonus_hit = False
            if compare_draw:
                match_count = len(set(numbers) & set(compare_draw.numbers))
                bonus_hit = compare_draw.bonus in numbers
            recommendations_list.append({
                'numbers': numbers,
                'algorithm': item.get('algorithm'),
                'algorithm_label': texts.get('label', ''),
                'algorithm_summary': texts.get('summary', ''),
                'explanation': texts.get('explanation', []),
                'odd_count': metrics.get('odd_count', 0),
                'even_count': metrics.get('even_count', 0),
                'small_count': metrics.get('small_count', 0),
                'large_count': metrics.get('large_count', 0),
                'total_sum': metrics.get('total_sum', 0),
                'hot_count': metrics.get('hot_count', 0),
                'cold_count': metrics.get('cold_count', 0),
                'pair_boost': metrics.get('pair_boost', 0),
                'match_count': match_count,
                'bonus_hit': bonus_hit,
            })

    context = {
        'recommendations': recommendations_list,
        'seed': seed,
        'window': window_value,
        'latest_draw': latest_draw,
        'base_draw_date': base_draw_date,
        'compare_draw': compare_draw,
        'disclaimer': _disclaimer_text(lang),
        'lang': lang,
    }
    return render(request, 'lotto/recommendations.html', context)


def api_status(request):
    latest_draw = Draw.objects.order_by('-date').first()
    latest_log = IngestionLog.objects.first()
    return JsonResponse({
        'total_draws': Draw.objects.count(),
        'latest_draw_date': latest_draw.date.isoformat() if latest_draw else None,
        'latest_ingestion': latest_log.message if latest_log else None,
    })


def api_analysis(request):
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    rolling_default = settings.LOTTO_CONFIG['DEFAULT_ROLLING_WINDOW']

    window = _parse_int(request.GET.get('window'), window_default)
    if window <= 0:
        window = None
    rolling = _parse_int(request.GET.get('rolling'), rolling_default)
    start_date = _parse_date(request.GET.get('start_date'))
    end_date = _parse_date(request.GET.get('end_date'))

    params = {
        'window': window,
        'rolling': rolling,
        'start_date': start_date,
        'end_date': end_date,
    }

    def compute():
        draws = get_draws(window=window, start_date=start_date, end_date=end_date)
        return compute_analysis(draws, rolling_window=rolling)

    analysis_data = cache.get_or_set('analysis', params, compute)

    return JsonResponse({
        'meta': analysis_data.meta,
        'main_frequency': analysis_data.main_frequency,
        'bonus_frequency': analysis_data.bonus_frequency,
        'omissions': analysis_data.omissions,
        'hot_numbers': analysis_data.hot_numbers,
        'cold_numbers': analysis_data.cold_numbers,
        'pair_frequency': analysis_data.pair_frequency,
        'triplet_frequency': analysis_data.triplet_frequency,
        'odd_even_distribution': analysis_data.odd_even_distribution,
        'size_distribution': analysis_data.size_distribution,
        'sum_distribution': analysis_data.sum_distribution,
        'span_distribution': analysis_data.span_distribution,
        'consecutive_ratio': analysis_data.consecutive_ratio,
        'rolling_series': analysis_data.rolling_series,
    })


def api_recommendations(request):
    lang = _get_lang(request)
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    seed = request.GET.get('seed')
    window = _parse_int(request.GET.get('window'), window_default)
    if window <= 0:
        window = None
    draws = get_draws(window=window)
    recommendations_list = build_recommendations(draws, seed=seed, lang=lang)

    payload = []
    for rec in recommendations_list:
        payload.append({
            'numbers': rec.numbers,
            'odd_count': rec.odd_count,
            'even_count': rec.even_count,
            'small_count': rec.small_count,
            'large_count': rec.large_count,
            'total_sum': rec.total_sum,
            'hot_count': rec.hot_count,
            'cold_count': rec.cold_count,
            'pair_boost': rec.pair_boost,
            'explanation': rec.explanation,
            'algorithm': rec.algorithm,
            'algorithm_label': rec.algorithm_label,
            'algorithm_summary': rec.algorithm_summary,
        })

    return JsonResponse({
        'seed': seed,
        'window': window,
        'recommendations': payload,
    })


def api_ai(request):
    lang = _get_lang(request)
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    seed = request.GET.get('seed') or settings.LOTTO_CONFIG.get('RECOMMENDATION_SEED')
    window = _parse_int(request.GET.get('window'), window_default)
    window_value = window if window > 0 else 0

    params = {
        'window': window_value,
        'seed': seed,
    }

    latest_two = list(Draw.objects.order_by('-date')[:2])
    latest_draw = latest_two[0] if latest_two else None
    previous_draw = latest_two[1] if len(latest_two) > 1 else None
    base_draw = previous_draw or latest_draw
    base_draw_date = base_draw.date if base_draw else None
    compare_draw = latest_draw if previous_draw else None

    result = None
    if base_draw_date:
        seed_value = str(seed or f"auto:ai:{base_draw_date.isoformat()}:{window_value}").strip()
        snapshot = AiPredictionSnapshot.objects.filter(
            base_draw_date=base_draw_date,
            window=window_value,
            seed=seed_value,
        ).first()
        if snapshot is None:
            draws = get_draws(window=window_value or None, end_date=base_draw_date)
            payload = predict_next_draw_probabilities(draws, seed=seed_value)
            snapshot = AiPredictionSnapshot.objects.create(
                base_draw_date=base_draw_date,
                window=window_value,
                seed=seed_value,
                payload=payload,
            )
        result = snapshot.payload

    if result is None:
        def compute():
            draws = get_draws(window=window_value or None)
            return predict_next_draw_probabilities(draws, seed=seed)

        result = cache.get_or_set('ai', params, compute, ttl=60 * 30)

    match_count = None
    bonus_hit = False
    if compare_draw:
        match_count = len(set(result.get('top_numbers', [])) & set(compare_draw.numbers))
        bonus_hit = compare_draw.bonus in set(result.get('top_numbers', []))

    return JsonResponse({
        'window': window_value,
        'seed': seed,
        'experimental': True,
        'base_draw_date': base_draw_date.isoformat() if base_draw_date else None,
        'compare_draw_date': compare_draw.date.isoformat() if compare_draw else None,
        'compare_draw_numbers': compare_draw.numbers if compare_draw else [],
        'compare_draw_bonus': compare_draw.bonus if compare_draw else None,
        'match_count': match_count,
        'bonus_hit': bonus_hit,
        'probabilities': result['probabilities'],
        'top_numbers': result['top_numbers'],
        'meta': result['meta'],
    })


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def cron_ingest(request):
    expected_token = settings.CRON_INGEST_TOKEN
    auth_header = request.headers.get('Authorization', '')
    bearer_token = auth_header.replace('Bearer ', '').replace('Token ', '').strip() if auth_header else ''
    token = (
        request.headers.get('X-CRON-TOKEN')
        or request.headers.get('X-CRON-SECRET')
        or bearer_token
        or request.GET.get('token')
        or request.POST.get('token')
    )
    if not expected_token:
        return JsonResponse({'error': 'CRON_INGEST_TOKEN not configured'}, status=500)
    if token != expected_token:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    source = request.GET.get('source') or request.POST.get('source') or 'lotto8'
    try:
        result = ingest_draws(incremental=True, source=source)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    return JsonResponse({
        'status': result['status'],
        'draws_added': result['draws_added'],
        'message': result['message'],
    })


def _disclaimer_text(lang: str) -> str:
    if lang == 'en':
        return (
            'Disclaimer: Lottery results are random. Recommendations do not guarantee winnings. '
            'This site is for statistical learning and visualization only and is not gambling advice.'
        )
    return (
        '免责声明：彩票结果具有随机性，任何推荐不保证中奖。'
        '本网站仅用于统计学习与可视化展示，不构成博彩建议。'
    )
