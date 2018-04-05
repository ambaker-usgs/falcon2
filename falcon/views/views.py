from django.http import HttpResponse
from django.shortcuts import render

from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl

import glob
import subprocess
from datetime import datetime, timedelta

class StationOverview(object):
    def __init__(self, netsta, alert_days_back=15):
        ofadump = '/data/www/falcon/asl-station-processor/falcon/ofadump -%s %s'
        self.station = Stations.objects.get(station_name=netsta)
        self.most_recent_stationday = Stationdays.objects.filter(station_fk=self.station).order_by('-stationday_date')[0]
        self.get_channels_with_warnings()
        # alerts = Alerts.objects.filter(stationday_fk__stationday_date__gte=datetime.today() - timedelta(alert_days_back))
        self.get_alerts_with_warnings(alert_days_back)
    def get_channels_with_warnings(self):
        channels = ValuesAhl.objects.distinct('channel_fk__channel').filter(stationday_fk__station_fk=self.station).order_by('channel_fk__channel')
        self.channels_dict = {}
        for chan in channels:
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
    def get_alerts_with_warnings(self, alert_days_back):
        # alerts = Alerts.objects.filter(stationday_fk__station_fk=self.station,
        #                                stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(7)).order_by('-alert_text')
        alerts = Alerts.objects.filter(stationday_fk__station_fk=self.station,
                                       stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(7)).order_by('-alert_text')
        self.alerts_dict = {}
        for alert in alerts:
            # sets the state of warning for each alert according to most recent alert
            # True means there is a warning, False means no warning
            trigger = str(alert).replace('Indoor t', 'IndoorT').split()[6]
            if trigger not in self.alerts_dict:
                self.alerts_dict[trigger.replace('IndoorT', 'Indoor t')] = 'triggered' == str(alert).split()[-1]

# Create your views here.
def index(request):
    'Overall view'
    net_stas = Stations.objects.all()
    now = datetime.today()
    stations = []
    # alerts = Alerts.objects.filter(stationday_fk__stationday_date__gte=datetime.today() - timedelta(7))
    for net_sta in net_stas:
        stations.append(StationOverview(net_sta))
    msg = (datetime.today() - now).seconds
    return HttpResponse("Hello, world. You're at the 🦅 index. %ss" % (msg))

def network_level(request, network='*'):
    return HttpResponse("Hello, you're at the network level for %s." % (network))

def station_level(request, network='*', station='*'):
    return HttpResponse("Hello, you're at the station level for %s_%s." % (network, station))

def channel_level(request, network='*', station='*', channel='*'):
    return HttpResponse("Hello, you're at the channel level for %s_%s %s." % (network, station, channel))

def falconer(request):
    netstas = glob.glob('/msd/*_*/2018/087/90_OF[AC].512.seed')
    
    print(len(netstas))
    message = ('There are %d stations with OFC/OFA files.' % len(netstas))
    files = []
    for each in netstas:
        files.append(each.split('/')[2])
    return HttpResponse("Falcon dispatched! 🦅<p>%s<br><br>%s" % (message, '<br>'.join(files)))