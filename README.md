VZ Backup
=========

Django App for automagically backing up Models data.  Backups can be compressed, sent to ADMINS.

Uses Django's [dumpdata](http://docs.djangoproject.com/en/dev/ref/django-admin/#dumpdata-appname-appname-appname-model 'dumpdata docs') management command.

TODO
----

* Email
    * If-changed
* Size Experimentation
* Auto/Manual Pruning
* Download
* Re-load 
    * From Admin Site
    * From Command

Settings
--------

**VZ_BACKUP_DIR** - required, full path to directory for backup archive files

**VZ_BACKUP_INDENT** - optional, default is 4, see [Django documentation](http://docs.djangoproject.com/en/dev/ref/django-admin/#djadminopt---format)

**VZ_BACKUP_FORMAT** - optional, default is json, see [Django documentation](http://docs.djangoproject.com/en/dev/ref/django-admin/#djadminopt---indent)


Models
------

### BackupObject


A backup manager for an app.

**app_label** - charfield, from application being backed up.

**include** - boolean, a *switch* that turns backups on/off for this app.  Easier than deleting for troubleshooting.

**use_natural_keys** - boolean, see [django documentation](http://docs.djangoproject.com/en/dev/ref/django-admin/#djadminopt---natural)

**compress** - charfield, choices are bz2, gz, or none

**prune_by** - charfield, can either be:

* count - delete after *x* number of archives that are not marked as *keep*, starting with oldest.  *x* is defined in **prune_by** 
* size - delete after total aggregated archive size of archives not marked *keep* for app reaches *x*.  *x* is defined as kilo bytes in **prune_by**
* time - delete archives not marked *keep* after *x* days starting with oldest. *x* is defined as days in **prune_by** 

**prune_value** - positive integer, see **prune_by**

**send_to_admins** - boolean, email new archives to admins?

**created** - datetime

**modified** - datetime

Management Commands
-------------------

### add_to_backups


`./manage.py add_to_backups widget`

This creates a BackupObject for the widget app.