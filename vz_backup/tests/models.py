from django.db import models

class BackupTestWidget(models.Model):
    name = models.CharField(max_length='255')
    created = models.DateTimeField(auto_now=True)

def create_widgets(number=100):
    from string import ascii_letters
    from random import choice, randrange

    letters = list(ascii_letters)
    n = len(ascii_letters)
    for digit in xrange(number):
        name = ''.join([choice(ascii_letters) for i in xrange(n)])
        BackupTestWidget.objects.create(name=name)
