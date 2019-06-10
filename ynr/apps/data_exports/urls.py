from django.conf.urls import url

from data_exports import views

urlpatterns = [url(r"^$", views.DataHomeView.as_view(), name="data_home")]
