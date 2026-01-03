from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lotto', '0002_recommendation_snapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='AiPredictionSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base_draw_date', models.DateField(db_index=True)),
                ('window', models.PositiveIntegerField(default=0)),
                ('seed', models.CharField(blank=True, max_length=64)),
                ('payload', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='aipredictionsnapshot',
            constraint=models.UniqueConstraint(fields=('base_draw_date', 'window', 'seed'), name='uniq_ai_snapshot_base_window_seed'),
        ),
    ]
