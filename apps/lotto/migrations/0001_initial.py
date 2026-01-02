from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Draw',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True, unique=True)),
                ('numbers', models.JSONField()),
                ('bonus', models.PositiveSmallIntegerField()),
                ('source_url', models.URLField(blank=True)),
                ('hash', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='IngestionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')], max_length=16)),
                ('source', models.CharField(max_length=32)),
                ('message', models.TextField(blank=True)),
                ('draws_processed', models.PositiveIntegerField(default=0)),
                ('draws_added', models.PositiveIntegerField(default=0)),
                ('min_date', models.DateField(blank=True, null=True)),
                ('max_date', models.DateField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-run_at'],
            },
        ),
        migrations.CreateModel(
            name='DrawNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveSmallIntegerField(db_index=True)),
                ('is_bonus', models.BooleanField(default=False)),
                ('draw', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='draw_numbers', to='lotto.draw')),
            ],
        ),
        migrations.AddConstraint(
            model_name='drawnumber',
            constraint=models.UniqueConstraint(fields=('draw', 'number', 'is_bonus'), name='uniq_draw_number_bonus'),
        ),
        migrations.AddIndex(
            model_name='drawnumber',
            index=models.Index(fields=['number', 'is_bonus'], name='draw_number_idx'),
        ),
    ]
