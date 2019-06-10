from django.test import TestCase
from candidates.tests.uk_examples import UK2015ExamplesMixin

from data_exports.models import MaterializedMemberships


class TestMaterializedMemberships(UK2015ExamplesMixin, TestCase):
    def test_foo(self):

        self.create_lots_of_candidates(
            self.earlier_election, ((self.labour_party, 16), (self.ld_party, 8))
        )
        self.create_lots_of_candidates(
            self.election, ((self.labour_party, 16), (self.ld_party, 8))
        )

        # self.labour_party.membership_set.first().person.tmp_person_identifiers.create(value_type="twitter_username", value="foo")
        print(MaterializedMemberships().recreate_view())

        import ipdb

        ipdb.set_trace()
