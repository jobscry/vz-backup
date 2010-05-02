# -*- coding: utf-8 -*-

from django.db.models.signals import post_save, post_syncdb

import os

def unlink_archive(sender, instance, **kwargs):
    """Unlink Archive
    
    post_save signal
    sender is BackupArchive
    
    unlinks file after a BackupArhive object has been deleted"""
    try:
        os.unlink(instance.path)
    except OSError:
        pass

def check_auto_prune(sender, instance, created, **kwargs):
    if created and instance.backup_object.auto_prune:
        instance.backup_object.prune()
