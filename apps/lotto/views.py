from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Draw, IngestionLog
from .services.analytics import compute_analysis, get_draws
from .services.cache import AnalysisCache
from .services.ingestion import ingest_draws
from .services.recommender import RecommendationEngine

cache = AnalysisCache()


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


def home(request):
    latest_draw = Draw.objects.order_by('-date').first()
    latest_log = IngestionLog.objects.first()
    total_draws = Draw.objects.count()
    context = {
        'latest_draw': latest_draw,
        'latest_log': latest_log,
        'total_draws': total_draws,
        'disclaimer': _disclaimer_text(),
    }
    return render(request, 'lotto/home.html', context)


def rules(request):
    return render(request, 'lotto/rules.html', {'disclaimer': _disclaimer_text()})


def data_status(request):
    latest_draw = Draw.objects.order_by('-date').first()
    logs = IngestionLog.objects.all()[:10]
    recent_draws = Draw.objects.order_by('-date')[:15]
    context = {
        'latest_draw': latest_draw,
        'total_draws': Draw.objects.count(),
        'logs': logs,
        'recent_draws': recent_draws,
        'disclaimer': _disclaimer_text(),
    }
    return render(request, 'lotto/data.html', context)


def analysis(request):
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    context = {
        'window_default': window_default,
        'disclaimer': _disclaimer_text(),
    }
    return render(request, 'lotto/analysis.html', context)


def recommendations(request):
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    seed = request.GET.get('seed')
    window = _parse_int(request.GET.get('window'), window_default)
    if window <= 0:
        window = None
    draws = get_draws(window=window)
    engine = RecommendationEngine(draws, seed=seed)
    recommendations_list = engine.generate(count=settings.LOTTO_CONFIG['RECOMMENDATION_COUNT'])
    context = {
        'recommendations': recommendations_list,
        'seed': seed,
        'window': window,
        'disclaimer': _disclaimer_text(),
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
    window_default = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
    seed = request.GET.get('seed')
    window = _parse_int(request.GET.get('window'), window_default)
    if window <= 0:
        window = None
    count = _parse_int(request.GET.get('count'), settings.LOTTO_CONFIG['RECOMMENDATION_COUNT'])

    draws = get_draws(window=window)
    engine = RecommendationEngine(draws, seed=seed)
    recommendations_list = engine.generate(count=count)

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
        })

    return JsonResponse({
        'seed': seed,
        'window': window,
        'recommendations': payload,
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


def _disclaimer_text() -> str:
    return (
        '免责声明：彩票结果具有随机性，任何推荐不保证中奖。'
        '本网站仅用于统计学习与可视化展示，不构成博彩建议。'
    )
