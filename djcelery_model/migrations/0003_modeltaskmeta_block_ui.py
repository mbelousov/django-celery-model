# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery_model', '0002_modeltaskmeta_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='modeltaskmeta',
            name='block_ui',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
