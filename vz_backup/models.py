# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.commands import dumpdata
from django.db import models
from django.db.models.signals import post_save, post_syncdb, pre_delete

import datetime
import gzip
import os
import time

INDENT = 4
FORMAT = 'json'

class BackupObject(models.Model):
    """Backup Object
    
    App to be backed up.  All apps from INSTALLED APPS are added upon `syncdb`.
    
    """

    app_label = models.CharField(blank=True, max_length=100, unique=True)
    include = models.BooleanField(default=True)
    use_natural_keys = models.BooleanField(default=True)
    compress = models.BooleanField(default=True)
    send_to_admins = models.BooleanField(default=True)
    created = models.DateTimeField(blank=True, auto_now_add=True)
    last_backup =  models.DateTimeField(blank=True, null=True)
    changed_since_last_backup = models.BooleanField(default=True)
    modified = models.DateTimeField(blank=True, auto_now=True)   


    def backup(self):
        if not self.changed_since_last_backup:
            return

        dt = datetime.datetime.now()
        name = u'%s_%s%s.%s' % (self.app_label, dt.strftime('%Y%j-'), int(time.time()), FORMAT)

        if self.compress:
            name = name + u'.gz'

        path = os.path.join(settings.VZ_BACKUP_DIR, name)
        try:
            if self.compress:
                b_file = gzip.open(path, 'wb')
            else:
                b_file = open(path, 'w')
            dump = dumpdata.Command()
            b_file.write(
                dump.handle(
                    self.app_label,
                    use_natural_keys=self.use_natural_keys,
                    indent=INDENT,
                    format=FORMAT
                )
            )
            b_file.close()
            BackupArchive.objects.create(
                backup_object=self,
                name=name,
                path=path,
                size=os.path.getsize(path)
            )
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
    created = models.DateTimeField(blank=True, auto_now_add=True)
    

    def __unicode__(self):
        return u"%s on %s" % (self.backup_object, self.created.isoformat())


def backup_all():
    bs = BackupObject.objects.all()
    for b in bs:
        b.backup()


post_save.connect(vz_backup.signals.update_backup_object, sender=BackupArchive)
pre_delete.connect(vz_backup.signals.unlink_archive, sender=BackupArchive)
