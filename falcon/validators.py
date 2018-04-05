from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

valid_network_codes = ['CU','GS','GT','IC','IU','IW','NE','US','XX']

def is_uppercase(value):
    if value.upper() != value:
        raise ValidationError(
            _('"%(value)s" is not uppercase'),
            params={'value': value},
        )

def valid_netsta_code(value):
    if '_' not in value:
        print('(!!) Invalid network-station code; please form like IU_ANMO')
        raise ValidationError(
            _('"%(value)" is not a valid network-station code (please form like "IU_ANMO")\nplease see Adam Baker if you feel this is in error'),
            params={'value': value,}
        )
    net, sta = value.split('_')
    if len(net) != 2:
        print('(!!) Invalid length of network code; it must be 2 letters long')
        raise ValidationError(
            _('"%(value)s" is not a valid network code (%(network_code)s)\nplease see Adam Baker if you feel this is in error'),
            params={'value': value,
                    'network_codes': net},
        )
    if len(sta) < 3 or len(sta) > 5:
        print('(!!) Invalid length of station code; it must be 3, 4, or 5 letters long')
        raise ValidationError(
            _('"%(value)s" is not a valid station code (%(station_codes)s)\nplease see Adam Baker if you feel this is in error'),
            params={'value': value,
                    'station_codes': sta},
        )
    if net.upper() not in valid_network_codes:
        print('(!!) Chanlist Error: Incorrect network code submission attempted')
        raise ValidationError(
            _('"%(value)s" is not a valid network code (%(network_codes)s)\nplease see Adam Baker if you feel this is in error'),
            params={'value': value,
                    'network_codes': ', '.join(valid_network_codes)},
        )