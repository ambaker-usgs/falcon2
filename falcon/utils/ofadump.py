
import os
import glob
import subprocess
from datetime import datetime
from dateutil import tz
from obspy.core import UTCDateTime

from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl

shallow_days_back = 10
deep_years_back = 8


def falconer(refresh_depth):
    """
    Process seed files for given time span
    :param refresh_depth: Either shallow or deep
    :type refresh_depth: str
    """
    stationdate = UTCDateTime.now()
    if refresh_depth == 'shallow':
        backdate = stationdate - (86400 * shallow_days_back)
    if refresh_depth == 'deep':
        backdate = UTCDateTime('%s,%s' % (stationdate.year - deep_years_back, stationdate.strftime('%j')))
    while stationdate >= backdate:
        process_opaque_files(opaque_files=glob.glob('/msd/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%j')))
        process_opaque_files(opaque_files=glob.glob('/tr1/telemetry_days/*_*/%s/90_OF[AC].512.seed' % stationdate.strftime('%Y/%Y_%j')))
        stationdate -= 86400


def process_opaque_files(opaque_files, ofadump_path=None):
    """
    Pass the files to ofadump and extract the necessary parameters for database insertion
    :param opaque_files: Seed files to process
    :type opaque_files: list of str
    :param ofadump_path: Path to location of ofadump executable
    :type ofadump_path: str
    """
    if ofadump_path is None:
        ofadump = '/data/www/falcon/asl-station-processor/falcon/ofadump -%s %s'
        ofadump = '/home/dwitte/dev/ofadump/ofadump -%s %s'
    else:
        ofadump = ofadump_path + ' -%s %s'

    for opaque in opaque_files:
        tmp = opaque.split('/')
        opaque_fp = tmp[-5]
        net_sta = tmp[-4]
        year = tmp[-3]
        jday = tmp[-2].split('_')[-1]
        opaque_filename = tmp[-1]
        print(net_sta)
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
            print(chans)
            for chan in chans:
                if not Channels.objects.filter(channel=chan).exists():
                    Channels.objects.create(channel=chan, units='Unknown',
                                            description='Unknown channel added from channel data load')

            # also add the values to the values table, linking with the appropriate channel table entry
            vals = subprocess.getoutput(ofadump % ('f', opaque))
            values_dict = {}
            # first, gather all the values
            for chans in vals.split('description:')[1:]:
                lines = chans.split('\n')
                chan = lines[0].strip()
                values_dict[chan] = [[], [], []]
                for line in lines:
                    line = line.split()
                    if '|' in line and 'Timestamp' not in line:
                        # print(channel, line)
                        values_dict[chan][0].append(int(line[4]))  # average
                        values_dict[chan][1].append(int(line[6]))  # high
                        values_dict[chan][2].append(int(line[8]))  # low
            # then, get the average, high, and low values
            for chan in values_dict:
                val_avg = sum(values_dict[chan][0]) / len(values_dict[chan][0])
                val_high = max(values_dict[chan][0])
                val_low = min(values_dict[chan][0])

                # find appropriate channel and add to values table
                channel = Channels.objects.filter(channel=chan).first()
                if not channel:
                    Channels.objects.create(channel=chan, units='Unknown',
                                            description='Unknown channel added from value data load')

                value, _ = ValuesAhl.objects.get_or_create(stationday_fk=staday, channel_fk=channel)
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
