# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-02 18:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery_model', '0005_modeltaskmeta_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modeltaskmeta',
            name='state',
            field=models.PositiveIntegerField(choices=[(0, b'PENDING'), (1, b'STARTED'), (2, b'RETRY'), (3, b'FAILURE'), (4, b'SUCCESS'), (5, b'IGNORED')], default=0),
        ),
    ]
