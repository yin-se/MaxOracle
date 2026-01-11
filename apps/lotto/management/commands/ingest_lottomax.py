from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from ...services.ingestion import ingest_draws


class Command(BaseCommand):
    help = 'Ingest lottery draws from configured data sources.'

    def add_arguments(self, parser):
        parser.add_argument('--since', type=str, help='Ingest draws since YYYY-MM-DD')
        parser.add_argument('--max-pages', type=int, help='Max pages to fetch, if supported')
        parser.add_argument('--source', type=str, default='auto', help='Data source key or auto')
        parser.add_argument('--incremental', action='store_true', help='Use latest draw date as start')
        parser.add_argument('--game', type=str, default='max', help='Game key: max or 649')

    def handle(self, *args, **options):
        since_value = options.get('since')
        since_date = None
        if since_value:
            try:
                since_date = datetime.strptime(since_value, '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('Invalid --since format, use YYYY-MM-DD') from exc

        incremental = bool(options.get('incremental'))
        if since_date and incremental:
            incremental = False
            self.stdout.write(self.style.WARNING('Ignoring --incremental because --since was provided.'))

        result = ingest_draws(
            since=since_date,
            max_pages=options.get('max_pages'),
            source=options.get('source', 'auto'),
            incremental=incremental,
            game=options.get('game', 'max'),
        )
        self.stdout.write(self.style.SUCCESS(result['message']))
