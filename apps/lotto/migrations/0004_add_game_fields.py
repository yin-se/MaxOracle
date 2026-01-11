from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lotto', '0003_ai_prediction_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='draw',
            name='game',
            field=models.CharField(
                choices=[('max', 'Lotto Max'), ('649', 'Lotto 6/49')],
                db_index=True,
                default='max',
                max_length=8,
            ),
        ),
        migrations.AlterField(
            model_name='draw',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AddConstraint(
            model_name='draw',
            constraint=models.UniqueConstraint(fields=('game', 'date'), name='uniq_game_date'),
        ),
        migrations.AddField(
            model_name='ingestionlog',
            name='game',
            field=models.CharField(
                choices=[('max', 'Lotto Max'), ('649', 'Lotto 6/49')],
                db_index=True,
                default='max',
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name='recommendationsnapshot',
            name='game',
            field=models.CharField(
                choices=[('max', 'Lotto Max'), ('649', 'Lotto 6/49')],
                db_index=True,
                default='max',
                max_length=8,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='recommendationsnapshot',
            name='uniq_snapshot_base_window_seed',
        ),
        migrations.AddConstraint(
            model_name='recommendationsnapshot',
            constraint=models.UniqueConstraint(
                fields=('game', 'base_draw_date', 'window', 'seed'),
                name='uniq_snapshot_game_base_window_seed',
            ),
        ),
        migrations.AddField(
            model_name='aipredictionsnapshot',
            name='game',
            field=models.CharField(
                choices=[('max', 'Lotto Max'), ('649', 'Lotto 6/49')],
                db_index=True,
                default='max',
                max_length=8,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='aipredictionsnapshot',
            name='uniq_ai_snapshot_base_window_seed',
        ),
        migrations.AddConstraint(
            model_name='aipredictionsnapshot',
            constraint=models.UniqueConstraint(
                fields=('game', 'base_draw_date', 'window', 'seed'),
                name='uniq_ai_snapshot_game_base_window_seed',
            ),
        ),
    ]
