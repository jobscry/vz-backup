# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from vz_backup.models import BackupArchive

import mimetypes
import os

@permission_required('backuparchive.can_delete')
def delete_archive(request, model_admin, id):
    """
    http://www.lonelycode.com/2009/05/28/customising-the-django-admin/
    http://www.beardygeek.com/2010/03/adding-views-to-the-django-admin/
    http://www.scribd.com/doc/24645813/Customizing-the-Django-Admin
    """
    try:
        archive = BackupArchive.objects.select_related().get(id__exact=id)
    except BackupArchive.DoesNotExist:
        return HttpResponseNotFound('Archive with this ID does not exist.')

    opts = model_admin.model._meta
    admin_site = model_admin.admin_site
    has_perm = request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())

    if request.method == 'POST':
        bo = archive.backup_object
        archive.delete()
        request.user.message_set.create(message='Deleted archive')
        return redirect(reverse('admin:vz_backup_backupobject_change', args=(bo.id, )))

    context = {
        'archive': archive,
        'admin_site': admin_site.name,
        'title': 'Delete Archive',
        'opts':opts,
        'root_path': '/%s' % admin_site.root_path,
        'app_label' : opts.app_label,
        'has_change_permission':has_perm}
    template = 'admin/vz_backup/backuparchive/delete_archive.html'
    return render_to_response(template, context, context_instance=RequestContext(request))

@permission_required('backuparchive.can_change')
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

@permission_required('backuparchive.can_change')
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

@permission_required('backuparchive.can_change')
def mail_archive(request, id):
    try:
        archive = BackupArchive.objects.select_related().get(id__exact=id)
    except BackupArchive.DoesNotExist:
        return HttpResponseNotFound('Archive with this ID does not exist.')

    archive.backup_object.mail(archive.id)
    request.user.message_set.create(message='Sent archive')

    return redirect(reverse('admin:vz_backup_backupobject_change', args=(archive.backup_object.id, )))


@permission_required('backuparchive.can_change')
def reload_archive(request, model_admin, id):
    try:
        archive = BackupArchive.objects.select_related().get(id__exact=id)
    except BackupArchive.DoesNotExist:
        return HttpResponseNotFound('Archive with this ID does not exist.')

    opts = model_admin.model._meta
    admin_site = model_admin.admin_site
    has_perm = request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())

    if request.method == 'POST':
        archive.backup_object.reload(archive.id)
        request.user.message_set.create(message='App Reloaded from Backup Archive')
        return redirect(reverse('admin:vz_backup_backupobject_change', args=(archive.backup_object.id, )))

    context = {
        'archive': archive,
        'admin_site': admin_site.name,
        'title': 'Reload App from Backup Archive',
        'opts':opts,
        'root_path': '/%s' % admin_site.root_path,
        'app_label' : opts.app_label,
        'has_change_permission':has_perm}
    template = 'admin/vz_backup/backuparchive/reload_archive.html'
    return render_to_response(template, context, context_instance=RequestContext(request))
