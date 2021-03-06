# Generated by Django 2.0.3 on 2018-03-28 22:10

from django.db import migrations, models
import falcon.validators


class Migration(migrations.Migration):

    dependencies = [
        ('falcon', '0003_auto_20180316_1937'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alerts',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_desc', models.TextField()),
            ],
            options={
                'db_table': 'alerts',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Channels',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.TextField(unique=True)),
            ],
            options={
                'db_table': 'channels',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Stationdays',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='stationday of data')),
                ('ofa_mod_ts', models.DateTimeField(verbose_name='timestamp of modified time of OFA file')),
                ('ofc_mod_ts', models.DateTimeField(verbose_name='timestamp of modified time of OFC file')),
            ],
            options={
                'db_table': 'stationdays',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Stations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('netsta_code', models.TextField(max_length=8, unique=True, validators=[falcon.validators.is_uppercase, falcon.validators.valid_netsta_code], verbose_name='(e.g. IU_ANMO)')),
            ],
            options={
                'db_table': 'stations',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Values',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('average_value', models.FloatField()),
                ('high_value', models.IntegerField()),
                ('low_value', models.IntegerField()),
            ],
            options={
                'db_table': 'values_ahl',
                'managed': False,
            },
        ),
        migrations.RemoveField(
            model_name='alert',
            name='stationday',
        ),
        migrations.AlterUniqueTogether(
            name='stationday',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='stationday',
            name='net_sta',
        ),
        migrations.RemoveField(
            model_name='value',
            name='channel',
        ),
        migrations.RemoveField(
            model_name='value',
            name='stationday',
        ),
        migrations.DeleteModel(
            name='Alert',
        ),
        migrations.DeleteModel(
            name='Channel',
        ),
        migrations.DeleteModel(
            name='NetSta',
        ),
        migrations.DeleteModel(
            name='Stationday',
        ),
        migrations.DeleteModel(
            name='Value',
        ),
    ]
