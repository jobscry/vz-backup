# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.core.management.commands import dumpdata
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, pre_delete, pre_save

import datetime
import mimetypes
import os
import time

from vz_backup import generate_file_hash
from vz_backup.exceptions import *
from vz_backup.signals import maintenance_tasks, unlink_archive

INDENT = getattr(settings, 'VZ_BACKUP_INDENT', 4)
FORMAT = getattr(settings, 'VZ_BACKUP_FORMAT', 'json')

PRUNE_CHOICES = (
    ('count', 'Count'),
    ('size', 'Size'),
    ('time', 'Time'),
    ('none', 'None'),
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
    compress = models.CharField(max_length=5, choices=COMPRESS_CHOICES, default='none', db_index=True)
    prune_by = models.CharField(max_length=5, choices=PRUNE_CHOICES,
        default='none',
        help_text='What factor leads to archive file deletion?', db_index=True)
    prune_value = models.FloatField(blank=True, null=True,
        default=10)
    auto_prune = models.BooleanField(default=False,
        help_text="Prune after backup?", db_index=True)
    mail_to = models.ManyToManyField(User, limit_choices_to={'is_superuser': True}, 
        blank=True, null=True, default='', help_text='Select which admin(s) to send new backup archives to.')
    created = models.DateTimeField(blank=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, auto_now=True)


    def __unicode__(self):
        return self.app_label

    @property
    def archives(self):
        return BackupArchive.objects.filter(backup_object__exact=self)


    @property
    def kept_archives(self):
        return self.archives.filter(keep=True)


    @property
    def unkept_archives(self):
        return self.archives.filter(keep=False)


    @property
    def unkept_archives_size(self):
        qs = self.unkept_archives.aggregate(Sum('size'))
        if qs['size__sum'] is None:
            return 0
        return qs['size__sum']


    @property
    def archives_size(self):
        qs = self.archives.aggregate(Sum('size'))
        if qs['size__sum'] is None:
            return 0
        return qs['size__sum']


    @property
    def last_archive(self):
        return self.archives[0]


    @property
    def last_kept_archive(self):
        return self.kept_archives[0]


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

        If prune_by is "none", don't prune
        """
        unkept = self.unkept_archives

        if self.prune_by == 'count':
            prune_value = int(self.prune_value)
            if unkept.count() > prune_value:
                last_backup = unkept.all()[prune_value-1]
                BackupArchive.objects.filter(
                    backup_object=self,
                    keep=False,
                    created__lt=last_backup.created).delete()

        elif self.prune_by == 'size':

            prune_value = self.prune_value * 1000

            ids = list()
            start = 0
            size = self.unkept_archives_size
            while size > prune_value:
                archive = unkept.order_by('created')[start]
                ids.append(archive.id)
                start = start + 1
                size = size - archive.size
            BackupArchive.objects.filter(id__in=ids).delete()

        elif self.prune_by == 'time':

            delta = datetime.timedelta(days=self.prune_value)
            threshold = datetime.date.today() - delta
            BackupArchive.objects.filter(
                backup_object=self, keep=False, created__lt=threshold).delete()

        else:
            pass


    def backup(self):
        dt = datetime.datetime.now()
        name = u'%s_%s%s.%s' % (self.app_label, dt.strftime('%Y%j-'), dt.microsecond, FORMAT)

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

            file_hash = generate_file_hash(path)
            try:
                ba = BackupArchive.objects.get(file_hash__exact=file_hash, backup_object__exact=self)
                os.unlink(path)
            except BackupArchive.DoesNotExist:
                BackupArchive.objects.create(
                    backup_object=self,
                    name=name,
                    path=path,
                    size=os.path.getsize(path),
                    file_hash=file_hash)

        except IOError:
            raise UnableToCreateArchive


    def mail(self, which=None, fail_silently=True):
        if self.mail_to.count() > 0:
            message = EmailMessage(
                subject=u'%s backup manager %s'%(settings.EMAIL_SUBJECT_PREFIX, self),
                to=self.mail_to.values_list('email', flat=True)
            )
            if which is None:
                ba = BackupArchive.objects.filter(backup_object=self).only('backup_object', 'path', 'created').latest()
            else:
                ba = BackupArchive.objects.get(id__exact=which)

            message.body='sha1 has for archive is: %s'%ba.file_hash
            message.attach_file(ba.path, mimetypes.guess_type(ba.path)[0])
            message.send()

    def reload(self, which):
        ba = BackupArchive.objects.only('backup_object', 'id', 'path').get(backup_object=self, id__exact=which)
        if ba.file_hash != generate_file_hash(ba.path):
            raise ArchiveHashesDoNotMatch

        call_command('reset', self.app_label, interactive=False)
        call_command('loaddata', ba.path, verbosity=0)


class BackupArchive(models.Model):
    """Backup Archive"""

    backup_object = models.ForeignKey(BackupObject, editable=False)
    name = models.CharField(blank=True, max_length=100, editable=False)
    path = models.FilePathField(path=settings.VZ_BACKUP_DIR, editable=False)
    size = models.BigIntegerField(default=0, editable=False, db_index=True)
    file_hash = models.CharField(max_length=40, editable=False, default='', null=True, blank=True, db_index=True)
    keep = models.BooleanField(default=False, db_index=True)
    edited = models.DateTimeField(blank=True, auto_now=True, editable=False)
    created = models.DateTimeField(blank=True, auto_now_add=True, editable=False)


    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'


    def __unicode__(self):
        return u"%s on %s" % (self.backup_object, self.created.isoformat())


def backup_all():
    bs = BackupObject.objects.filter(include=True).all()
    for b in bs:
        b.backup()

pre_delete.connect(unlink_archive, sender=BackupArchive)
post_save.connect(maintenance_tasks, sender=BackupArchive)
