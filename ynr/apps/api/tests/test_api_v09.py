import json
from datetime import datetime
from os.path import join

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import DefaultStorage
from django.core.management import call_command
from django_webtest import WebTest
from mock import patch

from candidates.models import LoggedAction, PersonRedirect
from candidates.tests.auth import TestUserMixin
from candidates.tests.factories import MembershipFactory
from candidates.tests.helpers import TmpMediaRootMixin
from candidates.tests.uk_examples import UK2015ExamplesMixin
from moderation_queue.tests.paths import EXAMPLE_IMAGE_FILENAME
from people.models import PersonIdentifier, PersonImage
from people.tests.factories import PersonFactory


class TestAPI(TestUserMixin, TmpMediaRootMixin, UK2015ExamplesMixin, WebTest):
    def setUp(self):
        super().setUp()

        person = PersonFactory.create(id=2009, name="Tessa Jowell")
        PersonImage.objects.update_or_create_from_file(
            EXAMPLE_IMAGE_FILENAME,
            "images/imported.jpg",
            person,
            defaults={
                "md5sum": "md5sum",
                "copyright": "example-license",
                "uploading_user": self.user,
                "user_notes": "Here's an image...",
                "is_primary": True,
                "source": "Found on the candidate's Flickr feed",
            },
        )
        dulwich_not_stand = PersonFactory.create(id=4322, name="Helen Hayes")
        edinburgh_candidate = PersonFactory.create(
            id="818", name="Sheila Gilmore"
        )
        edinburgh_winner = PersonFactory.create(
            id="5795", name="Tommy Sheppard"
        )
        edinburgh_may_stand = PersonFactory.create(
            id="5163", name="Peter McColl"
        )
        MembershipFactory.create(
            person=person,
            post=self.dulwich_post,
            party=self.labour_party,
            ballot=self.dulwich_post_ballot,
        )
        MembershipFactory.create(
            person=person, ballot=self.edinburgh_east_post_ballot
        )

        MembershipFactory.create(
            person=dulwich_not_stand,
            post=self.dulwich_post,
            party=self.labour_party,
            ballot=self.dulwich_post_ballot_earlier,
        )
        dulwich_not_stand.not_standing.add(self.election)

        MembershipFactory.create(
            person=edinburgh_winner,
            post=self.edinburgh_east_post,
            party=self.labour_party,
            elected=True,
            ballot=self.edinburgh_east_post_ballot,
        )

        MembershipFactory.create(
            person=edinburgh_candidate,
            post=self.edinburgh_east_post,
            party=self.labour_party,
            ballot=self.edinburgh_east_post_ballot,
        )

        MembershipFactory.create(
            person=edinburgh_may_stand,
            post=self.edinburgh_east_post,
            party=self.labour_party,
            ballot=self.edinburgh_east_post_ballot_earlier,
        )

        self.storage = DefaultStorage()

    def test_api_basic_response(self):
        response = self.app.get("/api/v0.9/")
        self.assertEqual(response.status_code, 200)
        json = response.json

        self.assertEqual(json["persons"], "http://testserver/api/v0.9/persons/")
        self.assertEqual(
            json["organizations"], "http://testserver/api/v0.9/organizations/"
        )
        self.assertEqual(
            json["elections"], "http://testserver/api/v0.9/elections/"
        )
        self.assertEqual(json["posts"], "http://testserver/api/v0.9/posts/")

        persons_resp = self.app.get("/api/v0.9/persons/")
        self.assertEqual(persons_resp.status_code, 200)

        organizations_resp = self.app.get("/api/v0.9/organizations/")
        self.assertEqual(organizations_resp.status_code, 200)

        elections_resp = self.app.get("/api/v0.9/elections/")
        self.assertEqual(elections_resp.status_code, 200)

        posts_resp = self.app.get("/api/v0.9/posts/")
        self.assertEqual(posts_resp.status_code, 200)

    def test_api_home(self):
        response = self.app.get("/api/")
        self.assertEqual(response.status_code, 302)

        response = self.app.get("/api/docs/")
        self.assertEqual(response.status_code, 200)

        response = self.app.get("/api/v0.8", expect_errors=True)
        self.assertEqual(response.status_code, 404)

        response = self.app.get("/api/v0.9/person/", expect_errors=True)
        self.assertEqual(response.status_code, 404)

        response = self.app.get("/api/v0.9/persons/4000/", expect_errors=True)
        self.assertEqual(response.status_code, 404)

        response = self.app.post(
            "/api/v0.9/persons/", params={}, expect_errors=True
        )
        self.assertEqual(response.status_code, 403)

    def test_api_persons(self):
        persons_resp = self.app.get("/api/v0.9/persons/")

        persons = persons_resp.json

        self.assertEqual(persons["count"], len(persons["results"]))
        self.assertEqual(persons["count"], 5)

    def test_api_person(self):
        person_resp = self.app.get("/api/v0.9/persons/2009/")

        self.assertEqual(person_resp.status_code, 200)

        person = person_resp.json
        self.assertEqual(person["id"], 2009)
        self.assertEqual(person["name"], "Tessa Jowell")

        memberships = sorted(person["memberships"], key=lambda m: m["role"])

        self.assertEqual(len(memberships), 2)
        self.assertEqual(memberships[1]["role"], "Candidate")

        self.assertEqual(len(person["versions"]), 0)

    def _make_legacy_parties(self):
        """
        It used to be that political parties were stored on the "Organization"
        model. for maintaining v0.9 API compatibility we've not deleted them
        from that model (yet), so let's make the test data support this legacy
        case
        """

        from candidates.tests.factories import OrganizationFactory
        from candidates.tests.uk_examples import EXAMPLE_PARTIES

        for party in EXAMPLE_PARTIES:
            p = OrganizationFactory(
                slug=party["legacy_slug"], name=party["name"]
            )

    def test_api_legacy_organizations_with_parties(self):
        self._make_legacy_parties()
        organizations_resp = self.app.get("/api/v0.9/organizations/")

        organizations = organizations_resp.json

        self.assertEqual(organizations["count"], len(organizations["results"]))
        self.assertEqual(organizations["count"], 7)

    def test_api_legacy_organization_with_parties(self):
        self._make_legacy_parties()
        organizations_resp = self.app.get("/api/v0.9/organizations/")
        organizations = organizations_resp.json

        organization_url = None
        for organization in organizations["results"]:
            if organization["id"] == "party:53":
                organization_url = organization["url"]
                break

        organization_resp = self.app.get(organization_url)
        self.assertEqual(organization_resp.status_code, 200)

        organization = organization_resp.json
        self.assertEqual(organization["id"], "party:53")
        self.assertEqual(organization["name"], "Labour Party")

    def test_api_elections(self):
        elections_resp = self.app.get("/api/v0.9/elections/")

        elections = elections_resp.json

        self.assertEqual(elections["count"], len(elections["results"]))
        self.assertEqual(elections["count"], 3)

    def test_api_elections_without_orgs(self):
        # Regression test that we can serve elections without an organzation
        self.election.organization = None
        self.election.save()
        elections_resp = self.app.get(
            "/api/v0.9/elections/", expect_errors=True
        )
        self.assertEqual(elections_resp.status_code, 200)

    def test_api_election(self):
        elections_resp = self.app.get("/api/v0.9/elections/")
        elections = elections_resp.json

        election_url = None
        for election in elections["results"]:
            if election["id"] == "parl.2015-05-07":
                election_url = election["url"]
                break

        election_resp = self.app.get(election_url)
        self.assertEqual(election_resp.status_code, 200)

        election = election_resp.json
        self.assertEqual(election["id"], "parl.2015-05-07")
        self.assertEqual(election["name"], "2015 General Election")

    def test_api_posts(self):
        posts_resp = self.app.get("/api/v0.9/posts/")

        posts = posts_resp.json

        self.assertEqual(posts["count"], len(posts["results"]))
        self.assertEqual(posts["count"], 5)

    def test_api_post(self):
        posts_resp = self.app.get("/api/v0.9/posts/")
        posts = posts_resp.json

        post_url = None
        for post in posts["results"]:
            if post["id"] == "65808":
                post_url = post["url"]
                break

        self.assertTrue(post_url)
        post_resp = self.app.get(post_url)
        self.assertEqual(post_resp.status_code, 200)

        post = post_resp.json

        self.assertEqual(post["id"], "65808")
        self.assertEqual(
            post["label"], "Member of Parliament for Dulwich and West Norwood"
        )

    def test_api_person_redirects(self):
        PersonRedirect.objects.create(old_person_id="1234", new_person_id="42")
        PersonRedirect.objects.create(old_person_id="5678", new_person_id="12")
        person_redirects_resp = self.app.get("/api/v0.9/person_redirects/")
        person_redirects = person_redirects_resp.json
        self.assertEqual(person_redirects["results"][0]["old_person_id"], 1234)
        self.assertEqual(person_redirects["results"][0]["new_person_id"], 42)
        self.assertEqual(person_redirects["results"][1]["old_person_id"], 5678)
        self.assertEqual(person_redirects["results"][1]["new_person_id"], 12)

    def test_api_person_redirect(self):
        PersonRedirect.objects.create(old_person_id="1234", new_person_id="42")
        url = "/api/v0.9/person_redirects/1234/"
        person_redirect_resp = self.app.get(url)
        person_redirect = person_redirect_resp.json
        self.assertEqual(person_redirect["old_person_id"], 1234)
        self.assertEqual(person_redirect["new_person_id"], 42)

    def test_api_version_info(self):
        version_resp = self.app.get("/version.json")
        self.assertEqual(version_resp.status_code, 200)

        info = version_resp.json
        self.assertEqual(info["users_who_have_edited"], 0)
        self.assertEqual(info["interesting_user_actions"], 0)

        LoggedAction.objects.create(action_type="set-candidate-not-elected")

        LoggedAction.objects.create(action_type="edit-candidate")

        version_resp = self.app.get("/version.json")
        info = version_resp.json
        self.assertEqual(info["interesting_user_actions"], 1)

    def test_api_cors_headers(self):
        resp = self.app.get(
            "/api/v0.9/", headers={"Origin": b"http://example.com"}
        )
        self.assertTrue("Access-Control-Allow-Origin" in resp.headers)
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "*")

        resp = self.app.get("/", headers={"Origin": b"http://example.com"})
        self.assertFalse("Access-Control-Allow-Origin" in resp.headers)

    def test_api_jsonp_response(self):
        response = self.app.get("/api/v0.9/?format=jsonp&callback=test")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text.startswith("test("))

    @patch(
        "candidates.management.commands.candidates_cache_api_to_directory.datetime"
    )
    def test_persons_api_to_directory(self, mock_datetime):
        # current
        # timestamped
        # timestamped
        mock_datetime.now.return_value = datetime(2017, 5, 14, 12, 33, 5, 0)
        target_directory = settings.MEDIA_ROOT
        call_command(
            "candidates_cache_api_to_directory",
            page_size="3",
            url_prefix="https://example.com/media/api-cache-for-wcivf",
        )
        expected_leafname = "2017-05-14T12:33:05"
        expected_timestamped_directory = join(
            settings.MEDIA_ROOT, "cached-api", expected_leafname
        )
        expected_path = join("cached-api", "latest")
        self.assertTrue(self.storage.exists(expected_timestamped_directory))
        self.assertTrue(self.storage.exists(expected_path))
        # Check that the files in that directory are as expected:
        entries = self.storage.listdir(expected_timestamped_directory)[1]
        people_1_leafname = "people-000001.json"
        people_2_leafname = "people-000002.json"

        ballot_1_leafname = "ballots-000001.json"
        ballot_2_leafname = "ballots-000002.json"
        ballot_3_leafname = "ballots-000003.json"

        self.assertEqual(
            set(entries),
            {
                people_1_leafname,
                people_2_leafname,
                ballot_1_leafname,
                ballot_2_leafname,
                ballot_3_leafname,
            },
        )
        # Get the data from those pages:
        with self.storage.open(
            join(expected_timestamped_directory, people_1_leafname)
        ) as f:
            persons_1_data = json.loads(f.read().decode("utf8"))
        with self.storage.open(
            join(expected_timestamped_directory, people_2_leafname)
        ) as f:
            persons_2_data = json.loads(f.read().decode("utf8"))

        # Check the previous and next links are as we expect:
        self.assertEqual(
            persons_1_data["next"],
            "https://example.com/media/api-cache-for-wcivf/{}/{}".format(
                expected_leafname, people_2_leafname
            ),
        )
        self.assertEqual(persons_1_data["previous"], None)
        self.assertEqual(persons_2_data["next"], None)
        self.assertEqual(
            persons_2_data["previous"],
            "https://example.com/media/api-cache-for-wcivf/{}/{}".format(
                expected_leafname, people_1_leafname
            ),
        )
        # Check that the URL of the first person is as expected,
        # as well as it being the right person:
        first_person = persons_1_data["results"][0]
        self.assertEqual(first_person["id"], 818)
        self.assertEqual(first_person["name"], "Sheila Gilmore")
        self.assertEqual(
            first_person["url"],
            "https://candidates.democracyclub.org.uk/api/next/people/818/?format=json",
        )

    def _setup_cached_api_directory(self, dir_list):
        """
        Saves a tmp file in settings.MEDIA_ROOT, called `.keep` in each
        directory in dir_list.

        """
        for d in dir_list:
            self.storage.save(join("cached-api", d, ".keep"), ContentFile("."))

    @patch(
        "candidates.management.commands.candidates_cache_api_to_directory.datetime"
    )
    def test_cache_api_to_directory_prune(self, mock_datetime):
        # Need to make sure datetime.strptime still works:
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2017, 5, 14, 12, 33, 5, 0)

        expected_to_prune = [
            "2017-05-12T08:00:00",
            "2017-05-12T10:00:00",
            "2017-05-12T12:00:00",
        ]
        expected_to_keep = [
            "2017-05-14T08:00:00",
            "2017-05-14T10:00:00",
            "2017-05-14T12:00:00",
            "2017-05-14T12:33:05",
        ]

        self._setup_cached_api_directory(expected_to_keep + expected_to_prune)

        self.assertTrue(
            self.storage.exists(
                join("cached-api", "2017-05-12T08:00:00", ".keep")
            )
        )

        call_command(
            "candidates_cache_api_to_directory",
            page_size="3",
            url_prefix="https://example.com/media/api-cache-for-wcivf/",
            prune=True,
        )

        for dir_name in expected_to_keep:
            self.assertTrue(
                self.storage.exists(join("cached-api", dir_name, ".keep"))
            )

        for dir_name in expected_to_prune:
            self.assertFalse(
                self.storage.exists(join("cached-api", dir_name, ".keep"))
            )

    @patch(
        "candidates.management.commands.candidates_cache_api_to_directory.datetime"
    )
    def test_cache_api_to_directory_prune_four_old(self, mock_datetime):
        # Need to make sure datetime.strptime still works:
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2017, 5, 14, 12, 33, 5, 0)

        expected_to_prune = ["2017-05-12T06:00:00"]
        expected_to_keep = [
            "2017-05-12T08:00:00",
            "2017-05-12T10:00:00",
            "2017-05-12T12:00:00",
            "2017-05-14T12:33:05",
        ]

        self._setup_cached_api_directory(expected_to_keep + expected_to_prune)

        self.assertTrue(
            self.storage.exists(
                join("cached-api", "2017-05-12T06:00:00", ".keep")
            )
        )

        self.assertTrue(
            self.storage.exists(
                join("cached-api", "2017-05-12T08:00:00", ".keep")
            )
        )

        call_command(
            "candidates_cache_api_to_directory",
            page_size="3",
            url_prefix="https://example.com/media/api-cache-for-wcivf/",
            prune=True,
        )
        # Even though all of those directories are more than 36
        # hours old, they should all be kept because they're the
        # most recent 4:
        for dir_name in expected_to_keep:
            self.assertTrue(
                self.storage.exists(join("cached-api", dir_name, ".keep"))
            )

        for dir_name in expected_to_prune:
            self.assertFalse(
                self.storage.exists(join("cached-api", dir_name, ".keep"))
            )

    def test_legacy_redirects(self):
        req = self.app.get("/api/v0.9/elections/2010/")
        self.assertEqual(req.status_code, 301)
        self.assertEqual(req.location, "/api/v0.9/elections/parl.2010-05-06/")
        req = self.app.get("/api/v0.9/elections/2010.json")
        self.assertEqual(req.status_code, 301)
        self.assertEqual(
            req.location, "/api/v0.9/elections/parl.2010-05-06.json"
        )

    def test_legacy_contact_details(self):
        person = PersonFactory()
        PersonIdentifier.objects.create(
            value_type="twitter_username", value="Froglet4MP", person=person
        )

        req = self.app.get("/api/v0.9/persons/{}/".format(person.pk))
        person_json = req.json
        self.assertTrue("contact_details" in person_json)
        self.assertEqual(
            person_json["contact_details"][0]["contact_type"], "twitter"
        )
        self.assertEqual(
            person_json["contact_details"][0]["value"], "Froglet4MP"
        )
