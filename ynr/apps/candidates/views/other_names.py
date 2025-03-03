from braces.views import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from candidates.models import LoggedAction
from people.forms import OtherNameForm
from people.models import Person
from popolo.models import OtherName

from .version_data import get_change_metadata, get_client_ip


class PersonMixin(object):
    @cached_property
    def person(self):
        return Person.objects.get(pk=self.kwargs["person_id"])

    def get_success_url(self):
        return reverse(
            "person-other-names", kwargs={"person_id": self.person.id}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.person
        return context


class PersonOtherNamesView(PersonMixin, ListView):

    model = OtherName
    template_name = "candidates/othername_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        ct = ContentType.objects.get_for_model(Person)
        return qs.filter(
            content_type=ct, object_id=self.kwargs["person_id"]
        ).order_by("name", "start_date", "end_date")


class PersonOtherNameCreateView(LoginRequiredMixin, PersonMixin, CreateView):

    model = OtherName
    form_class = OtherNameForm
    template_name = "candidates/othername_new.html"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = None
        form.instance.content_object = self.person
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            # This is similar to the example here:
            #   https://docs.djangoproject.com/en/1.8/topics/class-based-views/generic-editing/#models-and-request-user

            result = super(PersonOtherNameCreateView, self).form_valid(form)
            change_metadata = get_change_metadata(
                self.request, form.cleaned_data["source"]
            )
            self.person.record_version(change_metadata)
            self.person.save()
            LoggedAction.objects.create(
                user=self.request.user,
                person=self.person,
                action_type="person-other-name-create",
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata["version_id"],
                source=change_metadata["information_source"],
            )
            """
            On the bulk edit page this view is inlined and the data
            sent over ajax so we have to return an ajax response, and
            also the new list of names so we can show the new list of
            alternative names as a confirmation it's all worked
            """
            if self.request.is_ajax():
                qs = super().get_queryset()
                ct = ContentType.objects.get_for_model(Person)
                qs = qs.filter(
                    content_type=ct, object_id=self.person.id
                ).order_by("name", "start_date", "end_date")
                data = {
                    "success": True,
                    "names": list(qs.values_list("name", flat=True)),
                }
                return JsonResponse(data)
            return result

    def form_invalid(self, form):
        result = super(PersonOtherNameCreateView, self).form_invalid(form)
        if self.request.is_ajax():
            data = {"success": False, "errors": form.errors}
            return JsonResponse(data)

        return result


class PersonOtherNameDeleteView(LoginRequiredMixin, PersonMixin, DeleteView):

    model = OtherName
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            result_redirect = super().delete(request, *args, **kwargs)
            change_metadata = get_change_metadata(
                self.request, self.request.POST["source"]
            )
            self.person.record_version(change_metadata)
            self.person.save()
            LoggedAction.objects.create(
                user=self.request.user,
                person=self.person,
                action_type="person-other-name-delete",
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata["version_id"],
                source=change_metadata["information_source"],
            )
            return result_redirect


class PersonOtherNameUpdateView(LoginRequiredMixin, PersonMixin, UpdateView):

    model = OtherName
    form_class = OtherNameForm
    template_name = "candidates/othername_edit.html"
    raise_exception = True

    def form_valid(self, form):
        with transaction.atomic():
            result = super(PersonOtherNameUpdateView, self).form_valid(form)
            change_metadata = get_change_metadata(
                self.request, form.cleaned_data["source"]
            )
            self.person.record_version(change_metadata)
            self.person.save()
            LoggedAction.objects.create(
                user=self.request.user,
                person=self.person,
                action_type="person-other-name-update",
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata["version_id"],
                source=change_metadata["information_source"],
            )
            return result
