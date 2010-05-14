# -*- coding: utf-8 -*-

from optparse import make_option

from django.core.management.base import BaseCommand
from vz_backup.models import backup_all
from vz_backup.models import BackupObject


class Command(BaseCommand):
    
    option_list = BaseCommand.option_list
    if '--verbosity' not in [opt.get_opt_string() for opt in BaseCommand.option_list]:
        option_list += (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        )

    help = "Adds application to backups"

    def handle(self, *args, **options):
        backup_all()
