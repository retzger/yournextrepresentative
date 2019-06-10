from django.views.generic import TemplateView

from .filters import MaterializedMembershipFilter


# class BallotFilter(django_filters.FilterSet):
#     class Meta:
#         model = PostExtraElection
#         fields = ["year__foo"]
#         filter_overrides = {}
#
#     year__foo = django_filters.MultipleChoiceFilter(
#         choices=[
#             (y.year, y.year)
#             for y in Election.objects.annotate(year=TruncYear("election_date"))
#             .values("year")
#             .annotate(c=Count("year"))
#             .values("year", "c")
#             .order_by("year")
#             .values_list("year", flat=True)
#         ],
#         field_name="election__election_date__year",
#         widget=CheckboxSelectMultiple,
#         label="Election Year",
#     )
#       # , widget=RadioSelect, choices=(("Yes", "True"), ("No", "False"), ("All", "all")))
#


class DataHomeView(TemplateView):
    """
    A view for presenting all options for getting all data out of this site
    """

    template_name = "frontend/data_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filterset = MaterializedMembershipFilter(self.request.GET)
        queryset = filterset.qs
        # queryset = queryset.select_related("person").defer("person__versions", "person__biography")

        context["filter"] = filterset
        context["objects"] = queryset.order_by("-election_date")[:10]
        return context
