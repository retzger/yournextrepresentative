from django.core.management.base import BaseCommand

from candidates.models import Ballot
from compat import BufferDictWriter


class Command(BaseCommand):

    help = """
    Create a CSV file that can be populated and imported by
    candidates_import_statements_of_persons_nominated
    """

    fieldnames = [
        "ballot_paper_id",
        "Election name",
        "Area name",
        "Council webpage likely to link to SOPN",
        "Link to PDF",
        "Notes",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--election-date", action="store", required=True)

        parser.add_argument(
            "--non-current",
            action="store_true",
            help="Also include elections marked as not current",
        )

    def handle(self, *args, **options):

        out_csv = BufferDictWriter(self.fieldnames)
        out_csv.writeheader()

        qs = (
            Ballot.objects.filter(
                election__election_date=options["election_date"]
            )
            .select_related("election", "postextra", "post")
            .order_by("election__slug")
        )

        if not options["non_current"]:
            qs = qs.filter(election__current=True)

        for ballot in qs:
            row = {
                "ballot_paper_id": ballot.ballot_paper_id,
                "Election name": ballot.election.name,
                "Area name": ballot.post.label,
                "Council webpage likely to link to SOPN": "",
                "Link to PDF": "",
                "Notes": "",
            }
            out_csv.writerow(row)

        self.stdout.write(out_csv.output)
