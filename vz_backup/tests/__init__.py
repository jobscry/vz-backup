# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.db.models import loading
from django.test import TransactionTestCase
from vz_backup import generate_file_hash
from vz_backup.exceptions import ArchiveHashesDoNotMatch
from vz_backup.tests.testwidgets.models import BackupTestWidget, create_widgets
from vz_backup.models import backup_all, BackupObject, BackupArchive

import datetime
import mimetypes
import os
import shutil
import tempfile

class BackupTestCase(TransactionTestCase):
    def _pre_setup(self):
        #add BackupTestWidget model
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS += ['vz_backup.tests.testwidgets']
        loading.cache.loaded = False
        loading.load_app('vz_backup.tests.testwidgets')
        call_command('syncdb', verbosity=0, interactive=False)

        #create a temp directory for backup archives
        self.old_backup_dir = settings.VZ_BACKUP_DIR
        settings.VZ_BACKUP_DIR = tempfile.mkdtemp()

        super(BackupTestCase, self)._pre_setup()

    def _post_teardown(self):
        settings.INSTALLED_APPS = self.old_installed_apps
        loading.cache.loaded = False

        #remove temp backup dir, reset to original path
        shutil.rmtree(settings.VZ_BACKUP_DIR)
        settings.VZ_BACKUP_DIR = self.old_backup_dir

        super(BackupTestCase, self)._post_teardown()

