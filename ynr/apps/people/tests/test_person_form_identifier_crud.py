from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTest

from candidates.tests.auth import TestUserMixin
from candidates.tests.factories import faker_factory
from people.models import PersonIdentifier
from people.tests.factories import PersonFactory


@override_settings(TWITTER_APP_ONLY_BEARER_TOKEN=None)
class PersonFormsIdentifierCRUDTestCase(TestUserMixin, WebTest):
    def setUp(self):
        # super().setUp()
        self.person = PersonFactory(name=faker_factory.name())
        self.pi = PersonIdentifier.objects.create(
            person=self.person,
            value="democlub",
            value_type="twitter_username",
            internal_identifier="123456",
        )

    def test_person_identifier_on_form(self):
        """
        Test that the PersonIdentifier is listed on the Person form.
        """
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        pi_form = resp.context["identifiers_formset"].initial_forms[0]

        self.assertEqual(pi_form["value"].value(), "democlub")
        self.assertEqual(pi_form["value_type"].value(), "twitter_username")

    def test_form_can_add_new_pi(self):
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "Adding a home page"
        form["tmp_person_identifiers-1-value"] = "https://democracyclub.org.uk"
        form["tmp_person_identifiers-1-value_type"] = "homepage_url"
        form.submit()

        self.assertEqual(PersonIdentifier.objects.all().count(), 2)
        self.assertEqual(
            list(PersonIdentifier.objects.values_list("value", flat=True)),
            ["https://democracyclub.org.uk", "democlub"],
        )
        # Check that internal IDs still exist for unchanged values
        self.assertEqual(
            PersonIdentifier.objects.get(
                value_type="twitter_username"
            ).internal_identifier,
            "123456",
        )

    def test_form_can_update_pi(self):
        """
        Test that the PersonIdentifier can be updated
        """
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "They changed their username"
        form["tmp_person_identifiers-0-value"] = "@democracyclub"
        form.submit()

        pi = PersonIdentifier.objects.get()
        self.assertEqual(pi.value, "democracyclub")
        self.assertEqual(pi.value_type, "twitter_username")

    def test_form_can_delete_pi(self):
        """
        Test that the PersonIdentifier can be deleted by removing the value
        """
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "They deleted their account"
        form["tmp_person_identifiers-0-value"] = ""
        form.submit()

        self.assertFalse(PersonIdentifier.objects.exists())

    def test_form_valid_when_extra_value_type_selected(self):
        """
        If someone selects a value type but doesn't enter a value, it's still valid
        """
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "Just picking something from the dropdown"
        form["tmp_person_identifiers-1-value_type"] = "twitter_username"
        resp = form.submit()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.location,
            reverse("person-view", kwargs={"person_id": self.person.pk}),
        )

        self.assertEqual(PersonIdentifier.objects.get().value, "democlub")

    def test_change_value_type(self):
        """
        The value stays the same, but the type changes
        """
        self.assertEqual(
            PersonIdentifier.objects.get().value_type, "twitter_username"
        )
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "Just picking something from the dropdown"
        form["tmp_person_identifiers-0-value_type"] = "homepage_url"
        resp = form.submit()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.location,
            reverse("person-view", kwargs={"person_id": self.person.pk}),
        )

        self.assertEqual(
            PersonIdentifier.objects.get().value_type, "homepage_url"
        )

    def _submit_values(self, value, value_type="twitter_username"):
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "They changed their username"
        form["tmp_person_identifiers-0-value_type"] = value_type
        form["tmp_person_identifiers-0-value"] = value
        form.submit()
        return form.submit()

    def test_twitter_bad_url(self):
        resp = self._submit_values("http://example.com/blah")
        form = resp.context["identifiers_formset"]
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form[0].non_field_errors(),
            [
                "The Twitter username must only consist of alphanumeric characters or underscore"
            ],
        )

    def test_twitter_full_url(self):
        resp = self._submit_values("https://twitter.com/madeuptwitteraccount")
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(
            PersonIdentifier.objects.get().value, "madeuptwitteraccount"
        )

    def test_bad_email_address(self):
        resp = self._submit_values("whoops", "email")
        form = resp.context["identifiers_formset"]
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form[0].non_field_errors(), ["Enter a valid email address."]
        )

    def test_clean_wikidata_ids(self):
        resp = self._submit_values("Whoops", "wikidata_id")
        form = resp.context["identifiers_formset"]
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form[0].non_field_errors(),
            ["Wikidata ID be a 'Q12345' type identifier"],
        )

        self._submit_values(
            "http://www.wikidata.org/entity/Q391562", "wikidata_id"
        )
        self.person.refresh_from_db()
        self.assertEqual(
            self.person.get_single_identifier_of_type("wikidata_id").value,
            "Q391562",
        )

    def test_remove_internal_id_on_user_save(self):
        """
        This tests for a specific condition:


        1. A Twitter user name is added, no internal ID is added
        2. Time passes, and the user changes their username
        3. Another person comes along and creates an account with the old
           username
        4. TwitterBot attaches the internal ID to the screen name, however this
           is now the wrong person's account
        5. A user to the site corrects the username
        6. TwitterBot comes along and "corrects" the username back to the screen
           name that maatches the internal ID (because it's designed to alter
           screen names)

        Basically the user can never stop TwitterBot from doing this,
        without removing the Twitter account and re-adding it in two saves.

        It's better to assume the screen name change is valid as per the user
        edit and remove the internal ID at time of edit, for TwitterBot to add
        later.
        """
        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        form = resp.forms[1]
        form["source"] = "They changed their username"
        form["tmp_person_identifiers-0-value"] = "democracyclub"
        form.submit()

        pi = PersonIdentifier.objects.get()
        self.assertEqual(pi.value, "democracyclub")
        self.assertEqual(pi.value_type, "twitter_username")
        self.assertEqual(pi.internal_identifier, None)

    def test_duplicate_values_raises_form_error(self):

        resp = self.app.get(
            reverse("person-update", kwargs={"person_id": self.person.pk}),
            user=self.user,
        )

        pi = PersonIdentifier.objects.create(
            person=self.person,
            value_type="facebook_personal_url",
            value="https://www.facebook.com/example",
        )

        form = resp.forms[1]
        form["source"] = "They changed their username"
        form["tmp_person_identifiers-0-value_type"] = "email"
        form["tmp_person_identifiers-0-value"] = "person@example.com"

        form[
            "tmp_person_identifiers-1-value"
        ] = "https://www.facebook.com/example"
        form["tmp_person_identifiers-1-value_type"] = "facebook_page_url"

        form["tmp_person_identifiers-2-id"] = pi.pk
        form["tmp_person_identifiers-2-value"] = ""
        form["tmp_person_identifiers-2-value_type"] = "facebook_personal_url"

        resp = form.submit()

        self.assertEqual(resp.status_code, 302)
        resp.follow()
        self.assertEqual(
            resp.context["person"].tmp_person_identifiers.count(), 2
        )
