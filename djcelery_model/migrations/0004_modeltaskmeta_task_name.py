# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery_model', '0003_modeltaskmeta_block_ui'),
    ]

    operations = [
        migrations.AddField(
            model_name='modeltaskmeta',
            name='task_name',
            field=models.CharField(max_length=255, blank=True),
            preserve_default=True,
        ),
    ]
