# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from vz_backup.models import BackupObject

def mark_changed(sender, instance, **kwargs):
    """Mark Changed
    
    post save signal
    sender is whatever you'd like to be "watched"
    
    This is one way to watch for changes on models, this requires you to manually
    add this signal to the models you want to watch.
    """
    try:
        backup_object = BackupObject.objects.get(sender._meta.app_label)
        if not backup_object.changed_since_last_backup:
            backup_object.changed_since_last_backup = True
            backup_object.save()
    except ObjectDoesNotExist:
        pass


def load_backupObjects(sender, created_models, **kwargs):
    """Load Backup Objects
    
    post_syncdb signal
    
    Creates BackupObjects for each installed app."""
    for model in created_models:
        BackupObject.objects.get_or_create(
            app_label=model._meta.app_label
        )


def unlink_archive(sender, instance, **kwargs):
    """Unlink Archive
    
    post_save signal
    sender is BackupArchive
    
    unlinks file after a BackupArhive object has been deleted"""
    os.unlink(instance.path)


def update_backup_object(sender, instance, created, **kwargs):
    """Update Backup Object
    
    post_save signal
    sender is BackupArchive
    
    update BackupObject when new BackupArchive is created
    """
    if created:
        backup_object = instance.backup_object
        backup_object.last_backup = instance.created
        backup_object.changed_since_last_backup = False
        backup_object.save()

post_syncdb.connect(_load_backupObjects)