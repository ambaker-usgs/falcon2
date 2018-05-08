from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template import loader
from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl
from falcon.forms.userscale import UserScalingForm

import json
import glob
import itertools
import subprocess
from datetime import datetime, timedelta
from multiprocessing import pool

threadcount = 10

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
        ## alerts.filter(stationday_fk__stationday_date__gte=self.most_recent_stationday.stationday_date - timedelta(alert_days_back)).order_by('-alert_text')
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

def process_stations(net_sta):
    before_t = datetime.now()
    alert = Alerts.objects.filter(stationday_fk__station_fk__station_name=net_sta).filter(stationday_fk__stationday_date__gte=before_t - timedelta(60)).order_by('-alert_text')[:100]
    during = datetime.today()
    stn = StationOverview(net_sta, alert)
    after = datetime.today()
    # if (during - before_t).seconds >= 1.0 or (after - during).seconds >= 1.0:
    #     print('\t%s' % net_sta.station_name)
    #     print('\tAlerts rcvd:  %.2f' % (during - before_t).seconds)
    #     print('\tStation objd: %.2f' % (after - during).seconds)
    #     print('\tAlerts ct:    %d' % alert.count())
    #     print()
    return stn

# Create your views here.
def index(request):
    'Overall view'
    overall_time = datetime.today()
    net_stas = Stations.objects.all().order_by('station_name')
    now = datetime.today()
    stations = []
    # alerts = Alerts.objects.select_related('stationday_fk','stationday_fk__station_fk').filter(stationday_fk__stationday_date__gte=now - timedelta(60))
    alerts_gotten = datetime.today()
    # mp_pool = pool.Pool(threadcount)
    # stations = mp_pool.map(process_stations, net_stas)
    for net_sta in net_stas:
        stations.append(process_stations(net_sta))
    # for net_sta in net_stas:
    #     before_t = datetime.now()
    #     alert = alerts.filter(stationday_fk__station_fk__station_name=net_sta).filter(stationday_fk__stationday_date__gte=now - timedelta(60)).order_by('-alert_text')
    #     during = datetime.now()
    #     stations.append(StationOverview(net_sta, alert))
    #     after = datetime.now()
    #     if (during - before_t).seconds >= 1.0 or (after - during).seconds >= 1.0:
    #         print('\t%s' % net_sta.station_name)
    #         print('\tAlerts rcvd:  %.2f' % (during - before_t).seconds)
    #         print('\tStation objd: %.2f' % (after - during).seconds)
    #         print('\tAlerts ct:    %d' % alert.count())
    #         print()
    template = loader.get_template('falcon/overall.html')
    context = {
        'message': (datetime.today() - now).seconds,
        'stations': stations,
    }
    #message = '<br>'.join(stations[10].channels_dict_sorted_keys)
    #return HttpResponse("Hello, world. You're at the 🦅 index. %ss" % (message))
    # print('Overall time: %.2f seconds' % (datetime.today() - overall_time).seconds)
    # print('Stations gtn: %.5f seconds' % (now - overall_time).seconds)
    # print('Alerts gottn: %.5f seconds' % (alerts_gotten - now).seconds)
    return HttpResponse(template.render(context, request))

def network_level(request, network='*'):
    'Network view'
    net_stas = Stations.objects.filter(station_name__startswith=network + '_').order_by('station_name')
    now = datetime.today()
    stations = []
    alerts = Alerts.objects.select_related('stationday_fk','stationday_fk__station_fk').filter(stationday_fk__stationday_date__gte=now - timedelta(60))
    for net_sta in net_stas:
        alert = alerts.filter(stationday_fk__station_fk=net_sta).filter(stationday_fk__stationday_date__gte=now - timedelta(60)).order_by('-alert_text')
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


