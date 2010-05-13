# -*- coding: utf-8 -*-

from django.contrib import admin
from django.db.models import Sum
from vz_backup.models import BackupObject, BackupArchive


def mark_include(modeladmin, request, queryset):
    queryset.update(include=True)
mark_include.short_description = 'Enable Backup (include) on Selected Objects'


def mark_no_include(modeladmin, request, queryset):
    queryset.update(include=False)
mark_no_include.short_description = 'Disable Backup (include) on \
    Selected Objects'


def mark_use_natural_keys(modeladmin, request, queryset):
    queryset.update(use_natural_keys=True)
mark_use_natural_keys.short_description = 'Use Natural Keys on \
    Selected Objects'


def mark_no_use_natural_keys(modeladmin, request, queryset):
    queryset.update(use_natural_keys=False)
mark_no_use_natural_keys.short_description = 'Do Not Use Natural Keys on \
    Selected Objects'


def mark_send_to_admins(modeladmin, request, queryset):
    queryset.update(send_to_admins=True)
mark_send_to_admins.short_description = 'Send Backups of Selected Objects \
    to Admins'


def mark_no_send_to_admins(modeladmin, request, queryset):
    queryset.update(send_to_admins=False)
mark_no_send_to_admins.short_description = 'Do Not Send Backups of Selected \
    Objects to Admins'


def backup_now(modeladmin, request, queryset):
    for bobj in queryset:
        bobj.backup()
backup_now.short_description = 'Backup Selected Objects Now'


def prune_now(modeladmin, request, queryset):
    for bobj in queryset:
        bobj.prune()
prune_now.short_description = 'Prune Selected Objects Now'


class BackupObjectAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/vz_backup.css',)
        }
        js = ('js/jquery.js', 'js/jquery.tablesorter.js', 'js/vz_backup_tablesorter.js', )

    list_display = (
        'app_label',
        'include',
        'compress',
        'auto_prune',
        'send_to_admins',
        'backup_size',
        'number_of_archives',
        'kept_archives',
        'created',
        'modified',
    )

    readonly_fields = ('app_label', )
    actions = [
        backup_now,
        prune_now,
        mark_include,
        mark_no_include,
        mark_use_natural_keys,
        mark_no_use_natural_keys,
        mark_send_to_admins,
        mark_no_send_to_admins,
    ]


    def backup_size(self, obj):
        qs = BackupArchive.objects.filter(
            backup_object=obj).aggregate(Sum('size'))
        return _sizeof_fmt(qs['size__sum'])

    def number_of_archives(self, obj):
        return BackupArchive.objects.filter(backup_object=obj).count()

    def kept_archives(self, obj):
        return BackupArchive.objects.filter(
            backup_object=obj, keep=True).count()

admin.site.register(BackupObject, BackupObjectAdmin)


#http://stackoverflow.com/questions/1094841/reusable-library-to-get-\
#human-readable-version-of-file-size/1094933#1094933


def _sizeof_fmt(num):
    if num is None:
        num = 0
    for x in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
