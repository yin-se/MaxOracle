from django.db import models


class Draw(models.Model):
    date = models.DateField(unique=True, db_index=True)
    numbers = models.JSONField()
    bonus = models.PositiveSmallIntegerField()
    source_url = models.URLField(blank=True)
    hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self) -> str:
        return f"{self.date}: {' '.join(str(n) for n in self.numbers)} + {self.bonus}"


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
    source = models.CharField(max_length=32)
    message = models.TextField(blank=True)
    draws_processed = models.PositiveIntegerField(default=0)
    draws_added = models.PositiveIntegerField(default=0)
    min_date = models.DateField(null=True, blank=True)
    max_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-run_at']

    def __str__(self) -> str:
        return f"{self.run_at:%Y-%m-%d %H:%M} {self.status} {self.source}"


class RecommendationSnapshot(models.Model):
    base_draw_date = models.DateField(db_index=True)
    window = models.PositiveIntegerField(default=0)
    seed = models.CharField(max_length=64, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['base_draw_date', 'window', 'seed'],
                name='uniq_snapshot_base_window_seed',
            ),
        ]

    def __str__(self) -> str:
        window_label = self.window if self.window else 'all'
        seed_label = self.seed or 'auto'
        return f"{self.base_draw_date} window={window_label} seed={seed_label}"


class AiPredictionSnapshot(models.Model):
    base_draw_date = models.DateField(db_index=True)
    window = models.PositiveIntegerField(default=0)
    seed = models.CharField(max_length=64, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['base_draw_date', 'window', 'seed'],
                name='uniq_ai_snapshot_base_window_seed',
            ),
        ]

    def __str__(self) -> str:
        window_label = self.window if self.window else 'all'
        seed_label = self.seed or 'auto'
        return f"{self.base_draw_date} window={window_label} seed={seed_label}"
