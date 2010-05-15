# -*- coding: utf-8 -*-

from django.db.models.signals import post_save, post_syncdb
from vz_backup.exceptions import UnableToDeleteArchive

import os

def maintenance_tasks(sender, instance, created, **kwargs):
    if created:
        bo = instance.backup_object
        bo.prune()
        bo.mail()

def unlink_archive(sender, instance, **kwargs):
    """Unlink Archive
    
    post_save signal
    sender is BackupArchive
    
    unlinks file after a BackupArhive object has been deleted"""
    try:
        os.unlink(instance.path)
    except OSError:
        raise UnableToDeleteArchive
