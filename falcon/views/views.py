from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, get_list_or_404, get_object_or_404
from django.template import loader
from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl, AlertsDisplay, ChannelsDisplay
from falcon.forms.userscale import UserScalingForm

import concurrent.futures
import json
import glob
import itertools
import subprocess
from datetime import date, datetime, timedelta
from multiprocessing import pool

def process_stations(station_objects=Stations.objects.all().order_by('station_name') ):
    'Processes the given stations objects to gather the stations information'
    if station_objects.count() == 0:
        raise Http404
    for net_sta in station_objects:
        net_sta.net_code, net_sta.sta_code = net_sta.station_name.split('_')
        alerts_disp = AlertsDisplay.objects.filter(station_fk=net_sta).exclude(alert__istartswith='B',alert__iendswith='V')
        channels_disp = ChannelsDisplay.objects.filter(station_fk=net_sta)
        net_sta.alerts = alerts_disp
        net_sta.channels = channels_disp
        #get overall station warning level
        net_sta.station_warning_level = 0
        for alert in alerts_disp:
            net_sta.station_warning_level = max(net_sta.station_warning_level, alert.alert_warning_level)
            if alert.alert == 'OFC':
                alert_dt = datetime.strptime(alert.alert_value.replace(' UTC',''),'%Y-%m-%d (%j) %H:%M:%S')
        for channel in channels_disp:
            net_sta.station_warning_level = max(net_sta.station_warning_level, channel.channel_warning_level)
    return station_objects

def get_legend(station_objects):
    'Returns a legend as a list of [alarm, description of alarm]'
    legend = []
    legend_alarms = AlertsDisplay.objects.filter(station_fk__in=station_objects).order_by('alert').distinct('alert').values_list('alert')
    legend_channels = ChannelsDisplay.objects.filter(station_fk__in=station_objects).order_by('channel').distinct('channel').values_list('channel')
    for alarm in legend_alarms:
        alarm = alarm[0]
        try:
            description = Channels.objects.get(channel=alarm).description
        except ObjectDoesNotExist:
            description = 'unknown'
        legend.append([alarm, description])
    for channel in legend_channels:
        channel = channel[0]
        try:
            description = Channels.objects.get(channel=channel).description
        except ObjectDoesNotExist:
            description = 'unknown'
        legend.append([channel, description])
    return sorted(legend)

def get_most_recent_update(station_objects):
    'Returns a datetime object of the most recent OFC/OFA file modified time'
    ofc = Stationdays.objects.filter(station_fk__in=station_objects).exclude(ofc_mod_ts=None).order_by('-ofc_mod_ts').first().ofc_mod_ts
    ofa = Stationdays.objects.filter(station_fk__in=station_objects).exclude(ofa_mod_ts=None).order_by('-ofa_mod_ts').first().ofa_mod_ts
    return max(ofc, ofa)

# Create your views here.
def index(request):
    'Overall view'
    now = datetime.today()
    net_stas = process_stations()
    legend = get_legend(net_stas)
    most_recent_update = get_most_recent_update(net_stas)
    template = loader.get_template('falcon/legend.html')
    context = {
        'message': str(datetime.today() - now),
        'timestamp': most_recent_update.strftime('%Y-%m-%d (%j) %H:%M:%S UTC'),
        'stations': net_stas,
        'legend': legend,
    }
    return HttpResponse(template.render(context, request))

def network_level(request, network='*'):
    'Network view'
    now = datetime.today()
    net_stas = Stations.objects.filter(station_name__istartswith=network).order_by('station_name')
    net_stas = process_stations(net_stas)
    legend = get_legend(net_stas)
    most_recent_update = get_most_recent_update(net_stas)
    template = loader.get_template('falcon/legend.html')
    context = {
        'message': str(datetime.today() - now),
        'timestamp': most_recent_update.strftime('%Y-%m-%d (%j) %H:%M:%S UTC'),
        'stations': net_stas,
        'legend': legend,
    }
    return HttpResponse(template.render(context, request))

def station_level(request, network='*', station='*'):
    'Station view'
    now = datetime.today()
    net_stas = Stations.objects.filter(station_name__istartswith=network,station_name__iendswith=station)
    net_stas = process_stations(net_stas)
    legend = get_legend(net_stas)
    most_recent_update = get_most_recent_update(net_stas)
    alerts = Alerts.objects.filter(stationday_fk__station_fk=net_stas[0]).order_by('-alert_ts')[:100]
    template = loader.get_template('falcon/legend.html')
    context = {
        'message': str(datetime.today() - now),
        'timestamp': most_recent_update.strftime('%Y-%m-%d (%j) %H:%M:%S UTC'),
        'stations': net_stas,
        'legend': legend,
        'alerts': alerts,
    }
    return HttpResponse(template.render(context, request))
        

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
        channel_obj = Channels.objects.get(channel=channel)
        plot_data['units'] = channel_obj.units
        plot_data['description'] = channel_obj.description
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
    return render(request, 'falcon/channel.html',
                  {'network': network,
                   'station': station,
                   'channel': channel,
                   'parameters': parameters,
                   'userscalingform': UserScalingForm()
                   })