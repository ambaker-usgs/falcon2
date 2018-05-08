
import glob
from obspy.core import UTCDateTime

from django.core.management.base import BaseCommand, CommandError

from falcon.utils.ofadump import falconer


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='+', type=str)

    def handle(self, *args, **options):
        for refresh_depth in options['action']:
            try:
                falconer(refresh_depth)
            except Exception as e:
                raise CommandError('Unable to %sly refresh Falcon files: %s' % (refresh_depth, e))
