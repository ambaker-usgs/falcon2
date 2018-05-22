from django.test import TestCase

# Create your tests here.
from falcon.models import Stations, Stationdays, Channels, Alerts, ValuesAhl
from falcon.views.views import process_opaque_files

import subprocess
import sys
from datetime import datetime

class ModelsTestCase(TestCase):
    def setUp(self):
        self.test_ofc_file = '/msd/IU_ANMO/2013/001/90_OFC.512.seed'
        self.ofadump = '/data/www/falcon/asl-station-processor/falcon/ofadump -%s %s'
    def test_ofadump(self):
        'Tests ofadump with know values'
        # test against the above test_ofc_file since it is not going to change
        known_channel_output = 'B1V\nB2V\nB3V\nB4V\nBT\nDCV\nIHS\nITS'
        exit_code, given_channel_output = subprocess.getstatusoutput(self.ofadump % ('c', self.test_ofc_file))
        self.assertEqual(known_channel_output, given_channel_output)
        self.assertEqual(0, exit_code)
        try:
            fob = open('falcon/IU_ANMO_2013_001_90_OFC_512_SEED_output.txt','r')
            known_values_output = fob.read()
        except:
            sys.stdout.write('Unable to open file: %s' % self.test_ofc_file)
        finally:
            fob.close()
        exit_code, given_values_output = subprocess.getstatusoutput(self.ofadump % ('f', self.test_ofc_file))
        self.assertEqual(known_values_output, given_values_output)
        self.assertEqual(0, exit_code)
    def test_process_opaque_files(self):
        'Test the insertion of data into the database'
        _,_,net_sta,year,jday,_ = self.test_ofc_file.split('/')
        self.assertEqual('IU_ANMO',net_sta)
        self.assertEqual('2013',year)
        self.assertEqual('001', jday)
        test_stationday = datetime.strptime('%s,%s' % (year, jday), '%Y,%j')
        sta, _ = Stations.objects.get_or_create(station_name=net_sta)
        staday, _ = Stationdays.objects.get_or_create(station_fk=sta,stationday_date=test_stationday)
        
        database_stationday = Stationdays.objects.filter(station_fk__station_name=net_sta)
        self.assertEqual(test_stationday.strftime(), database_stationday[0].stationday_date)
        