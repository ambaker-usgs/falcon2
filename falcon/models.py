from django.db import models

from falcon.validators import *

# Create your models here.
class Stations(models.Model):
    station_id = models.BigAutoField(primary_key=True)
    station_name = models.TextField(max_length=8, unique=True, verbose_name='(e.g. IU_ANMO)', validators=[is_uppercase, valid_netsta_code])
    
    class Meta:
        app_label = 'falcon'
        db_table = 'stations'
        managed = False
    
    def __str__(self):
        return '%s' % (self.station_name)

class Stationdays(models.Model):
    stationday_id = models.BigAutoField(primary_key=True)
    station_fk = models.ForeignKey('Stations', models.DO_NOTHING, db_column='station_fk')
    stationday_date = models.DateTimeField()
    ofa_mod_ts = models.DateTimeField(blank=True, null=True)
    ofc_mod_ts = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'stationdays'
        # unique_together = ('station_fk', 'stationday_date')
    
    def __str__(self):
        return '%s %s' % (self.station_fk, self.stationday_date)

class Channels(models.Model):
    channel_id = models.BigAutoField(primary_key=True)
    channel = models.TextField(unique=True)
    units = models.TextField(blank=True, null=True)
    description = models.TextField()

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'channels'
    
    def __str__(self):
        return '%s' % (self.channel)

class Alerts(models.Model):
    alert_id = models.BigAutoField(primary_key=True)
    stationday_fk = models.ForeignKey('Stationdays', models.DO_NOTHING, db_column='stationday_fk')
    alert = models.TextField()
    alert_ts = models.DateTimeField()
    triggered = models.BooleanField()

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'alerts'
    
    def __str__(self):
        alert_dt = self.alert_ts.strftime('%Y/%m/%d (%j) %H:%M:%S')
        return '%-8s %s %s: Alarm event On %s' % (self.stationday_fk.station_fk.station_name, alert_dt, self.alert, 'triggered' if self.triggered else 'restored')

class ValuesAhl(models.Model):
    value_id = models.BigAutoField(primary_key=True)
    stationday_fk = models.ForeignKey('Stationdays', models.DO_NOTHING, db_column='stationday_fk')
    channel_fk = models.ForeignKey('Channels', models.DO_NOTHING, db_column='channel_fk')
    avg_value = models.FloatField()
    high_value = models.IntegerField()
    low_value = models.IntegerField()

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'values_ahl'
        # unique_together = ('stationday_fk','channel_fk')
    
    def __str__(self):
        if self.avg_value and self.high_value and self.low_value:
            return '%s %s %.2f %d %d' % (self.stationday_fk, self.channel_fk, self.avg_value, self.high_value, self.low_value)
        return '%s %s -- -- --' % (self.stationday_fk, self.channel_fk)

class AlertsDisplay(models.Model):
    alerts_display_id = models.BigAutoField(primary_key=True)
    station_fk = models.ForeignKey('Stations', models.DO_NOTHING, db_column='station_fk')
    alert = models.TextField()
    alert_warning_level = models.BigIntegerField()
    alert_value = models.TextField()

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'alerts_display'
    
    def __str__(self):
        return '%-8s %s [%d] %s' % (self.station_fk.station_name, self.alert_value, self.alert_warning_level, self.alert)

class ChannelsDisplay(models.Model):
    channels_display_id = models.BigAutoField(primary_key=True)
    station_fk = models.ForeignKey('Stations', models.DO_NOTHING, db_column='station_fk')
    channel = models.TextField()
    channel_warning_level = models.BigIntegerField()
    channel_value = models.TextField()

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'channels_display'
    
    def __str__(self):
        return '%-8s %s [%d] %s' % (self.station_fk.station_name, self.channel_value, self.channel_warning_level, self.channel)