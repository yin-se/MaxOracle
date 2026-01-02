from django.contrib import admin, messages
from django.utils import timezone

from .models import Draw, DrawNumber, IngestionLog
from .services.ingestion import ingest_draws


@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
    list_display = ('date', 'bonus', 'source_url')
    list_filter = ('date',)
    search_fields = ('date',)


@admin.register(DrawNumber)
class DrawNumberAdmin(admin.ModelAdmin):
    list_display = ('draw', 'number', 'is_bonus')
    list_filter = ('is_bonus',)
    search_fields = ('number',)


@admin.register(IngestionLog)
class IngestionLogAdmin(admin.ModelAdmin):
    list_display = ('run_at', 'status', 'source', 'draws_processed', 'draws_added')
    list_filter = ('status', 'source', 'run_at')
    actions = ['trigger_ingest', 'trigger_incremental']

    def trigger_ingest(self, request, queryset):
        result = ingest_draws()
        messages.add_message(
            request,
            messages.INFO,
            f"Ingestion triggered at {timezone.now():%Y-%m-%d %H:%M}. Added {result['draws_added']} draws.",
        )

    trigger_ingest.short_description = 'Trigger ingest with default settings'

    def trigger_incremental(self, request, queryset):
        result = ingest_draws(incremental=True)
        messages.add_message(
            request,
            messages.INFO,
            f"Incremental ingestion at {timezone.now():%Y-%m-%d %H:%M}. Added {result['draws_added']} draws.",
        )

    trigger_incremental.short_description = 'Trigger incremental ingest'
