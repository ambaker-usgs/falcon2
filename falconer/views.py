from django.http import HttpResponse
from django.shortcuts import render
from dateutil import tz

import glob
import os
import subprocess
from datetime import date, datetime
from obspy.core import UTCDateTime

from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl

# Create your views here.

def falconer(request):
    stationdate = UTCDateTime.now()
    stationdate = UTCDateTime('%s,%s' % (UTCDateTime.now().year - 4, UTCDateTime.now().strftime('%j')))
    while stationdate >= UTCDateTime('%s,%s' % (UTCDateTime.now().year - 8, UTCDateTime.now().strftime('%j'))):
        print(stationdate.strftime('%Y,%j'))    #debug
        process_opaque_files(glob.glob('/msd/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%j')))
        process_opaque_files(glob.glob('/tr1/telemetry_days/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%Y_%j')))
        stationdate -= 86400
    return HttpResponse("A falcon has been dispatched! 🦅")

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
        sta, _ = Stations.objects.get_or_create(station_name=net_sta)
        
        # update or create Stationday, lastly update for OFA/OFC file mod times
        # staday_id, _ = Stationdays.objects.get_or_create(station_fk=sta_id,
        #                                                  stationday_date=UTCDateTime('%s,%s' % (year, jday)).date)
        opaque_fmt = datetime.fromtimestamp(os.path.getmtime(opaque)).replace(tzinfo=tz.gettz('UTC'))
        
        staday, _ = Stationdays.objects.get_or_create(station_fk=sta,
                                                             stationday_date=UTCDateTime('%s,%s' % (year, jday)).datetime)

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
                # ValuesAhl.objects.update(stationday_fk=staday,
                #                          channel_fk=channel,
                #                          avg_value=val_avg,
                #                          high_value=val_high,
                #                          low_value=val_low)
        # OFA ALERTS
        elif 'OFA' in opaque_filename:
            staday.ofa_mod_ts = opaque_fmt
            staday.save()
            # Stationdays.objects.update(stationday_id=staday.stationday_id,
            #                                            ofa_mod_ts=opaque_fmt)

            # also add the alert to the alerts table
            alerts = subprocess.getoutput(ofadump % ('f', opaque)).split('\n')
            for alert in alerts:
                alert_obj, _ = Alerts.objects.get_or_create(stationday_fk=staday, alert_text=alert)