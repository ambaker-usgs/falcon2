from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl

import glob
import os
import subprocess
from datetime import datetime, timedelta
from dateutil import tz
from multiprocessing import Pool

class StationOverview(object):
    def __init__(self, netsta, alerts, alert_days_back=15):
        self.station = Stations.objects.get(station_name=netsta)
        print('%s %s %s' % ('-' * 20, netsta, '-'*20))
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
            # Direct Current Voltage, usually stays around 24v
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
        alerts = alerts.order_by('-alert_text')
        self.alerts_dict = {}
        latest_ofc_file_date = Stationdays.objects.filter(station_fk=self.station).order_by('-stationday_date')[0].stationday_date
        self.alerts_dict['OFC'] = latest_ofc_file_date <= (datetime.today() - timedelta(1))
        for alert in alerts:
            # sets the state of warning for each alert according to most recent alert
            # True means there is a warning, False means no warning
            trigger = str(alert).split()[6]
            if self.alerts_dict and (trigger not in self.alerts_dict):
                self.alerts_dict[trigger] = str(alert).endswith('triggered')
    def calculate_highest_alert(self):
        self.station_warning_level = 0
        if self.channels_dict:
            self.station_warning_level = max(self.station_warning_level, max(self.channels_dict.values()))
        if self.alerts_dict:
            self.station_warning_level = max(self.station_warning_level, 3 if max(self.alerts_dict.values()) else 1)
        print(self.station, self.station_warning_level, '=', self.alerts_dict.values(), max(self.alerts_dict.values()), 3 if max(self.alerts_dict.values()) else 1)

# Create your views here.
def index(request):
    'Overall view'
    net_stas = Stations.objects.all().order_by('station_name')
    now = datetime.today()
    print('Number of stations: %d' % len(net_stas))
    stations = []
    alerts = Alerts.objects.select_related('stationday_fk','stationday_fk__station_fk').filter(stationday_fk__stationday_date__gte=now - timedelta(60))
    for net_sta in net_stas:
        station_alerts = alerts.filter(stationday_fk__station_fk__station_name=net_sta)
        stations.append(StationOverview(net_sta, station_alerts))
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
    net_sta = Stations.objects.filter(station_name=network + '_' + station).order_by('station_name')[0]
    now = datetime.today()
    stations = []
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
    process_opaque_files(glob.glob('/msd/%s/%s/90_OF[AC].512.seed' % ('-'.join([network, station]), stationdate.strftime('%Y/%j'))))
    process_opaque_files(glob.glob('/tr1/telemetry_days/%s/%s/90_OF[AC].512.seed' % ('-'.join([network, station]), stationdate.strftime('%Y/%Y_%j'))))
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

def process_opaque_files(opaque_files):
    'Pass the files to ofadump and extract the necessary parameters for database insertion'
    ofadump = '/data/www/falcon/asl-station-processor/falcon/ofadump -%s %s'
    
    for opaque in opaque_files:
        tmp = opaque.split('/')
        opaque_fp = tmp[-5]
        net_sta = tmp[-4]
        year = tmp[-3]
        jday = tmp[-2].split('_')[-1]
        opaque_filename = tmp[-1]
        # get or create Station
        # sta, _ = Stations.objects.get_or_create(station_name=net_sta)
        
        # update or create Stationday, lastly update for OFA/OFC file mod times
        # staday_id, _ = Stationdays.objects.get_or_create(station_fk=sta_id,
        #                                                  stationday_date=UTCDateTime('%s,%s' % (year, jday)).date)
        opaque_fmt = datetime.fromtimestamp(os.path.getmtime(opaque)).replace(tzinfo=tz.gettz('UTC'))
        
        staday, _ = Stationdays.objects.get_or_create(station_fk__station_name=net_sta,
                                                             stationday_date=datetime.strptime('%s,%s' % (year, jday), '%Y,%j'))

        # OFC VALUES
        if 'OFC' in opaque_filename:
            
            staday.ofc_mod_ts = opaque_fmt
            staday.save()
            # Stationdays.objects.update(stationday_id=staday.stationday_id,
            #                                            ofc_mod_ts=opaque_fmt)
            
            # also add the channels to the channels table
            chans = subprocess.getoutput(ofadump % ('c', opaque)).split('\n')
            for chan in chans:
                channel, _ = Channels.objects.get_or_create(channel=chan)
            
            # also add the values to the values table, linking with the appropriate channel table entry
            vals = subprocess.getoutput(ofadump % ('f', opaque))
            values_dict = {}
            # first, gather all the values
            for chans in vals.split('description:')[1:]:
                lines = chans.split('\n')
                chan = lines[0].strip()
                values_dict[chan] = [[],[],[]]
                for line in lines:
                    line = line.split()
                    if '|' in line and 'Timestamp' not in line:
                        # print(channel, line)
                        values_dict[chan][0].append(int(line[4]))  #average
                        values_dict[chan][1].append(int(line[6]))  #high
                        values_dict[chan][2].append(int(line[8]))  #low
            # then, get the average, high, and low values
            for chan in values_dict:
                val_avg = sum(values_dict[chan][0])/len(values_dict[chan][0])
                val_high = max(values_dict[chan][0])
                val_low = min(values_dict[chan][0])
                
                # find appropriate channel and add to values table
                channel, _ = Channels.objects.get_or_create(channel=chan)
                
                value, _ = ValuesAhl.objects.get_or_create(stationday_fk=staday,
                                                                channel_fk=channel)
                value.stationday_fk = staday
                value.channel_fk = channel
                value.avg_value = val_avg
                value.high_value = val_high
                value.low_value = val_low
                value.save()
        # OFA ALERTS
        elif 'OFA' in opaque_filename:
            staday.ofa_mod_ts = opaque_fmt
            staday.save()

            # also add the alert to the alerts table
            alerts = subprocess.getoutput(ofadump % ('f', opaque)).split('\n')
            for alert in alerts:
                alert_obj, _ = Alerts.objects.get_or_create(stationday_fk=staday, alert_text=alert)

