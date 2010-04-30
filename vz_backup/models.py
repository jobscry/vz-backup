# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.commands import dumpdata
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, pre_delete

import datetime
import gzip
import os
import time

INDENT = 4
FORMAT = 'json'

PRUNE_CHOICES = (
    ('count', 'Count'),
    ('size', 'Size'),
    ('time', 'Time'),
)


class BackupObject(models.Model):
    """Backup Object

    App to be backed up.  All apps from INSTALLED APPS are added upon `syncdb`.

    """

    app_label = models.CharField(blank=True, max_length=100, unique=True)
    include = models.BooleanField(default=True,
        help_text='Include this app when performing backup?')
    use_natural_keys = models.BooleanField(default=True)
    compress = models.BooleanField(default=True)
    prune_by = models.CharField(max_length=4, choices=PRUNE_CHOICES,
        default='count',
        help_text='What factor leads to archive file deletion?')
    prune_value = models.CharField(blank=True, null=True, max_length='255',
        default='10')
    send_to_admins = models.BooleanField(default=True)
    created = models.DateTimeField(blank=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, auto_now=True)

    def prune(self):
        if self.prune_by == 'count':
            count = int(self.prune_value)
            if BackupArchive.objects.filter(backup_object=self,
                keep=False).count() > count:
                last_backup = BackupArchive.objects.filter(backup_object=self,
                    keep=False).only('created')[count-1]
                BackupArchive.objects.filter(
                    backup_object=self,
                    keep=False,
                    created__lt=last_backup.created).delete()
        elif self.prune_by == 'size':
            max_size = int(self.prune_value)
            qs = BackupArchive.objects.filter(backup_object=self,
                keep=False).aggregate(Sum('size'))
            size = qs['size__sum']
            ids = list()
            start = 0
            while size > max_size:
                archive = BackupArchive.objects.filter(
                    backup_object=self).only('id', 'size', 'created').order_by(
                        'created')[start]
                ids.append(archive.id)
                start = start + 1
                size = size - archive.size
            BackupArchive.objects.filter(id__in=ids).delete()
        elif self.prune_by == 'time':
            delta = datetime.timedelta(days=int(self.prune_value))
            threshold = datetime.today() - delta
            BackupArchive.objects.filter(backup_object=self, keep=False, created__lt=threshold).delete()

    def backup(self, notes=None):
        dt = datetime.datetime.now()
        name = u'%s_%s%s.%s' % (self.app_label, dt.strftime('%Y%j-'),
            int(time.time()), FORMAT)

        if self.compress:
            name = name + u'.gz'

        path = os.path.join(settings.VZ_BACKUP_DIR, name)
        try:
            if self.compress:
                b_file = gzip.open(path, 'wb')
            else:
                b_file = open(path, 'w')
            dump = dumpdata.Command()
            b_file.write(dump.handle(
                    self.app_label,
                    use_natural_keys=self.use_natural_keys,
                    indent=INDENT,
                    format=FORMAT))
            b_file.close()
            BackupArchive.objects.create(
                backup_object=self,
                name=name,
                path=path,
                size=os.path.getsize(path),
                notes=notes)
        except IOError:
            pass

    def __unicode__(self):
        return self.app_label


class BackupArchive(models.Model):
    """Backup Archive"""

    backup_object = models.ForeignKey(BackupObject)
    name = models.CharField(blank=True, max_length=100)
    path = models.FilePathField(path=settings.VZ_BACKUP_DIR)
    size = models.BigIntegerField(default=0)
    notes = models.TextField(blank=True, null=True, default='')
    keep = models.BooleanField(default=False)
    edited = models.DateTimeField(blank=True, auto_now=True)
    created = models.DateTimeField(blank=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s on %s" % (self.backup_object, self.created.isoformat())

    class Meta:
        ordering = ['-created']


def backup_all():
    bs = BackupObject.objects.all()
    for b in bs:
        b.backup()

from vz_backup.signals import *

pre_delete.connect(unlink_archive, sender=BackupArchive)
