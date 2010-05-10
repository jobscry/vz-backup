# -*- coding: utf-8 -*-

from django import template
from vz_backup.models import BackupObject, BackupArchive

register = template.Library()

@register.inclusion_tag('vz_backup/vz_backup_admin_view_archives.html')
def display_archives(b_obj_id):
    b_obj = BackupObject.objects.get(id__exact=b_obj_id)
    return { 'archives': BackupArchive.objects.filter(backup_object=b_obj) }
