# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-01 18:20
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery_model', '0004_modeltaskmeta_task_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='modeltaskmeta',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(2016, 6, 1, 18, 20, 13, 5532, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
