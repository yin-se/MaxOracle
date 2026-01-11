from __future__ import annotations

from datetime import date
import hashlib
import logging
from typing import Iterable, List, Optional

from django.db import transaction
from django.utils import timezone

from django.conf import settings

from ..models import Draw, DrawNumber, IngestionLog
from .analytics import compute_analysis, get_draws
from .cache import AnalysisCache
from .game_config import get_game_config
from .scrapers.base import DrawRecord, ScrapeError
from .scrapers.registry import fetch_draws

logger = logging.getLogger('lotto')


def normalize_numbers(numbers: Iterable[int]) -> List[int]:
    unique = sorted({int(n) for n in numbers})
    return unique


def validate_draw(record: DrawRecord, main_count: int, max_number: int) -> tuple[bool, str]:
    numbers = normalize_numbers(record.numbers)
    if len(numbers) != main_count:
        return False, f'expected {main_count} unique main numbers'
    if any(n < 1 or n > max_number for n in numbers):
        return False, 'main numbers out of range'
    if record.bonus < 1 or record.bonus > max_number:
        return False, 'bonus number out of range'
    if record.bonus in numbers:
        return False, 'bonus duplicates main number'
    return True, ''


def compute_hash(game: str, draw_date: date, numbers: List[int], bonus: int) -> str:
    payload = f"{game}|{draw_date.isoformat()}|{'-'.join(map(str, numbers))}|{bonus}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def ingest_draws(
    since: Optional[date] = None,
    max_pages: Optional[int] = None,
    source: str = 'auto',
    incremental: bool = False,
    game: str | None = None,
) -> dict:
    game_config = get_game_config(game)
    game_key = game_config.key
    if incremental and since is None:
        latest_draw = Draw.objects.filter(game=game_key).order_by('-date').first()
        if latest_draw:
            since = latest_draw.date

    logger.info(
        'Starting ingestion: source=%s since=%s max_pages=%s incremental=%s',
        source,
        since,
        max_pages,
        incremental,
    )
    status = 'failed'
    draws_added = 0
    draws_processed = 0
    min_date = None
    max_date = None
    message = ''

    try:
        source_name, records = fetch_draws(source=source, max_pages=max_pages, game=game_key)
    except ScrapeError as exc:
        message = f"{exc} ({exc.detail})"
        IngestionLog.objects.create(
            status='failed',
            game=game_key,
            source=exc.source,
            message=message,
            draws_processed=0,
            draws_added=0,
        )
        raise

    if since:
        records = [record for record in records if record.date >= since]

    deduped: dict[date, DrawRecord] = {}
    for record in records:
        deduped[record.date] = record

    records = list(deduped.values())
    records.sort(key=lambda r: r.date, reverse=True)

    if records:
        min_date = records[-1].date
        max_date = records[0].date

    existing_draws = {
        draw.date: draw
        for draw in Draw.objects.filter(game=game_key, date__in=[record.date for record in records])
    }

    new_draws: List[Draw] = []
    new_draw_numbers: List[DrawNumber] = []
    skipped = 0

    for record in records:
        draws_processed += 1
        is_valid, reason = validate_draw(record, game_config.main_count, game_config.max_number)
        if not is_valid:
            logger.warning('Skipping draw %s due to validation error: %s', record.date, reason)
            skipped += 1
            continue
        numbers = normalize_numbers(record.numbers)
        bonus = int(record.bonus)
        draw_hash = compute_hash(game_key, record.date, numbers, bonus)

        existing = existing_draws.get(record.date)
        if existing:
            if existing.numbers == numbers and existing.bonus == bonus:
                continue
            logger.error('Conflict detected for %s, existing draw differs from scraped data', record.date)
            skipped += 1
            continue

        new_draw = Draw(
            game=game_key,
            date=record.date,
            numbers=numbers,
            bonus=bonus,
            source_url=record.source_url,
            hash=draw_hash,
        )
        new_draws.append(new_draw)

    with transaction.atomic():
        created_draws = Draw.objects.bulk_create(new_draws)
        for draw in created_draws:
            for number in draw.numbers:
                new_draw_numbers.append(DrawNumber(draw=draw, number=number, is_bonus=False))
            new_draw_numbers.append(DrawNumber(draw=draw, number=draw.bonus, is_bonus=True))
        DrawNumber.objects.bulk_create(new_draw_numbers)

    draws_added = len(new_draws)
    status = 'success' if skipped == 0 else 'partial'
    message = f"Processed {draws_processed} draws, added {draws_added}, skipped {skipped}"

    IngestionLog.objects.create(
        status=status,
        game=game_key,
        source=source_name,
        message=message,
        draws_processed=draws_processed,
        draws_added=draws_added,
        min_date=min_date,
        max_date=max_date,
    )

    try:
        window = settings.LOTTO_CONFIG['DEFAULT_WINDOW']
        rolling = settings.LOTTO_CONFIG['DEFAULT_ROLLING_WINDOW']
        cache = AnalysisCache()

        def compute():
            analysis_draws = get_draws(window=window, game=game_key)
            return compute_analysis(
                analysis_draws,
                rolling_window=rolling,
                max_number=game_config.max_number,
                main_count=game_config.main_count,
                small_threshold=game_config.small_threshold,
            )

        cache.get_or_set('analysis', {'game': game_key, 'window': window, 'rolling': rolling}, compute)
    except Exception as exc:
        logger.warning('Post-ingest analysis cache failed: %s', exc)

    logger.info('Ingestion completed: %s', message)
    return {
        'status': status,
        'source': source_name,
        'draws_processed': draws_processed,
        'draws_added': draws_added,
        'min_date': min_date,
        'max_date': max_date,
        'message': message,
        'timestamp': timezone.now(),
    }
