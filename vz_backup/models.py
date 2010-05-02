# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.commands import dumpdata
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, pre_delete

import datetime
import os
import time

from vz_backup import exceptions
from vz_backup.signals import unlink_archive, check_auto_prune

try:
    INDENT = settings.VZ_BACKUP_INDENT
except AttributeError:
    INDENT = 4

try:
    FORMAT = settings.VZ_BACKUP_FORMAT
except AttributeError:
    FORMAT = 'json'

PRUNE_CHOICES = (
    ('count', 'Count'),
    ('size', 'Size'),
    ('time', 'Time'),
)

COMPRESS_CHOICES = (
    ('bz2', 'bz2'),
    ('gz', 'gz'),
    ('none', 'none'),
)


class BackupObject(models.Model):
    """
    Backup Object

    Manages app backups.  Apps are added via management command.
    """

    app_label = models.CharField(blank=True, max_length=100, unique=True)
    include = models.BooleanField(default=True,
        help_text='Include this app when performing backup?')
    use_natural_keys = models.BooleanField(default=True)
    compress = models.CharField(max_length=4, choices=COMPRESS_CHOICES, default='none')
    prune_by = models.CharField(max_length=4, choices=PRUNE_CHOICES,
        default='count',
        help_text='What factor leads to archive file deletion?')
    prune_value = models.PositiveIntegerField(blank=True, null=True,
        default=10)
    auto_prune = models.BooleanField(default=False,
        help_text="Prune after backup?")
    send_to_admins = models.BooleanField(default=True)
    created = models.DateTimeField(blank=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, auto_now=True)

    def prune(self):
        """
        Prune

        Depends on prune_by.

        If prune_by is "count", prune_value is number of BackupArhchives
        to keep.  Find totalBackupArchives for this BackupObject that
        are not marked "keep".  Delete all BackupArchives not marked
        "keep" for BackupObject older than BackupArchives[count-1].

        If prune_by is "size", prune_value is total size of
        BackupArchive files not marked "keep" in kilo bytes.  If total
        is greater than prune_value, get ids of BackupArchives where
        size of this list - total is less than prune_value.  Delete
        BackupArchives with selected ids.

        If prune_by is "time", prune_value is number of days to keep
        BackupArchive files not marked "keep".  Find all BackupArchives
        older than today - prune_value, delete them.
        """

        if self.prune_by == 'count':

            if BackupArchive.objects.filter(backup_object=self,
                keep=False).count() > count:
                last_backup = BackupArchive.objects.filter(backup_object=self,
                    keep=False).only('created')[self.prune_value-1]
                BackupArchive.objects.filter(
                    backup_object=self,
                    keep=False,
                    created__lt=last_backup.created).delete()

        elif self.prune_by == 'size':

            prune_value = self.prune_value * 1000
            qs = BackupArchive.objects.filter(backup_object=self,
                keep=False).aggregate(Sum('size'))
            size = qs['size__sum']
            ids = list()
            start = 0
            while size > prune_value:
                archive = BackupArchive.objects.filter(
                    backup_object=self, keep=False).only(
                    'id', 'size', 'created').order_by('created')[start]
                ids.append(archive.id)
                start = start + 1
                size = size - archive.size
            BackupArchive.objects.filter(id__in=ids).delete()

        elif self.prune_by == 'time':

            delta = datetime.timedelta(days=self.prune_value)
            threshold = datetime.today() - delta
            BackupArchive.objects.filter(
                backup_object=self, keep=False, created__lt=threshold).delete()

    def backup(self, notes=None):
        dt = datetime.datetime.now()
        name = u'%s_%s%s.%s' % (self.app_label, dt.strftime('%Y%j-'),
            int(time.time()), FORMAT)

        if self.compress == 'gz':
            from gzip import GzipFile
            name = name + u'.gz'
        elif self.compress == 'bz2':
            from bz2 import BZ2File
            name = name + u'.bz2'

        path = os.path.join(settings.VZ_BACKUP_DIR, name)
        try:
            if self.compress == 'gz':
                b_file = GzipFile(path, 'wb')
            elif self.compress == 'bz2':
                b_file = BZ2File(path, 'w')
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

pre_delete.connect(unlink_archive, sender=BackupArchive)
post_save.connect(check_auto_prune, sender=BackupArchive)
