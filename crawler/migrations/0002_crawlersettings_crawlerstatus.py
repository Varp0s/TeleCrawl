# Generated by Django 5.2 on 2025-05-26 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CrawlerSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField()),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Crawler Ayarı',
                'verbose_name_plural': 'Crawler Ayarları',
                'db_table': 'crawler_settings',
            },
        ),
        migrations.CreateModel(
            name='CrawlerStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_running', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('stopped', 'Stopped'), ('running', 'Running'), ('error', 'Error')], default='stopped', max_length=20)),
                ('process_id', models.IntegerField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('stopped_at', models.DateTimeField(blank=True, null=True)),
                ('last_message', models.TextField(blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('messages_processed', models.IntegerField(default=0)),
                ('channels_processed', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Crawler Durumu',
                'verbose_name_plural': 'Crawler Durumları',
                'db_table': 'crawler_status',
            },
        ),
    ]
