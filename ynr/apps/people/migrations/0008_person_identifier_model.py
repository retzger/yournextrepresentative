# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-10-29 14:47
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("people", "0007_remove_dateframe")]

    operations = [
        migrations.CreateModel(
            name="PersonIdentifier",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "value",
                    models.CharField(
                        help_text="An identifier e.g a URL or username provided by a 3rd party",
                        max_length=800,
                    ),
                ),
                (
                    "internal_identifier",
                    models.CharField(
                        help_text="An optional internal identifier from the 3rd party",
                        max_length=800,
                        null=True,
                    ),
                ),
                (
                    "value_type",
                    models.CharField(
                        help_text="A label for the type of value e.g. 'Twitter', 'Person blog'",
                        max_length=100,
                    ),
                ),
                (
                    "extra_data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        help_text="For storing any additional data against this field. \n                     Used by bots, not humans.",
                        null=True,
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="people.Person",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="personidentifier",
            unique_together=set(
                [
                    ("person", "internal_identifier", "value_type"),
                    ("person", "value"),
                ]
            ),
        ),
    ]
