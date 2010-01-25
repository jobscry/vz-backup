# -*- coding: utf-8 -*-


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