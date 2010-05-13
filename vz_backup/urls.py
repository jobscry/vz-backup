# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^download/(?P<id>\d+)/', 'vz_backup.views.download_archive', name='vz_backup_download_archive'),
)
