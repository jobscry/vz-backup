# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand

from optparse import make_option

class Command(NoArgsCommand):
    help = 'Check for changes since last backup using each models `latest`'

    def handle(self, **options):
        from vz_backup.models import BackupArchive
        
        pass