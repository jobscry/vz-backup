VZ Backup
=========

Django App for automagically backing up Models data.  Backups can be compressed, sent to ADMINS.

TODO
====

* Email
    * If-changed
* Size Experimentation
* Auto/Manual Pruning
* Download
* Re-load 
    * From Admin Site
    * From Command

Models
======

BackupObject
------------

A backup manager for an app.

Management Commands
===================

add_to_backups
----------------

`./manage.py add_to_backups widget`

This creates a BackupObject for the widget app.