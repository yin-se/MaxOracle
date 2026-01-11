from django.conf import settings
from django.db import models


def _game_choices() -> list[tuple[str, str]]:
    return [
        (key, config.get('game_name_en', key))
        for key, config in settings.LOTTO_GAMES.items()
    ]


class Draw(models.Model):
    game = models.CharField(max_length=8, db_index=True, choices=_game_choices(), default='max')
    date = models.DateField(db_index=True)
    numbers = models.JSONField()
    bonus = models.PositiveSmallIntegerField()
    source_url = models.URLField(blank=True)
    hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['game', 'date'], name='uniq_game_date'),
        ]

    def __str__(self) -> str:
        return f"{self.game} {self.date}: {' '.join(str(n) for n in self.numbers)} + {self.bonus}"


class DrawNumber(models.Model):
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='draw_numbers')
    number = models.PositiveSmallIntegerField(db_index=True)
    is_bonus = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['draw', 'number', 'is_bonus'], name='uniq_draw_number_bonus'),
        ]
        indexes = [
            models.Index(fields=['number', 'is_bonus'], name='draw_number_idx'),
        ]

    def __str__(self) -> str:
        label = 'bonus' if self.is_bonus else 'main'
        return f"{self.draw.date} {label} {self.number}"


class IngestionLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    run_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    game = models.CharField(max_length=8, db_index=True, choices=_game_choices(), default='max')
    source = models.CharField(max_length=32)
    message = models.TextField(blank=True)
    draws_processed = models.PositiveIntegerField(default=0)
    draws_added = models.PositiveIntegerField(default=0)
    min_date = models.DateField(null=True, blank=True)
    max_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-run_at']

    def __str__(self) -> str:
        return f"{self.run_at:%Y-%m-%d %H:%M} {self.game} {self.status} {self.source}"


class RecommendationSnapshot(models.Model):
    game = models.CharField(max_length=8, db_index=True, choices=_game_choices(), default='max')
    base_draw_date = models.DateField(db_index=True)
    window = models.PositiveIntegerField(default=0)
    seed = models.CharField(max_length=64, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'base_draw_date', 'window', 'seed'],
                name='uniq_snapshot_game_base_window_seed',
            ),
        ]

    def __str__(self) -> str:
        window_label = self.window if self.window else 'all'
        seed_label = self.seed or 'auto'
        return f"{self.game} {self.base_draw_date} window={window_label} seed={seed_label}"


class AiPredictionSnapshot(models.Model):
    game = models.CharField(max_length=8, db_index=True, choices=_game_choices(), default='max')
    base_draw_date = models.DateField(db_index=True)
    window = models.PositiveIntegerField(default=0)
    seed = models.CharField(max_length=64, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'base_draw_date', 'window', 'seed'],
                name='uniq_ai_snapshot_game_base_window_seed',
            ),
        ]

    def __str__(self) -> str:
        window_label = self.window if self.window else 'all'
        seed_label = self.seed or 'auto'
        return f"{self.game} {self.base_draw_date} window={window_label} seed={seed_label}"
