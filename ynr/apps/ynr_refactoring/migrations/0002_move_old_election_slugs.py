# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-01-10 11:36
from __future__ import unicode_literals

import json

from django.contrib.admin.utils import NestedObjects
from django.db import connection, migrations

UPDATED_SLUGS = {
    "2010": "parl.2010-05-06",
    "2015": "parl.2015-05-07",
    "gb-sp-2016-05-05-c": "sp.c.2016-05-05",
    "gb-sp-2016-05-05-r": "sp.r.2016-05-05",
    "gla-2016-05-05-a": "gla.a.2016-05-05",
    "gla-2016-05-05-c": "gla.c.2016-05-05",
    "local.barnet.underhill.2016-05-05": "local.barnet.2016-05-05",
    "local.barrow.dalton-south.2016-05-05": "local.barrow-in-furness.2016-05-05",
    "local.braintree.witham-south.2016-05-05": "local.braintree.2016-05-05",
    "local.breckland.attleborough-queens-and-besthorpe.2016-05-05": "local.breckland.2016-05-05",
    "local.brent.kilburn.2016-05-05": "local.brent.2016-05-05",
    "local.cambridgeshire.st.-neots-eaton-scon-and-eynesbury.2016-05-05": "local.cambridgeshire.2016-05-05",
    "local.canterbury.reculver.2016-05-05": "local.canterbury.2016-05-05",
    "local.castle-point.st-georges.2016-05-05": "local.castle-point.2016-05-05",
    "local.croydon.west-thornton.2016-05-05": "local.croydon.2016-05-05",
    "local.doncaster.edenthorpe-and-kirk-sandall.2016-05-05": "local.doncaster.2016-05-05",
    "local.east-hampshire.clanfield-and-finchdean.2016-05-05": "local.east-hampshire.2016-05-05",
    "local.east-riding-of-yorkshire.east-wolds-and-coastal.2016-05-05": "local.east-riding-of-yorkshire.2016-05-05",
    "local.east-sussex.st-helens-and-silverhill.2016-05-05": "local.east-sussex.2016-05-05",
    "local.forest-heath.brandon-west.2016-05-05": "local.forest-heath.2016-05-05",
    "local.forest-heath.south.2016-05-05": "local.forest-heath.2016-05-05",
    "local.glasgow.anderston-city.2016-05-05": "local.glasgow.2016-05-05",
    "local.gloucestershire.churchdown.2016-05-05": "local.gloucestershire.2016-05-05",
    "local.greenwich.glyndon-ward.2016-05-05": "local.greenwich.2016-05-05",
    "local.greenwich.glyndon.2016-05-05": "local.greenwich.2016-05-05",
    "local.guildford.stoke.2016-05-05": "local.guildford.2016-05-05",
    "local.hackney.hackney-downs.2016-05-05": "local.hackney.2016-05-05",
    "local.hackney.stoke-newington.2016-05-05": "local.hackney.2016-05-05",
    "local.hampshire.fareham-town.2016-05-05": "local.hampshire.2016-05-05",
    "local.hampshire.headley.2016-05-05": "local.hampshire.2016-05-05",
    "local.havering.heaton.2016-05-05": "local.havering.2016-05-05",
    "local.kensington-and-chelsea.abingdon.2016-05-05": "local.kensington-and-chelsea.2016-05-05",
    "local.lancashire.lancaster-east.2016-05-05": "local.lancashire.2016-05-05",
    "local.lancaster.carnforth-and-millhead.2016-05-05": "local.lancaster.2016-05-05",
    "local.lancaster.john-ogaunt.2016-05-05": "local.lancaster.2016-05-05",
    "local.lincoln.2016-05-05": "local.city-of-lincoln.2016-05-05",
    "local.melton.egerton.2016-05-05": "local.melton.2016-05-05",
    "local.merton.figges-marsh.2016-05-05": "local.merton.2016-05-05",
    "local.middlesbrough.coulby-newham.2016-05-05": "local.middlesbrough.2016-05-05",
    "local.north-dorset.blandford-hilltop.2016-05-05": "local.north-dorset.2016-05-05",
    "local.north-dorset.hill-forts.2016-05-05": "local.north-dorset.2016-05-05",
    "local.redbridge.roding.2016-05-05": "local.redbridge.2016-05-05",
    "local.romford.heaton.2016-05-05": "local.havering.2016-05-05",
    "local.south-bucks.farnham-royal-and-hedgerley.2016-05-05": "local.south-bucks.2016-05-05",
    "local.south-kestevan.deeping-st-james.2016-05-05": "local.south-kesteven.2016-05-05",
    "local.south-ribble.seven-stars.2016-05-05": "local.south-ribble.2016-05-05",
    "local.southwark.college.2016-05-05": "local.southwark.2016-05-05",
    "local.southwark.newington.2016-05-05": "local.southwark.2016-05-05",
    "local.spelthorne.ashford-north-and-stanwell-south.2016-05-05": "local.spelthorne.2016-05-05",
    "local.st-edmundsbury.haverhill-north.2016-05-05": "local.st-edmundsbury.2016-05-05",
    "local.staffordshire.uttoxeter-town.2016-05-05": "local.staffordshire.2016-05-05",
    "local.suffolk.bixley.2016-05-05": "local.suffolk.2016-05-05",
    "local.suffolk.haverhill-cangle.2016-05-05": "local.suffolk.2016-05-05",
    "local.surrey.staines-south-and-ashford-west.2016-05-05": "local.surrey.2016-05-05",
    "local.swansea.mynyddbach.2016-05-05": "local.swansea.2016-05-05",
    "local.tendring.st-paul.2016-05-05": "local.tendring.2016-05-05",
    "local.torbay.tormohun.2016-05-05": "local.torbay.2016-05-05",
    "local.waveney.wrentham.2016-05-05": "local.waveney.2016-05-05",
    "local.westminster.church-street.2016-05-05": "local.westminster.2016-05-05",
    "local.wiltshire.amesbury-east.2016-05-05": "local.wiltshire.2016-05-05",
    "mayor.greater-manchester.2017-05-04": "mayor.greater-manchester-ca.2017-05-04",
    "mayor.liverpool.2017-05-04": "mayor.liverpool-city-ca.2017-05-04",
    "naw-2016-05-05-c": "naw.c.2016-05-05",
    "naw-2016-05-05-r": "naw.r.2016-05-05",
    "nia-2016-05-05": "nia.2016-05-05",
    "parl.bridgend.ogmore.2016-05-05": "parl.2016-05-05",
    "parl.copeland.2017-02-23": "parl.2017-02-23",
    "parl.sheffield.sheffield-brightside-and-hillsborough.2016-05-05": "parl.2016-05-05",
    "parl.stoke-on-trent-central.2017-02-23": "parl.2017-02-23",
    "sp-2016-05-05-c": "sp.c.2016-05-05",
}


