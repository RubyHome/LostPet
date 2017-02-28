# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lostpet_auth', '0008_client_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='pricing',
            field=models.IntegerField(default=0, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='client',
            name='stripe_uid',
            field=models.CharField(default='', max_length=255, null=True, blank=True),
        ),
    ]
