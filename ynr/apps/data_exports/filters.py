import django_filters

from .models import MaterializedMemberships


BY_ELECTION_CHOICES = {
    ("", "Yes"),
    ("True", "Only by-elections"),
    ("False", "Exclude by-elections"),
}


class BallotPaperText(django_filters.CharFilter):
    field_name = "ballot_paper_id"

    def filter(self, qs, value):
        if value:
            qs = qs.filter(ballot_paper__ballot_paper_id__regex=value)
        return qs


class MaterializedMembershipFilter(django_filters.FilterSet):
    election_date = django_filters.CharFilter(lookup_expr="iexact")
    by_election = django_filters.ChoiceFilter(
        field_name="is_by_election",
        label="Include by-elections?",
        lookup_expr="exact",
        choices=BY_ELECTION_CHOICES,
        empty_label=None,
    )

    ballot_paper_id = BallotPaperText()

    class Meta:
        model = MaterializedMemberships
        fields = ["election_date", "by_election", "ballot_paper_id"]

        # fields = {
        #     'by_election': ['exact'],
        #     'election_date': ['exact', 'year'],
        # }
