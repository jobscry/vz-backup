# -*- coding: utf-8 -*-
"""
Heavily 'inspsired' by Django South's convert_to_south command
see: http://south.aeracode.org/browser/south/management/commands/convert_to_south.py
"""

from optparse import make_option
import sys

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.conf import settings
from django.db import models
from django.core import management
from django.core.exceptions import ImproperlyConfigured

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

    def handle(self, app=None, *args, **options):
        
        # Make sure we have an app
        if not app:
            print "Please specify an app to backup."
            return
        
        # See if the app exists
        app = app.split(".")[-1]
        try:
            app_module = models.get_app(app)
        except ImproperlyConfigured:
            print "There is no enabled application matching '%s'." % app
            return
        
        # Try to get its list of models
        model_list = models.get_models(app_module)
        if not model_list:
            print "This application has no models; this command is for applications that already have models syncdb."
            return

        obj, created = BackupObject.objects.get_or_create(app_label=app)
        if not created:
            print "This application is already being backed up."
            return

        obj.backup()
