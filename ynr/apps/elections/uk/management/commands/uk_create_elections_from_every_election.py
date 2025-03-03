from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import Election
from elections.uk.every_election import EveryElectionImporter


class Command(BaseCommand):
    help = "Create posts and elections from a EveryElection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Do a full import of all elections",
        )

    def import_approved_elections(self, full=False):
        # Get all approved elections from EveryElection
        query_args = None
        if full:
            query_args = {}
        ee_importer = EveryElectionImporter(query_args)
        ee_importer.build_election_tree()

        for ballot_id, election_dict in ee_importer.ballot_ids.items():
            parent = ee_importer.get_parent(ballot_id)
            election_dict.get_or_create_ballot(parent=parent)

    def delete_deleted_elections(self):
        # Get all deleted elections from EE
        ee_importer = EveryElectionImporter(
            {
                "poll_open_date__gte": str(date.today() - timedelta(days=30)),
                "deleted": 1,
            }
        )
        ee_importer.build_election_tree()

        for ballot_id, election_dict in ee_importer.ballot_ids.items():
            election_dict.delete_ballot()

        for group_id, election_dict in ee_importer.group_ids.items():
            election_dict.delete_election()

    def handle(self, *args, **options):

        with transaction.atomic():
            # Mark all elections as not current, any that are current will
            # be (re)set later
            Election.objects.update(current=False)

            self.import_approved_elections(full=options["full"])
            self.delete_deleted_elections()
