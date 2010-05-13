# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import permission_required
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from vz_backup.models import BackupArchive

import mimetypes
import os

@permission_required(lambda u: u.has_perm('backuparchive.can_change'))
def download_archive(request, id):
    """
    Download Archive
    
    If backup archive with *id* exists and user had change permissions
    download file based on *send_file* setting.
    """
    try:
        archive = BackupArchive.objects.select_related().get(id__exact=id)
    except BackupArchive.DoesNotExist:
        return HttpResponseNotFound('Archive with this ID does not exist.')

    if not os.path.exists(archive.path):
        return HttpResponseNotFound('Archive path does not exist.')

    send_file = getattr(settings,'VZ_BACKUP_SEND_FILE', None)

    headers = dict()
    headers['Content-Length'] = archive.size
    headers['Content-Disposition'] = 'attachment; filename=%s'%archive.name

    if send_file == 'x-accel-redirect' or send_file == 'x-send-file':
        response = HttpResponse()
        if send_file == 'x-accel-redirect':
            headers['Content-Type'] = ''
            headers['X-Accel-Redirect'] = archive.path
        else:
            headers['X-Sendfile'] = archive.path
    else:
        if archive.backup_object.compress == 'None':
            wrapper = FileWrapper(open(archive.path, 'r'))
        else:
            wrapper = FileWrapper(open(archive.path, 'rb'))

        response = HttpResponse(wrapper, mimetype=mimetypes.guess_type(archive.path)[0])

    for k, v in headers.iteritems():
        response[k] = v

    return response

@permission_required(lambda u: u.has_perm('backuparchive.can_change'))
def keep_archive(request, action, id):
    try:
        archive = BackupArchive.objects.select_related().get(id__exact=id)
    except BackupArchive.DoesNotExist:
        return HttpResponseNotFound('Archive with this ID does not exist.')

    if action == 'keep':
        archive.keep = True
    else:
        archive.keep = False

    archive.save()

    return redirect(reverse('admin:vz_backup_backupobject_change', args=(archive.backup_object.id, )))
