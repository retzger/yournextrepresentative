# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-07-16 12:53
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("uk_results", "0047_auto_20180501_1359")]

    operations = [
        migrations.RenameField(
            model_name="resultset", old_name="post_election", new_name="ballot"
        )
    ]
