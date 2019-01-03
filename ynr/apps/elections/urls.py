from django.conf.urls import url

from elections import views

urlpatterns = [
    url(
        "elections/$",
        views.ElectionListView.as_view(),
        name="election_list_view",
    ),
    url(
        "elections/(?P<election>[^/]+)/$",
        views.ElectionView.as_view(),
        name="election_view",
    ),
    url(
        r"^elections/(?P<election>[^/]+)/unlocked/",
        views.UnlockedBallotsForElectionListView.as_view(),
        name="constituencies-unlocked",
    ),
]
