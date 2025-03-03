import re

from django.core.management import call_command
from django_webtest import WebTest

from people.models import Person

from .auth import TestUserMixin
from .uk_examples import UK2015ExamplesMixin


class TestSearchView(TestUserMixin, UK2015ExamplesMixin, WebTest):
    def setUp(self):
        super().setUp()
        call_command("rebuild_index", verbosity=0, interactive=False)

    def test_search_page(self):
        # we have to create the candidate by submitting the form as otherwise
        # we're not making sure the index update hook fires
        response = self.app.get("/search?q=Elizabeth")
        # have to use re to avoid matching search box
        self.assertFalse(re.search(r"""<a[^>]*>Elizabeth""", response.text))

        self.assertFalse(re.search(r"""<a[^>]*>Mr Darcy""", response.text))

        response = self.app.get(
            self.dulwich_post_ballot.get_absolute_url(), user=self.user
        )
        form = response.forms["new-candidate-form"]
        form["name"] = "Mr Darcy"
        form["tmp_person_identifiers-0-value"] = "darcy@example.com"
        form["tmp_person_identifiers-0-value_type"] = "email"
        form["source"] = "Testing adding a new person to a post"
        form["party_GB_parl.2015-05-07"] = self.labour_party.ec_id
        form.submit()

        response = self.app.get(
            self.dulwich_post_ballot.get_absolute_url(), user=self.user
        )
        form = response.forms["new-candidate-form"]
        form["name"] = "Elizabeth Bennet"
        form["tmp_person_identifiers-0-value"] = "lizzie@example.com"
        form["tmp_person_identifiers-0-value_type"] = "email"
        form["source"] = "Testing adding a new person to a post"
        form["party_GB_parl.2015-05-07"] = self.labour_party.ec_id
        form.submit()

        response = self.app.get(
            self.dulwich_post_ballot.get_absolute_url(), user=self.user
        )
        form = response.forms["new-candidate-form"]
        form["name"] = "Charlotte O'Lucas"  # testers license
        form["tmp_person_identifiers-0-value"] = "charlotte@example.com"
        form["tmp_person_identifiers-0-value_type"] = "email"
        form["source"] = "Testing adding a new person to a post"
        form["party_GB_parl.2015-05-07"] = self.labour_party.ec_id
        form.submit()

        # check searching finds them
        response = self.app.get("/search?q=Elizabeth")
        self.assertTrue(re.search(r"""<a[^>]*>Elizabeth""", response.text))

        self.assertFalse(re.search(r"""<a[^>]*>Mr Darcy""", response.text))

        response = self.app.get(
            self.dulwich_post_ballot.get_absolute_url(), user=self.user
        )
        form = response.forms["new-candidate-form"]
        form["name"] = "Elizabeth Jones"
        form["tmp_person_identifiers-0-value"] = "e.jones@example.com"
        form["tmp_person_identifiers-0-value_type"] = "email"
        form["source"] = "Testing adding a new person to a post"
        form["party_GB_parl.2015-05-07"] = self.labour_party.ec_id
        form.submit()

        response = self.app.get("/search?q=Elizabeth")
        self.assertTrue(
            re.search(r"""<a[^>]*>Elizabeth Bennet""", response.text)
        )
        self.assertTrue(
            re.search(r"""<a[^>]*>Elizabeth Jones""", response.text)
        )

        person = Person.objects.get(name="Elizabeth Jones")
        response = self.app.get(
            "/person/{}/update".format(person.id), user=self.user
        )
        form = response.forms["person-details"]
        form["name"] = "Lizzie Jones"
        form["source"] = "Some source of this information"
        form.submit()

        response = self.app.get("/search?q=Elizabeth")
        self.assertTrue(
            re.search(r"""<a[^>]*>Elizabeth Bennet""", response.text)
        )
        self.assertFalse(
            re.search(r"""<a[^>]*>Elizabeth Jones""", response.text)
        )

        # check that searching for names with apostrophe works
        response = self.app.get("/search?q=O'Lucas")
        self.assertTrue(re.search(r"""<a[^>]*>Charlotte""", response.text))

        # check that searching with middle names works
        response = self.app.get("/search?q=Elizabeth+Mary+Bennet")
        self.assertTrue(
            re.search(r"""<a[^>]*>Elizabeth Bennet""", response.text)
        )
