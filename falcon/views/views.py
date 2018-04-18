from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl

import glob
import subprocess
from datetime import datetime, timedelta

class StationOverview(object):
    def __init__(self, netsta, alerts, alert_days_back=15):
        self.station = Stations.objects.get(station_name=netsta)
        self.net_code, self.sta_code = self.station.station_name.split('_')
        self.most_recent_stationday = Stationdays.objects.filter(station_fk=self.station).order_by('-stationday_date')[0]
        self.get_channels_with_warnings()
        # alerts = Alerts.objects.filter(stationday_fk__stationday_date__gte=datetime.today() - timedelta(alert_days_back))
        self.get_alerts_with_warnings(alerts, alert_days_back)
        self.calculate_highest_alert()
    def get_channels_with_warnings(self):
        channels = ValuesAhl.objects.distinct('channel_fk__channel').filter(stationday_fk__station_fk=self.station).order_by('channel_fk__channel')
        self.channels_dict = {}
        for channel in channels:
            chan = ValuesAhl.objects.filter(stationday_fk__station_fk=self.station,channel_fk=channel.channel_fk).order_by('-stationday_fk__stationday_date')[0]
            # Battery Voltages (B1V...B12V) usually stay around 13v
            if str(chan.channel_fk)[0] == 'B' and str(chan.channel_fk)[-1] == 'V' and str(chan.channel_fk)[1:-1].isdigit():
                if 11 <= chan.low_value <= 15 and 11 <= chan.high_value <= 15:
                    self.channels_dict[str(chan.channel_fk)] = 1
                elif 10 <= chan.low_value <= 16 and 10 <= chan.high_value <= 16:
                    self.channels_dict[str(chan.channel_fk)] = 2
                else:
                    self.channels_dict[str(chan.channel_fk)] = 3
            # Battery Voltages (B1V...B12V) usually stay around 13v
            elif str(chan.channel_fk)[0:3] == 'DCV':
                if 21 <= chan.low_value <= 30 and 21 <= chan.high_value <= 30:
                    self.channels_dict[str(chan.channel_fk)] = 1
                elif 19 <= chan.low_value <= 35 and 19 <= chan.high_value <= 35:
                    self.channels_dict[str(chan.channel_fk)] = 2
                else:
                    self.channels_dict[str(chan.channel_fk)] = 3
            else:
                self.channels_dict[str(chan.channel_fk)] = 0
        self.channels_dict_sorted = sorted(self.channels_dict.items())
    def get_alerts_with_warnings(self, alerts, alert_days_back):
        # alerts = Alerts.objects.filter(stationday_fk__station_fk=self.station,
        #                                stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(7)).order_by('-alert_text')
        # alerts = Alerts.objects.filter(stationday_fk__station_fk=self.station,
        #                                stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(7)).order_by('-alert_text')
        alerts.filter(stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(alert_days_back)).order_by('-alert_text')
        # alerts.filter(stationday_fk__stationday_date=self.most_recent_stationday.stationday_date).order_by('-alert_text')
        #alerts = Alerts.objects.filter(stationday_fk__station_fk=self.station)
        #self.alerts = alerts.filter(stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(alert_days_back))
        self.alerts_dict = {}
        for alert in alerts:
            # sets the state of warning for each alert according to most recent alert
            # True means there is a warning, False means no warning
            trigger = str(alert).split()[6]
            if trigger not in self.alerts_dict:
                self.alerts_dict[trigger] = str(alert).endswith('triggered')
    def calculate_highest_alert(self):
        self.station_warning_level = 0
        for chan in self.channels_dict:
            self.station_warning_level = max(self.station_warning_level, self.channels_dict[chan])
        for alert in self.alerts_dict:
            self.station_warning_level = max(self.station_warning_level, 3 if self.alerts_dict[alert] else 1)

