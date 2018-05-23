from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError
from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl, AlertsDisplay, ChannelsDisplay

import glob
import httplib2
import os
import subprocess   
from datetime import date, datetime, timedelta
from dateutil import tz
# from obspy.core import UTCDateTime
import subprocess

shallow_days_back = 10
deep_years_back = 6

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='+', type=str)

    def handle(self, *args, **options):
        for refresh_depth in options['action']:
            try:
                falconer(refresh_depth)
            except Exception as e:
                raise CommandError('Unable to refresh Falcon files on a %s level: %s' % (refresh_depth, e))

def falconer(refresh_depth):
    # stationdate = UTCDateTime.now()
    stationdate = datetime.today()
    backdate = stationdate
    # if refresh_depth == 'cache':
    #     base_url = 'http://igskgacgvmdevwb.cr.usgs.gov/falcon2/'
    #     httplib2.Http().request(base_url)
    #     httplib2.Http().request(base_url + 'IU/')
    #     backdate = stationdate + 1
    if refresh_depth == 'shallow':
        backdate = stationdate - (timedelta(1) * shallow_days_back)
    if refresh_depth == 'deep':
        backdate = datetime(stationdate.year - deep_years_back, stationdate.month, stationdate.day)
    while stationdate >= backdate:
        process_opaque_files(glob.glob('/msd/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%j')))
        process_opaque_files(glob.glob('/tr1/telemetry_days/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%Y_%j')))
        stationdate -= timedelta(1)
    if refresh_depth == 'builddisplay':
        pass
    build_display()

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
        opaque_fmt = datetime.fromtimestamp(os.path.getmtime(opaque)).replace(tzinfo=tz.gettz('UTC'))
        
        staday, _ = Stationdays.objects.get_or_create(station_fk=sta,
                                                      stationday_date=datetime.strptime('%s,%s' % (year, jday), '%Y,%j'))

        # OFC VALUES
        if 'OFC' in opaque_filename and staday.ofc_mod_ts != opaque_fmt:
            
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
        elif 'OFA' in opaque_filename and staday.ofa_mod_ts != opaque_fmt:
            staday.ofa_mod_ts = opaque_fmt
            staday.save()

            # also add the alert to the alerts table
            alerts = subprocess.getoutput(ofadump % ('f', opaque)).split('\n')
            if alerts != ['']:
                for alert in alerts:
                    try:
                        alert = alert.split()
                        alert_dt = datetime.strptime(' '.join((alert[1],alert[2])),'%Y/%m/%d %H:%M:%S')
                        alert_channel = alert[3] if alert[3] == alert[-6] else ' '.join((alert[3],alert[-6]))
                        is_triggered = alert[-1] == 'triggered'
                        alert_obj, _ = Alerts.objects.get_or_create(stationday_fk=staday, alert=alert_channel, alert_ts=alert_dt, triggered=is_triggered)
                    except MultipleObjectsReturned:
                        # there are a few times where there are multiple rows with the same data
                        # these are not duplicates; the important part is that they're alread inserted
                        pass
                    except Exception as e:
                        print('!! %s' % e, staday, alert)

def build_display():
    'Queries the most recent alerts and channels to build the view'
    #ALERTS; first truncate the table and then repopulate
    try:
        #this is dirty, but otherwise the command won't execute
        AlertsDisplay.objects.raw('TRUNCATE alerts_display RESTART IDENTITY')[0]
    except:
        pass
    finally:
        for net_sta in Stations.objects.all():
            alerts = Alerts.objects.filter(stationday_fk__station_fk=net_sta).order_by('alert','-alert_ts').distinct('alert')
            # add OFC alert, checking if filemodtime is recent
            latest_ofc_filemodtime = Stationdays.objects.filter(station_fk=net_sta).order_by('-stationday_date').first().ofc_mod_ts
            if latest_ofc_filemodtime < datetime.combine(date.today(), datetime.min.time()):
                alert_warning_level = 3
            else:
                alert_warning_level = 1
            alert = 'OFC'
            alert_value = latest_ofc_filemodtime.strftime('%Y-%m-%d (%j) %H:%M:%S UTC')
            alerts_disp_obj, _ = AlertsDisplay.objects.get_or_create(station_fk=net_sta,
                                                                     alert=alert,
                                                                     alert_warning_level=alert_warning_level,
                                                                     alert_value=alert_value
                                                                     )
            # add the other alerts, if any
            for alert in alerts:
                alerts_disp_obj, _ = AlertsDisplay.objects.get_or_create(station_fk=net_sta,
                                                                         alert=alert.alert,
                                                                         alert_warning_level=3 if alert.triggered else 1,
                                                                         alert_value=str(alert.triggered)
                                                                         )
    #CHANNELS; first truncate the table and then repopulate
    try:
        #this is dirty, but otherwise the command won't execute
        ChannelsDisplay.objects.raw('TRUNCATE channels_display RESTART IDENTITY')[0]
    except:
        pass
    finally:
        for net_sta in Stations.objects.all():
            channels = ValuesAhl.objects.filter(stationday_fk__station_fk=net_sta).order_by('channel_fk__channel','-stationday_fk__stationday_date').distinct('channel_fk__channel')
            # alerts = Alerts.objects.filter(stationday_fk__station_fk=net_sta).order_by('alert','-stationday_fk__stationday_date').distinct('alert')
            for channel in channels:
                # set channel warning levels
                # Battery Voltages (B1V...B12V) usually stay around 13v
                if channel.channel_fk.channel[0] == 'B' and channel.channel_fk.channel[-1] == 'V' and channel.channel_fk.channel[1:-1].isdigit():
                    if 11 <= channel.low_value <= 15 and 11 <= channel.high_value <= 15:
                        chan_warn_level = 1
                    elif 10 <= channel.low_value <= 16 and 10 <= channel.high_value <= 16:
                        chan_warn_level = 2
                    else:
                        chan_warn_level = 3
                # Battery Voltages (B1V...B12V) usually stay around 13v
                elif channel.channel_fk.channel[0:3] == 'DCV':
                    if 21 <= channel.low_value <= 30 and 21 <= channel.high_value <= 30:
                        chan_warn_level = 1
                    elif 19 <= channel.low_value <= 35 and 19 <= channel.high_value <= 35:
                        chan_warn_level = 2
                    else:
                        chan_warn_level = 3
                else:
                    chan_warn_level = 0
                channels_disp_obj, _ = ChannelsDisplay.objects.get_or_create(station_fk=net_sta,
                                                                         channel=channel.channel_fk.channel,
                                                                         channel_warning_level=chan_warn_level,
                                                                         channel_value='%.2f' % channel.avg_value
                                                                         )