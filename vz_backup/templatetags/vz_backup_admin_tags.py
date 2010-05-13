# -*- coding: utf-8 -*-

from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from vz_backup.models import BackupObject, BackupArchive

register = template.Library()

@register.inclusion_tag('vz_backup/vz_backup_admin_view_archives.html')
def display_archives(b_obj_id):
    b_obj = BackupObject.objects.get(id__exact=b_obj_id)
    return { 'archives': BackupArchive.objects.filter(backup_object=b_obj) }

@register.filter
@stringfilter
def bool_icon(value):
    BOOLEAN_MAPPING = {'True': 'yes', 'False': 'no', 'None': 'unknown'}
    return mark_safe(u'<img src="%simg/admin/icon-%s.gif" alt="%s" />' % \
        (settings.ADMIN_MEDIA_PREFIX, BOOLEAN_MAPPING[value], value))