# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from vz_backup.models import BackupObject, BackupArchive

import datetime
import os
import shutil
import tempfile

class VZBackupModelsTestCase(TestCase):
    def setUp(self):
        #create three users
        self.user1 = User.objects.create(username='testUser1', password='testUser')
        self.user2 = User.objects.create(username='testUser2', password='testUser')
        self.user3 = User.objects.create(username='testUser3', password='testUser')

        #create a temp directory for backup archives
        self.old_backup_dir = settings.VZ_BACKUP_DIR
        settings.VZ_BACKUP_DIR = tempfile.mkdtemp()


    def test_management_commands(self):
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


    def test_backup(self):
        #add auth app to backups
        self.test_management_commands()

        #get auth backup object, delete initial backup archive
        bo = BackupObject.objects.get(id__exact=1)
        ba = BackupArchive.objects.all()
        ba.delete()

        #test backup of auth app with no compression, default format
        bo.backup()
        self.assertEqual(BackupArchive.objects.filter(backup_object=bo).count(), 1)
        ba = BackupArchive.objects.all()[0]
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


    def test_prune(self):
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

    def tearDown(self):
        #remove temp backup dir, reset to original path
        shutil.rmtree(settings.VZ_BACKUP_DIR)
        settings.VZ_BACKUP_DIR = self.old_backup_dir