def api_channel_data(request, network, station, channel):
    """
    Grab data for a specific Channel
    """
    if request.method == 'GET':
        fields_raw = request.GET.get('fields')
        start_date_raw = request.GET.get('startdate')
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d') if start_date_raw else datetime.now() - timedelta(60)
        start_date = datetime(year=start_date.year, month=start_date.month, day=start_date.day, hour=0, minute=0, second=0)  # Remove time
        end_date_raw = request.GET.get('enddate')
        end_date = datetime.strptime(end_date_raw, '%Y-%m-%d') if end_date_raw else datetime.now()
        end_date = datetime(year=end_date.year, month=end_date.month, day=end_date.day, hour=0, minute=0, second=0)  # remove time
        ymin = request.GET.get('ymin')
        ymax = request.GET.get('ymax')
        kwdates = {'stationday_fk__stationday_date__gte': start_date, 'stationday_fk__stationday_date__lte': end_date}
        stationobj = get_object_or_404(Stations, station_name=network + '_' + station)
        if fields_raw:
            fields = fields_raw.split(',')
        else:
            fields = ['high', 'low', 'avg']
        plot_data = {'network': network,
                     'station': station,
                     'channel': channel,
                     'startdate': start_date.strftime('%Y-%m-%d'),
                     'enddate': end_date.strftime('%Y-%m-%d'),
                     'ymin': ymin,
                     'ymax': ymax,
                     'data': []}
        if channel.endswith('V'):
            plot_data['units'] = 'Volts DC'
        else:
            plot_data['units'] = 'Whatever this is?'
        if 'alert' in fields:
            alert_values = Alerts.objects.filter(stationday_fk__station_fk=stationobj).values_list('stationday_fk__stationday_date', 'alert_text').order_by('-stationday_fk__stationday_date')
            alerts = []
            for date, alert in alert_values:
                alerts.append({'date': str(date), 'value': alert})
            plot_data['alerts'] = alerts
        if 'high' in fields or 'low' in fields or 'avg' in fields:
            channel_values = ValuesAhl.objects.filter(**kwdates).filter(stationday_fk__station_fk=stationobj, channel_fk__channel=channel).values_list('stationday_fk__stationday_date', 'high_value', 'avg_value', 'low_value').order_by('-stationday_fk__stationday_date')
            high_values = []
            avg_values = []
            low_values = []
            for date, high_value, avg_value, low_value in channel_values.all():
                high_values.append({'date': date.strftime('%Y-%m-%d'), 'value': high_value})
                avg_values.append({'date': date.strftime('%Y-%m-%d'), 'value': avg_value})
                low_values.append({'date': date.strftime('%Y-%m-%d'), 'value': low_value})
            if 'avg' in fields:
                plot_data['data'].append({'id': 'Average', 'values': avg_values})
            if 'high' in fields:
                plot_data['data'].append({'id': 'High', 'values': high_values})
            if 'low' in fields:
                plot_data['data'].append({'id': 'Low', 'values': low_values})
    else:
        plot_data = {'error': 'unknown request'}
    return JsonResponse(plot_data)


def channel_level(request, network, station, channel):
    parameters = request.GET.dict()
    # process_opaque_files(glob.glob('/msd/%s/%s/90_OF[AC].512.seed' % ('-'.join([network, station]), stationdate.strftime('%Y/%j'))))
    # process_opaque_files(glob.glob('/tr1/telemetry_days/%s/%s/90_OF[AC].512.seed' % ('-'.join([network, station]), stationdate.strftime('%Y/%Y_%j'))))
    return render(request, 'falcon/channel.html',
                  {'network': network,
                   'station': station,
                   'channel': channel,
                   'parameters': parameters,
                   'userscalingform': UserScalingForm()
                   })


# def process_opaque_files(opaque_files):
#     'Pass the files to ofadump and extract the necessary parameters for database insertion'
#     ofadump = '/data/www/falcon/asl-station-processor/falcon/ofadump -%s %s'
#
#     for opaque in opaque_files:
#         tmp = opaque.split('/')
#         opaque_fp = tmp[-5]
#         net_sta = tmp[-4]
#         year = tmp[-3]
#         jday = tmp[-2].split('_')[-1]
#         opaque_filename = tmp[-1]
#         # get or create Station
#         sta, _ = Stations.objects.get_or_create(station_name=net_sta)
#
#         # update or create Stationday, lastly update for OFA/OFC file mod times
#         # staday_id, _ = Stationdays.objects.get_or_create(station_fk=sta_id,
#         #                                                  stationday_date=UTCDateTime('%s,%s' % (year, jday)).date)
#         opaque_fmt = datetime.fromtimestamp(os.path.getmtime(opaque)).replace(tzinfo=tz.gettz('UTC'))
#
#         staday, _ = Stationdays.objects.get_or_create(station_fk=sta,
#                                                              stationday_date=UTCDateTime('%s,%s' % (year, jday)).datetime)
#
#         # OFC VALUES
#         if 'OFC' in opaque_filename:
#
#             staday.ofc_mod_ts = opaque_fmt
#             staday.save()
#             # Stationdays.objects.update(stationday_id=staday.stationday_id,
#             #                                            ofc_mod_ts=opaque_fmt)
#
#             # also add the channels to the channels table
#             chans = subprocess.getoutput(ofadump % ('c', opaque)).split('\n')
#             for chan in chans:
#                 channel, _ = Channels.objects.get_or_create(channel=chan)
#
#             # also add the values to the values table, linking with the appropriate channel table entry
#             vals = subprocess.getoutput(ofadump % ('f', opaque))
#             values_dict = {}
#             # first, gather all the values
#             for chans in vals.split('description:')[1:]:
#                 lines = chans.split('\n')
#                 chan = lines[0].strip()
#                 values_dict[chan] = [[],[],[]]
#                 for line in lines:
#                     line = line.split()
#                     if '|' in line and 'Timestamp' not in line:
#                         # print(channel, line)
#                         values_dict[chan][0].append(int(line[4]))  #average
#                         values_dict[chan][1].append(int(line[6]))  #high
#                         values_dict[chan][2].append(int(line[8]))  #low
#             # then, get the average, high, and low values
#             for chan in values_dict:
#                 val_avg = sum(values_dict[chan][0])/len(values_dict[chan][0])
#