def _merge_election(Election, old_list):
    dest_slug = old_list.pop(0)
    dest_model = None
    while not dest_model and old_list:
        try:
            dest_model = Election.objects.get(slug=dest_slug)
        except Election.DoesNotExist:
            # This election doesn't exist, so it might just exist in
            # the person versions. Because of this, it's safe to return
            # here and leave the migration to rename the slug in the versions json
            dest_slug = old_list.pop(0)
            continue
    for source_slug in old_list:
        try:
            source_model = Election.objects.get(slug=source_slug)
        except Election.DoesNotExist:
            # Same as above – if this election doesn't exist than there
            # is nothing to merge
            continue

        source_model.ballot_set.update(election=dest_model)
        source_model.officialdocument_set.update(election=dest_model)
        source_model.resultevent_set.update(election=dest_model)

        collector = NestedObjects(using=connection.cursor().db.alias)
        collector.collect([source_model])
        if len(collector.nested()) > 1:
            # A related object exist for this source election,
            # something has gone wrong.
            print(collector.nested())
            raise ValueError(
                "Can't merge election {} with related objects".format(
                    source_slug
                )
            )
        source_model.delete()
    return dest_slug


def _update_versions(person, old, new):
    versions = json.loads(person.versions)
    for version in versions:
        if version["data"].get("standing_in"):
            if old in version["data"]["standing_in"]:
                version["data"]["standing_in"][new] = version["data"][
                    "standing_in"
                ].pop(old)
        if version["data"].get("party_memberships"):
            if old in version["data"]["party_memberships"]:
                version["data"]["party_memberships"][new] = version["data"][
                    "party_memberships"
                ].pop(old)
    if "'{}'".format(old) in json.dumps(versions):
        raise ValueError(
            "'{}' found in versions for person {}".format(old, person.pk)
        )
    person.versions = json.dumps(versions)
    person.save()


def _move_election_slug(apps):
    # Duplicate of `ynr_refactoring/views.py` because this migration is "static"
    # and the view code might change one day.
    Election = apps.get_model("elections", "Election")
    Person = apps.get_model("people", "Person")

    # Group by destination ID so we can merge
    elections_to_merge = {}
    for old, new in UPDATED_SLUGS.items():
        if new in elections_to_merge:
            elections_to_merge[new].append(old)
        else:
            elections_to_merge[new] = [old]

    for new, old_list in elections_to_merge.items():
        if len(old_list) > 1:
            # We need to merge this election before moving the IDs
            old = _merge_election(Election, old_list)
        else:
            old = old_list[0]
        try:
            election = Election.objects.get(slug=old)
        except Election.DoesNotExist:
            # Chances are this is a test run where we don't have these
            # elections yet
            continue
        if Election.objects.filter(slug=new).exists():
            # The new election might already exist. In that case, merge and remove
            # the old one
            new_slug = _merge_election(Election, [new, old])
            election = Election.objects.get(slug=new_slug)
        else:
            election.slug = new
            election.save()

        for old_slug in old_list:
            for person in Person.objects.filter(
                versions__contains='"{}"'.format(old_slug)
            ):
                _update_versions(person, old, new)


def update_election_slug(apps, schema_editor):
    return _move_election_slug(apps)


class Migration(migrations.Migration):

    dependencies = [("ynr_refactoring", "0001_initial")]

    operations = [
        migrations.RunPython(update_election_slug, migrations.RunPython.noop)
    ]