# Create your views here.
def index(request):
    'Overall view'
    net_stas = Stations.objects.all().order_by('station_name')
    now = datetime.today()
    stations = []
    alerts = Alerts.objects.select_related('stationday_fk','stationday_fk__station_fk').filter(stationday_fk__stationday_date__gte=now - timedelta(60))
    for net_sta in net_stas:
        alert = alerts.filter(stationday_fk__station_fk__station_name=net_sta)
        stations.append(StationOverview(net_sta, alert))
    template = loader.get_template('falcon/overall.html')
    context = {
        'message': (datetime.today() - now).seconds,
        'stations': stations,
    }
    #message = '<br>'.join(stations[10].channels_dict_sorted_keys)
    #return HttpResponse("Hello, world. You're at the 🦅 index. %ss" % (message))
    return HttpResponse(template.render(context, request))

def network_level(request, network='*'):
    'Network view'
    net_stas = Stations.objects.filter(station_name__startswith=network + '_').order_by('station_name')
    now = datetime.today()
    stations = []
    alerts = Alerts.objects.select_related('stationday_fk','stationday_fk__station_fk').filter(stationday_fk__stationday_date__gte=now - timedelta(60))
    for net_sta in net_stas:
        alert = alerts.filter(stationday_fk__station_fk=net_sta)
        stations.append(StationOverview(net_sta, alert))
    template = loader.get_template('falcon/overall.html')
    context = {
        'message': (datetime.today() - now).seconds,
        'stations': stations,
    }
    return HttpResponse(template.render(context, request))
    #return HttpResponse("Hello, you're at the network level for %s." % (network))

def station_level(request, network='*', station='*'):
    'Station view'
    net_stas = Stations.objects.filter(station_name=network + '_' + station).order_by('station_name')
    now = datetime.today()
    stations = []
    for net_sta in net_stas:
        alert = Alerts.objects.filter(stationday_fk__station_fk=net_sta).filter(stationday_fk__stationday_date__gte=now - timedelta(60)).order_by('-alert_text')
        stations.append(StationOverview(net_sta, alert))
    template = loader.get_template('falcon/alerts.html')
    context = {
        'message': (datetime.today() - now).seconds,
        'stations': stations,
        'alerts': alert,
    }
    return HttpResponse(template.render(context, request))
    #return HttpResponse("Hello, you're at the station level for %s_%s." % (network, station))

def channel_level(request, network='*', station='*', channel='*'):
    'Channel view'
    net_stas = Stations.objects.filter(station_name=network + '_' + station).order_by('station_name')
    now = datetime.today()
    stations = []
    for net_sta in net_stas:
        alert = Alerts.objects.filter(stationday_fk__station_fk=net_sta).filter(stationday_fk__stationday_date__gte=now - timedelta(60)).order_by('-alert_text')
        stations.append(StationOverview(net_sta, alert))
    message = []
    for channel, warning_level in stations[0].channels_dict_sorted:
        channel_high_values = ValuesAhl.objects.filter(stationday_fk__station_fk=net_sta,channel_fk__channel=channel).values_list('stationday_fk__stationday_date', 'high_value').order_by('-stationday_fk__stationday_date')
        channel_avg_values = ValuesAhl.objects.filter(stationday_fk__station_fk=net_sta,channel_fk__channel=channel).values_list('stationday_fk__stationday_date', 'avg_value').order_by('-stationday_fk__stationday_date')
        channel_low_values = ValuesAhl.objects.filter(stationday_fk__station_fk=net_sta,channel_fk__channel=channel).values_list('stationday_fk__stationday_date', 'low_value').order_by('-stationday_fk__stationday_date')
        wl = stations[0].channels_dict[channel]
        message.append('%s h:%s a:%.2f l:%d wl:%d' % (channel, str(channel_high_values[0]), channel_avg_values[0][1], channel_low_values[0][1], wl))
    return HttpResponse("Hello, you're at the channel level for %s_%s %s. With %s stations.<br>%s" % (network, station, channel, '<br>'.join(message),'<br>'.join(stations[0].debug)))

def falconer(request):
    netstas = glob.glob('/msd/*_*/2018/087/90_OF[AC].512.seed')
    
    print(len(netstas))
    message = ('There are %d stations with OFC/OFA files.' % len(netstas))
    files = []
    for each in netstas:
        files.append(each.split('/')[2])
    return HttpResponse("Falcon dispatched! 🦅<p>%s<br><br>%s" % (message, '<br>'.join(files)))
