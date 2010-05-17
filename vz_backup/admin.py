# -*- coding: utf-8 -*-

from django.contrib import admin
from django.conf.urls.defaults import *
from vz_backup.models import BackupObject, BackupArchive
from vz_backup.views import delete_archive, reload_archive


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
        'prune_by',
        'auto_prune',
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
    ]
    save_on_top = True


    def admin_delete_archive(self, request, id):
        return delete_archive(request, self, id)


    def admin_reload_archive(self, request, id):
        return reload_archive(request, self, id)


    def get_urls(self):
        urls = super(BackupObjectAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^download/(?P<id>\d+)/', 'vz_backup.views.download_archive', name='vz_backup_download_archive'),
            url(r'^(?P<action>keep|unkeep)/(?P<id>\d+)/', 'vz_backup.views.keep_archive', name='vz_backup_keep_archive'),
            url(r'^delete/(?P<id>\d+)/', self.admin_delete_archive, name='vz_backup_delete_archive'),
            url(r'^mail/(?P<id>\d+)/', 'vz_backup.views.mail_archive', name='vz_backup_mail_archive'),
            url(r'^reload/(?P<id>\d+)/', self.admin_reload_archive, name='vz_backup_reload_archive'),
        )
        return my_urls + urls

    def backup_size(self, obj):
        return _sizeof_fmt(obj.archives_size)

    def number_of_archives(self, obj):
        return obj.archives.count()

    def kept_archives(self, obj):
        return obj.kept_archives.count()

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