class VZBackupTestCase(BackupTestCase):
    def setUp(self):
        #create super user
        self.password = 'testUser'
        self.user1 = User.objects.create_user('testUser1', 'testUser1@test.com', self.password)
        self.user1.is_superuser = True
        self.user1.save()

        #create widgets
        self.num_widgets = 3
        create_widgets(self.num_widgets)

        #login user1
        self.client.login(username=self.user1.username, password=self.password)

        #add auth app to backups
        call_command('add_to_backups', 'vz_backup.tests.testwidgets')

        #get backup object
        self.bo = BackupObject.objects.get(id__exact=1)

    def test_create_widgets(self):
        #test create_widgets
        self.failUnlessEqual(BackupTestWidget.objects.count(), self.num_widgets)

    def test_management_add_to_backups(self):
        #test to see if auth app was added to backups
        self.assertEqual(BackupObject.objects.count(), 1)

        #get backup object
        self.assertEqual(self.bo.app_label, 'testwidgets')

        #test to see if initial backup archive was created
        self.assertEqual(self.bo.archives.count(), 1)


    def test_management_backup_all(self): 
        #test backup all
        create_widgets(1)
        call_command('backup_all')
        self.failUnlessEqual(self.bo.archives.count(), 2)

        #test backup all with no backup objects included
        self. bo.include = False
        self.bo.save()
        create_widgets(1)
        call_command('backup_all')
        self.failUnlessEqual(self.bo.archives.count(), 2)


    def test_models_file_hash(self):
        #test file hash
        ba = BackupArchive.objects.get(id__exact=1)
        self.failUnlessEqual(ba.file_hash, generate_file_hash(ba.path))


    def test_models_file_hash_same(self):
        #test backup only if changed
        self.bo.backup()
        self.failUnlessEqual(self.bo.archives.count(), 1)


    def test_models_backup(self):
        #delete initial backup archive
        ba = self.bo.archives.delete()
        
        #test include switch
        self.bo.include = False
        self.bo.save()
        create_widgets(1)
        backup_all()
        self.failUnlessEqual(self.bo.archives.count(), 0)
        self.bo.include = True
        self.bo.save()
        create_widgets(1)
        backup_all()
        self.failUnlessEqual(self.bo.archives.count(), 1)
        self.bo.archives.delete()

        #test backup of auth app with no compression, default format
        create_widgets(1)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 1)
        ba = self.bo.last_archive
        self.failUnlessEqual('testwidgets', self.bo.__unicode__())
        ba.delete()

        #test backup of auth app with bz2 compression, default format
        self.bo.compress = 'bz2'
        self.bo.save()
        create_widgets(1)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 1)
        ba = self.bo.last_archive
        ba.delete()

        #test backup of auth app with gz compression, default format
        self.bo.compress = 'gz'
        self.bo.save()
        create_widgets(1)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 1)
        ba = self.bo.last_archive


    def test_models_prune(self):
        #turn on auto prune
        self.bo.auto_prune = True
        self.bo.save()

        #mark initial backup archive as "keep"
        ba1 = self.bo.last_archive
        ba1.keep = True
        ba1.save()

        #test prune_by as "count"
        self.bo.prune_by = 'count'
        self.bo.prune_value = 1
        self.bo.save()
        create_widgets(1)
        self.bo.backup()
        ba2 = self.bo.last_archive

        #test for two backups, intial (keep) + ba2
        self.assertEqual(self.bo.archives.count(), 2)
        create_widgets(1)
        self.bo.backup()

        #test for two backups, initial (keep) + last backup
        self.assertEqual(self.bo.archives.count(), 2)

        #ensure ba2 was deleted
        ba3 = self.bo.unkept_archives[0]
        self.assertNotEqual(ba2.id, ba3.id)

        #test prune_by as "size"
        self.bo.prune_by = 'none'
        self.bo.save()
        #create a backup to measure
        create_widgets(1)
        self.bo.backup()
        ba4 = self.bo.unkept_archives[0]
        #set prune by to measured sizve
        self.bo.prune_by = 'size'
        self.bo.prune_value = ba4.size / 1000.0
        self.bo.save()
        #delete the known backup archive
        ba4.delete()
        #create a backup with a size we know
        self.bo.backup()
        ba4 = self.bo.unkept_archives[0]

        #ensure ba3 was deleted
        self.assertNotEqual(ba3.id, ba4.id)

        #test pure_by as "time"
        self.bo.prune_by = 'time'
        self.bo.prune_value = 1
        self.bo.save()

        #change ba4's created to trigger prune
        delta = datetime.timedelta(days=2)
        ba4.created = ba4.created - delta
        ba4.save()
        ba1.created = ba1.created - delta
        ba1.save()
        create_widgets(1)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 2)
        ba5 = self.bo.last_archive
        self.assertNotEqual(ba4.id, ba5.id)

        #test prune_by as "none"
        self.bo.prune_by = 'none'
        self.bo.save()
        create_widgets(1)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 3)
        self.bo.backup()
        self.assertEqual(self.bo.archives.count(), 3)


    def test_models_mail_to(self):
        #test empty mail_to
        self.bo.mail(fail_silently=True)
        self.assertEquals(len(mail.outbox), 0)

        #test mail_to with user1
        self.bo.mail_to.add(self.user1)
        self.bo.mail(fail_silently=True)
        self.assertEquals(len(mail.outbox), 1)
        self.bo.mail(1, fail_silently=True)
        self.assertEquals(len(mail.outbox), 2)


    def test_models_reload(self):
        #create more widgets
        create_widgets(self.num_widgets)
        
        #test reload from initial backup
        self.bo.reload(1)
        self.failUnlessEqual(BackupTestWidget.objects.count(), self.num_widgets)

    
    def test_views_download_archive(self):
        #make user1 a superuser
        self.user1.is_superuser = True
        self.user1.save()

        #login user1
        self.client.login(username=self.user1.username, password=self.password)

        #test download of an archive
        ba = BackupArchive.objects.get(id__exact=1)
        response = self.client.get(reverse('admin:vz_backup_download_archive', args=('1', )))
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(response.__getitem__('Content-Type'), mimetypes.guess_type(ba.path)[0])
        self.failUnlessEqual(response.__getitem__('Content-Disposition'), 'attachment; filename=%s'%ba.name)


    def test_views_keep_archive(self):
        #test keep archive
        response = self.client.get(reverse('admin:vz_backup_keep_archive', args=('keep', '1')))
        self.failUnlessEqual(response.status_code, 302)
        ba = BackupArchive.objects.get(id__exact=1)
        self.assertTrue(ba.keep)

        #test unkeep archive
        response = self.client.get(reverse('admin:vz_backup_keep_archive', args=('unkeep', '1')))
        self.failUnlessEqual(response.status_code, 302)
        ba = BackupArchive.objects.get(id__exact=1)
        self.assertFalse(ba.keep)


    def test_views_delete_archive(self):
        #test delete archive
        response = self.client.get(reverse('admin:vz_backup_delete_archive', args=('1',)))
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(BackupArchive.objects.count(), 1)
        response = self.client.post(reverse('admin:vz_backup_delete_archive', args=('1',)))
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(BackupArchive.objects.count(), 0)

    def test_views_mail_archive(self):
        #test send
        response = self.client.get(reverse('admin:vz_backup_mail_archive', args=('1',)))
        self.failUnlessEqual(response.status_code, 302)

    def test_views_reload_archive(self):
        #rest reload archive
        response = self.client.get(reverse('admin:vz_backup_reload_archive', args=('1', )))
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(BackupTestWidget.objects.count(), self.num_widgets)
        create_widgets(self.num_widgets)
        response = self.client.post(reverse('admin:vz_backup_reload_archive', args=('1', )))
        self.failUnlessEqual(BackupTestWidget.objects.count(), self.num_widgets)
        self.failUnlessEqual(response.status_code, 302)

    def test_exeptions_ArchiveHashesDoNotMatch(self):
        #test tampered file hash
        ba = BackupArchive.objects.get(id__exact=1)
        fh = ba.file_hash
        ba.file_hash = 'malicious'
        ba.save()
        self.failUnlessRaises(ArchiveHashesDoNotMatch, self.bo.reload, 1)


    def tearDown(self):
        pass
