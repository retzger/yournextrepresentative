import re

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.http import urlquote

from candidates.models.auth import (
    ChangeToLockedConstituencyDisallowedException,
    NameChangeDisallowedException,
)


class DisallowedUpdateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exc):
        if isinstance(exc, NameChangeDisallowedException):
            intro = "As a precaution, an update was blocked:"
            outro = "If this update is appropriate, someone should apply it manually."

            # Then email the support address about the name change...
            message = "{intro}\n\n  {message}\n\n{outro}".format(
                intro=intro, message=exc, outro=outro
            )
            send_mail(
                "Disallowed {site_name} update for checking".format(
                    site_name=Site.objects.get_current().name
                ),
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=False,
            )
            # And redirect to a page explaining to the user what has happened
            disallowed_explanation_url = reverse("update-disallowed")
            return HttpResponseRedirect(disallowed_explanation_url)
        elif isinstance(exc, ChangeToLockedConstituencyDisallowedException):
            return HttpResponseForbidden()


class CopyrightAssignmentMiddleware:
    """Check that authenticated users have agreed to copyright assigment

    This must come after AuthenticationMiddleware so that request.user
    is present.

    If this is an authenticated user, then insist that they agree to
    assign copyright of any contributions to the COPYRIGHT_HOLDER in
    settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        return response

    EXCLUDED_PATHS = (
        re.compile(r"^/copyright-question"),
        re.compile(r"^/accounts/"),
        re.compile(r"^/admin/"),
    )

    def process_request(self, request):
        for path_re in self.EXCLUDED_PATHS:
            if path_re.search(request.path):
                return None
        if not request.user.is_authenticated:
            return None
        if request.session.get("terms_agreement_assigned_to_dc") == True:
            return None

        already_assigned = request.user.terms_agreement.assigned_to_dc
        if already_assigned:
            request.session["terms_agreement_assigned_to_dc"] = True
            request.session.save()
            return None
        else:
            # Then redirect to a view that asks you to assign
            # copyright:
            assign_copyright_url = reverse("ask-for-copyright-assignment")
            assign_copyright_url += "?next={}".format(urlquote(request.path))
            return HttpResponseRedirect(assign_copyright_url)


class DisableCachingForAuthenticatedUsers:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_response(request, self.get_response(request))
        return response

    EXCLUDED_PATHS = (re.compile(r"^/static"), re.compile(r"^/media"))

    def process_response(self, request, response):
        if hasattr(request, "user") and request.user.is_authenticated:
            if all(
                path_re.search(request.path) is None
                for path_re in self.EXCLUDED_PATHS
            ):
                add_never_cache_headers(response)

        return response


class LogoutDisabledUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        return response

    def process_request(self, request):
        if (
            hasattr(request, "user")
            and request.user.is_authenticated
            and not request.user.is_active
        ):
            logout(request)
