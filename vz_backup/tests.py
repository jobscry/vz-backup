# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test import TestCase
from vz_backup.models import backup_all, BackupObject, BackupArchive

import datetime
import mimetypes
import os
import shutil
import tempfile

class VZBackupTestCase(TestCase):
    def setUp(self):
        #create three users
        self.password = 'testUser'
        self.user1 = User.objects.create_user('testUser1', 'testUser1@test.com', self.password)
        self.user2 = User.objects.create_user('testUser2', 'testUser2@test.com', self.password)
        self.user3 = User.objects.create_user('testUser3', 'testUser1@test.com', self.password)

        #create a temp directory for backup archives
        self.old_backup_dir = settings.VZ_BACKUP_DIR
        settings.VZ_BACKUP_DIR = tempfile.mkdtemp()


    def test_models_management_commands(self):
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #test to see if auth app was added to backups
        self.assertEqual(BackupObject.objects.count(), 1)

        #get auth backup object
        bo = BackupObject.objects.get(id__exact=1)
        self.assertEqual(bo.app_label, 'auth')

        #test to see if initial backup archive was created
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 1)
        ba = BackupArchive.objects.all()


    def test_models_backup(self):
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #get auth backup object, delete initial backup archive
        bo = BackupObject.objects.get(id__exact=1)
        ba = BackupArchive.objects.all().delete()
        
        #test include switch
        bo.include = False
        bo.save()
        backup_all()
        self.failUnlessEqual(BackupArchive.objects.count(), 0)
        bo.include = True
        bo.save()
        backup_all()
        self.failUnlessEqual(BackupArchive.objects.count(), 1)
        BackupArchive.objects.all().delete()

        #test backup of auth app with no compression, default format
        bo.backup()
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 1)
        ba = BackupArchive.objects.all()[0]
        self.failUnlessEqual('auth', bo.__unicode__())
        ba.delete()

        #test backup of auth app with bz2 compression, default format
        bo.compress = 'bz2'
        bo.backup()
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 1)
        ba = BackupArchive.objects.all()[0]
        ba.delete()

        #test backup of auth app with gz compression, default format
        bo.compress = 'gz'
        bo.backup()
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 1)
        ba = BackupArchive.objects.all()[0]


    def test_models_prune(self):
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #get auth app backup object, turn on auto prune
        bo = BackupObject.objects.get(id__exact=1)
        bo.auto_prune = True
        bo.save()

        #mark initial backup archive as "keep"
        ba1 = BackupArchive.objects.get(id__exact=1)
        ba1.keep = True
        ba1.save()

        #test prune_by as "count"
        bo.prune_value = 1
        bo.save()
        bo.backup()
        ba2 = BackupArchive.objects.filter(keep=False)[0]
        #test for two backups, intial (keep) + ba2
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 2)
        bo.backup()
        #test for two backups, initial (keep) + last backup
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 2)
        #ensure ba2 was deleted
        ba3 = BackupArchive.objects.filter(keep=False)[0]
        self.assertNotEqual(ba2.id, ba3.id)

        #test prune_by as "size"
        bo.prune_by = 'size'
        bo.prune_value = ba3.size/1000.0
        bo.save()
        bo.backup()
        #test for two backups, initial (keep) + last backup
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 2)
        #ensure ba3 was deleted
        ba4 = BackupArchive.objects.filter(keep=False)[0]
        self.assertNotEqual(ba3.id, ba4.id)

        #test pure_by as "time"
        bo.prune_by = 'time'
        bo.prune_value = 1
        bo.save()
        #change ba4's created to trigger prune
        delta = datetime.timedelta(days=2)
        ba4.created = ba4.created - delta
        ba4.save()
        ba1.created = ba1.created - delta
        ba1.save()
        bo.backup()
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 2)
        ba5 = BackupArchive.objects.filter(keep=False)[0]
        self.assertNotEqual(ba4.id, ba5.id)

    def test_models_mail_to(self):
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #get auth app backup object
        bo = BackupObject.objects.get(id__exact=1)

        #test empty mail_to
        bo.mail_latest(fail_silently=True)
        self.assertEquals(len(mail.outbox), 0)

        #test mail_to with user1
        bo.mail_to.add(self.user1)
        bo.mail_latest(fail_silently=True)
        self.assertEquals(len(mail.outbox), 1)
        
    
    def test_views_download_archive(self):
        #add auth app to backups
        call_command('add_to_backups', 'auth')

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
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #make user1 a superuser
        self.user1.is_superuser = True
        self.user1.save()

        #login user1
        self.client.login(username=self.user1.username, password=self.password)

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
        #add auth app to backups
        call_command('add_to_backups', 'auth')

        #make user1 a superuser
        self.user1.is_superuser = True
        self.user1.save()

        #login user1
        self.client.login(username=self.user1.username, password=self.password)

        #test delete archive
        response = self.client.get(reverse('admin:vz_backup_delete_archive', args=('1',)))
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(BackupArchive.objects.count(), 1)
        response = self.client.post(reverse('admin:vz_backup_delete_archive', args=('1',)))
        self.failUnlessEqual(response.status_code, 302)
        self.failUnlessEqual(BackupArchive.objects.count(), 0)


    def tearDown(self):
        #remove temp backup dir, reset to original path
        shutil.rmtree(settings.VZ_BACKUP_DIR)
        settings.VZ_BACKUP_DIR = self.old_backup_dir
