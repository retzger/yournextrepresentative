from django.core.management.base import BaseCommand

from data_exports.models import MaterializedMemberships


class Command(BaseCommand):
    help = "Updates the MaterializedMemberships materialized view"

    def add_arguments(self, parser):
        parser.add_argument("--drop", action="store_true")

    def handle(self, *args, **options):
        if options["drop"]:
            MaterializedMemberships.recreate_view()
        else:
            MaterializedMemberships.refresh_view()
