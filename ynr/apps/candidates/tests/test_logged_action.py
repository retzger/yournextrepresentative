from django.test import TestCase

import people.tests.factories
from candidates.models import Ballot, LoggedAction

from . import factories
from .auth import TestUserMixin
from .uk_examples import UK2015ExamplesMixin


class TestLoggedAction(TestUserMixin, UK2015ExamplesMixin, TestCase):
    def test_logged_action_repr(self):
        person = people.tests.factories.PersonFactory.create(
            id="9876", name="Test Candidate"
        )
        action = LoggedAction.objects.create(
            user=self.user,
            action_type="person-create",
            ip_address="127.0.0.1",
            person=person,
            popit_person_new_version="1234567890abcdef",
            source="Just for tests...",
        )
        self.assertEqual(
            repr(action),
            str("<LoggedAction: username='john' action_type='person-create'>"),
        )

    def test_subject_person(self):
        person = people.tests.factories.PersonFactory.create(
            id="9876", name="Test Candidate"
        )
        action = LoggedAction.objects.create(
            user=self.user,
            action_type="person-create",
            ip_address="127.0.0.1",
            person=person,
            popit_person_new_version="1234567890abcdef",
            source="Just for tests...",
        )
        self.assertEqual(
            action.subject_html,
            '<a href="/person/9876">Test Candidate (9876)</a>',
        )

    def test_subject_post(self):
        action = LoggedAction.objects.create(
            user=self.user,
            action_type="constituency-lock",
            ip_address="127.0.0.1",
            post=self.camberwell_post,
            popit_person_new_version="1234567890abcdef",
            source="Just for tests...",
        )
        self.assertEqual(
            action.subject_html,
            '<a href="/elections/parl.65913.2015-05-07/">Camberwell and Peckham (65913)</a>',
        )

    def test_guess_of_ballot_current(self):
        action = LoggedAction.objects.create(
            user=self.user,
            action_type="constituency-lock",
            ip_address="127.0.0.1",
            post=self.camberwell_post,
            popit_person_new_version="1234567890abcdef",
            source="Just for tests...",
        )
        self.assertEqual(
            action.ballot_guess,
            Ballot.objects.get(
                election=self.election, post=self.camberwell_post
            ),
        )

    def test_guess_of_ballots_past(self):
        past_election = factories.ElectionFactory.create(
            current=False,
            name="2017 Essex County Council local election",
            election_date="2017-05-04",
        )
        council = factories.OrganizationFactory.create(
            name="Essex County Council"
        )
        post = factories.PostFactory.create(
            elections=(past_election,),
            slug="CED:19782",
            label="CED:19782",
            party_set=self.gb_parties,
            organization=council,
        )
        action = LoggedAction.objects.create(
            user=self.user,
            action_type="constituency-lock",
            ip_address="127.0.0.1",
            post=post,
            popit_person_new_version="1234567890abcdef",
            source="Just for tests...",
        )
        self.assertEqual(
            action.ballot_guess,
            Ballot.objects.get(election=past_election, post=post),
        )
