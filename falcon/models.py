from django.db import models

from falcon.validators import *


class Stations(models.Model):
    station_id = models.BigAutoField(primary_key=True)
    station_name = models.CharField(max_length=8, unique=True,
                                    validators=[is_uppercase, valid_netsta_code],
                                    verbose_name='Station Name',
                                    help_text="Station name e.g. IU_ANMO")
    
    class Meta:
        app_label = 'falcon'
        db_table = 'stations'
        managed = False
    
    def __str__(self):
        return '%s' % self.station_name


class Stationdays(models.Model):
    """
    Station Date data
    """
    stationday_id = models.BigAutoField(primary_key=True)
    station_fk = models.ForeignKey('Stations',
                                   models.DO_NOTHING,
                                   db_column='station_fk',
                                   help_text='Station Date stamp',
                                   verbose_name='Station Date stamp')
    stationday_date = models.DateTimeField(help_text='Station data date stamp',
                                           verbose_name='Station Date')
    ofa_mod_ts = models.DateTimeField(blank=True, null=True,
                                      help_text='???',
                                      verbose_name='???')
    ofc_mod_ts = models.DateTimeField(blank=True, null=True,
                                      help_text='???',
                                      verbose_name='???')

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'stationdays'
        # unique_together = ('station_fk', 'stationday_date')
    
    def __str__(self):
        return '%s %s' % (self.station_fk, self.stationday_date)


class Channels(models.Model):
    """
    Sensor Channel
    """
    channel_id = models.BigAutoField(primary_key=True)
    channel = models.CharField(max_length=10,
                               unique=True,
                               help_text='Sensor Channel',
                               verbose_name='Sensor Channel')
    units = models.CharField(max_length=50,
                             help_text='Channel data units',
                             verbose_name='Sensor Channel Units')
    description = models.CharField(max_length=128,
                                   help_text='Description of Sensor Channel',
                                   verbose_name = 'Channel description')

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'channels'
    
    def __str__(self):
        return '%s' % self.channel


class Alerts(models.Model):
    """
    Alert events
    """
    alert_id = models.BigAutoField(primary_key=True)
    stationday_fk = models.ForeignKey('Stationdays',
                                      models.DO_NOTHING,
                                      db_column='stationday_fk',
                                      help_text='Date of alert',
                                      verbose_name='Alert Date')
    alert = models.TextField(blank=True, null=True,
                             help_text='Text of alert',
                             verbose_name='Alert Text')
    alert_ts = models.DateTimeField(help_text='Alert Event time stamp',
                                    verbose_name='Alert Time Stamp')
    triggered = models.BooleanField(help_text='Alert event triggered=True',
                                    verbose_name='Alert Triggered')

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'alerts'
    
    def __str__(self):
        return '%s %s' % (self.stationday_fk, self.alert)


class ValuesAhl(models.Model):
    value_id = models.BigAutoField(primary_key=True)
    stationday_fk = models.ForeignKey('Stationdays', models.DO_NOTHING,
                                      db_column='stationday_fk',
                                      verbose_name='Station Date',
                                      help_text='Station Date of data')
    channel_fk = models.ForeignKey('Channels', models.DO_NOTHING,
                                   db_column='channel_fk',
                                   verbose_name='Data channel',
                                   help_text='Data channel')
    avg_value = models.FloatField(verbose_name='Average Value',
                                  help_text='Average value')
    high_value = models.IntegerField(verbose_name='High Value',
                                     help_text='High value')
    low_value = models.IntegerField(verbose_name='Low Value',
                                    help_text='Low value')

    class Meta:
        app_label = 'falcon'
        managed = False
        db_table = 'values_ahl'
        # unique_together = ('stationday_fk','channel_fk')
    
    def __str__(self):
        if self.avg_value and self.high_value and self.low_value:
            return '%s %s %.2f %d %d' % (self.stationday_fk, self.channel_fk, self.avg_value, self.high_value, self.low_value)
        return '%s %s -- -- --' % (self.stationday_fk, self.channel_fk)
