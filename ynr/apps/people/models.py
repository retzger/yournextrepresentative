import json
from datetime import date
from enum import Enum, unique
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template import loader
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.six.moves.urllib_parse import quote_plus, urljoin
from django_extensions.db.models import TimeStampedModel
from slugify import slugify
from sorl.thumbnail import get_thumbnail

from candidates.diffs import get_version_diffs
from candidates.models import Ballot
from people.managers import (
    PersonIdentifierQuerySet,
    PersonImageManager,
    PersonQuerySet,
)
from popolo.behaviors.models import Timestampable
from popolo.models import Membership, VersionNotFound


def person_image_path(instance, filename):
    # Ensure the filename isn't too long
    filename = filename[400:]
    # Upload images in a directory per person
    return "images/people/{0}/{1}-{2}".format(
        instance.person.id, uuid.uuid4(), filename
    )


@unique
class EditLimitationStatuses(Enum):
    NEEDS_REVIEW = "Needs review"
    EDITS_PREVENTED = "Edits prevented"


class PersonImage(models.Model):
    """
    Images of people, uploaded by users of the site. It's important we keep
    track of the copyright the uploading user asserts over the image, and any
    notes they have.
    """

    person = models.ForeignKey(
        "people.Person", related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to=person_image_path, max_length=512)
    source = models.CharField(max_length=400)
    copyright = models.CharField(max_length=64, default="other", blank=True)
    uploading_user = models.ForeignKey(
        "auth.User", blank=True, null=True, on_delete=models.CASCADE
    )
    user_notes = models.TextField(blank=True)
    md5sum = models.CharField(max_length=32, blank=True)
    user_copyright = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    objects = PersonImageManager()


class PersonIdentifier(TimeStampedModel):
    """
    This is a model for storing "identifiers" for a person.

    The most simple case is a URL to another website.

    In this case the "value" is "@democlub" (or it could be
    "https"//twitter.com/democlub").

    Twitter uses "vanity URLs" as well as internal identifiers so we can
    store the internal ID that looks like "362837635" on the internal_identifier
    field.

    An identifier value or internal identifier doesn't have to be resolvable
    over HTTP. For example a phone number or snapchat handle are both valid
    values.

    """

    person = models.ForeignKey(
        "people.Person",
        related_name="tmp_person_identifiers",
        on_delete=models.CASCADE,
    )
    value = models.CharField(
        max_length=800,
        help_text="An identifier e.g a URL or username provided by a 3rd party",
    )
    internal_identifier = models.CharField(
        max_length=800,
        help_text="An optional internal identifier from the 3rd party",
        null=True,
    )
    value_type = models.CharField(
        max_length=100,
        help_text="A label for the type of value e.g. 'Twitter', 'Person blog'",
    )
    extra_data = JSONField(
        help_text="""For storing any additional data against this field.
                     Used by bots, not humans.""",
        null=True,
    )

    objects = PersonIdentifierQuerySet.as_manager()

    class Meta:
        unique_together = (
            ("person", "value"),
            ("person", "internal_identifier", "value_type"),
            # TODO: Remove this.
            # At the moemnt the version history can't deal with more than one
            # value per value_type. This prevents creating duplicates, and
            # therefore means we'll be able to merge and revert people.
            # This constraint should be removed when the version history can
            # support the data model we want
            ("person", "value_type"),
        )
        ordering = ("value_type", "-modified")

    def __str__(self):
        return "{}: {} ({})".format(self.person_id, self.value_type, self.value)

    @property
    def get_value_type_html(self):
        STRING_TO_LABEL = {
            "theyworkforyou": "TheyWorkForYou Profile",
            "facebook_page_url": "Facebook Page",
            "homepage_url": "Homepage",
            "party_ppc_page_url": "Party candidate page",
            "twitter_username": "Twitter",
            "wikipedia_url": "Wikipedia",
            "wikidata_id": "Wikidata",
            "ynmep_id": "YourNextMEP ID",
        }
        if self.value_type in STRING_TO_LABEL:
            return STRING_TO_LABEL[self.value_type]

        text = self.value_type.replace("_", " ")
        text = text.replace(" url", "")

        return text.title().strip()

    @property
    def get_value_html(self):
        url = None
        text = "{}"

        if self.value_type == "twitter_username":
            url = format_html("https://twitter.com/{}", self.value)

        if self.value.startswith("http"):
            url = format_html("{}", self.value)

        if self.value_type == "email":
            url = format_html("mailto:{}", self.value)

        if self.value_type == "wikidata_id":
            url = format_html("https://www.wikidata.org/wiki/{}", self.value)

        if url:
            text = format_html("""<a href="{}" rel="nofollow">{{}}</a>""", url)

        return format_html(text, self.value)


class Person(Timestampable, models.Model):
    """
    A real person, alive or dead
    see schema at http://popoloproject.com/schemas/person.json#
    """

    json_ld_context = "http://popoloproject.com/contexts/person.jsonld"
    json_ld_type = "http://www.w3.org/ns/person#Person"

    name = models.CharField(
        "name", max_length=512, help_text="A person's preferred full name"
    )

    # array of items referencing "http://popoloproject.com/schemas/other_name.json#"
    other_names = GenericRelation(
        "popolo.OtherName", help_text="Alternate or former names"
    )

    family_name = models.CharField(
        "family name",
        max_length=128,
        blank=True,
        help_text="One or more family names",
    )
    given_name = models.CharField(
        "given name",
        max_length=128,
        blank=True,
        help_text="One or more primary given names",
    )
    additional_name = models.CharField(
        "additional name",
        max_length=128,
        blank=True,
        help_text="One or more secondary given names",
    )
    honorific_prefix = models.CharField(
        "honorific prefix",
        max_length=128,
        blank=True,
        help_text="One or more honorifics preceding a person's name",
    )
    honorific_suffix = models.CharField(
        "honorific suffix",
        max_length=128,
        blank=True,
        help_text="One or more honorifics following a person's name",
    )
    patronymic_name = models.CharField(
        "patronymic name",
        max_length=128,
        blank=True,
        help_text="One or more patronymic names",
    )
    sort_name = models.CharField(
        "sort name",
        max_length=128,
        blank=True,
        help_text="A name to use in an lexicographically ordered list",
    )

    gender = models.CharField(
        "gender", max_length=128, blank=True, help_text="A gender"
    )
    birth_date = models.CharField(
        "birth date", max_length=20, blank=True, help_text="A date of birth"
    )
    death_date = models.CharField(
        "death date", max_length=20, blank=True, help_text="A date of death"
    )

    summary = models.CharField(
        "summary",
        max_length=1024,
        blank=True,
        help_text="A one-line account of a person's life",
    )
    biography = models.TextField(
        "biography",
        blank=True,
        help_text="An extended account of a person's life",
    )
    national_identity = models.CharField(
        "national identity",
        max_length=128,
        blank=True,
        null=True,
        help_text="A national identity",
    )

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation(
        "popolo.Source", help_text="URLs to source documents about the person"
    )

    # Former 'extra' fields
    # This field stores JSON data with previous version information
    # (as it did in PopIt).
    versions = models.TextField(blank=True)
    not_standing = models.ManyToManyField(
        "elections.Election", related_name="persons_not_standing_tmp"
    )

    favourite_biscuit = models.CharField(
        "Favourite biscuit 🍪", max_length=255, null=True
    )

    edit_limitations = models.CharField(
        max_length=100,
        null=False,
        blank=True,
        choices=[
            (status.name, status.value) for status in EditLimitationStatuses
        ],
    )

    class Meta:
        verbose_name_plural = "People"

    objects = PersonQuerySet.as_manager()

    @property
    def current_or_future_candidacies(self):
        result = self.memberships.filter(
            models.Q(ballot__election__current=True)
            | models.Q(ballot__election__election_date__gt=timezone.now())
        ).select_related("person", "party", "post")
        return list(result)

    def record_version(self, change_metadata, new_person=False):
        # Needed because of a circular import
        from candidates.models.versions import get_person_as_version_data

        versions = []
        if self.versions:
            versions = json.loads(self.versions)
        new_version = change_metadata.copy()
        new_version["data"] = get_person_as_version_data(
            self, new_person=new_person
        )
        should_insert = True

        if versions and new_version["data"] == versions[0]["data"]:
            # Don't create empty versions
            should_insert = False

        if new_version["information_source"].startswith("After merging person"):
            # Always create a version if this is a merge
            should_insert = True

        if should_insert:
            versions.insert(0, new_version)

        self.versions = json.dumps(versions)

    def get_slug(self):
        return slugify(self.name)

    def wcivf_url(self):
        return "https://whocanivotefor.co.uk/person/{}/{}".format(
            self.pk, self.get_slug()
        )

    @property
    def last_name_guess(self):
        try:
            return self.name.strip().split(" ")[-1]
        except:
            return self.name

    def get_absolute_url(self, request=None):
        path = reverse(
            "person-view",
            kwargs={"person_id": self.pk, "ignored_slug": self.get_slug()},
        )
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def get_edit_url(self, request=None):
        path = reverse("person-update", kwargs={"person_id": self.pk})
        if request is None:
            return path
        return request.build_absolute_uri(path)

    @cached_property
    def get_all_idenfitiers(self):
        return list(self.tmp_person_identifiers.all())

    def get_identifiers_of_type(self, value_type=None):
        id_list = self.get_all_idenfitiers
        if value_type:
            id_list = [i for i in id_list if i.value_type == value_type]
        return id_list

    def get_single_identifier_of_type(self, value_type=None):
        try:
            return self.get_identifiers_of_type(value_type=value_type)[0]
        except IndexError:
            pass

    def get_single_identifier_value(self, value_type):
        identifier = self.get_single_identifier_of_type(value_type)
        if identifier:
            return identifier.value

    @property
    def get_email(self):
        return self.get_single_identifier_value("email")

    @property
    def get_twitter_username(self):
        return self.get_single_identifier_value("twitter_username")

    @property
    def get_facebook_personal_url(self):
        return self.get_single_identifier_value("facebook_personal_url")

    def invalidate_identifier_cache(self):
        """
        Django can store a prefetch cache on a model, meaning
        that `dest_person.tmp_person_identifiers.all()`
        wont return the newly moved IDs. To save confusion
        in downstream code, invalidate the cache after moving.
        Do the same for the `get_all_identifiers` cache
        """
        attrs = ["_prefetched_objects_cache", "get_all_idenfitiers"]

        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    @property
    def last_candidacy(self):
        ordered_candidacies = Membership.objects.filter(
            person=self, ballot__election__isnull=False
        ).order_by(
            "ballot__election__current", "ballot__election__election_date"
        )
        return ordered_candidacies.last()

    def last_party(self):
        last_candidacy = self.last_candidacy
        if last_candidacy is None:
            return None
        return last_candidacy.party

    def name_with_honorifics(self):
        name_parts = []
        pre = self.honorific_prefix
        post = self.honorific_suffix
        if pre:
            name_parts.append(pre)
        name_parts.append(self.name)
        if post:
            name_parts.append(post)
        return " ".join(name_parts)

    @property
    def dob_as_approximate_date(self):
        from people.helpers import parse_approximate_date

        return parse_approximate_date(self.birth_date)

    def dob_as_date(self):
        approx = self.dob_as_approximate_date
        return date(approx.year, approx.month, approx.day)

    @property
    def dod_as_approximate_date(self):
        from people.helpers import parse_approximate_date

        return parse_approximate_date(self.death_date)

    def dod_as_date(self):
        approx = self.dod_as_approximate_date
        return date(approx.year, approx.month, approx.day)

    @property
    def age(self):
        """Return a string representing the person's age"""

        dob = self.dob_as_approximate_date
        if not dob:
            return None
        until = date.today()
        if self.death_date:
            until = self.dod_as_approximate_date
        approx_age = until.year - dob.year
        if dob.month == 0 and dob.day == 0:
            min_age = approx_age - 1
            max_age = approx_age
        elif dob.day == 0:
            min_age = approx_age - 1
            max_age = approx_age
            if until.month < dob.month:
                max_age = min_age
            elif until.month > dob.month:
                min_age = max_age
        else:
            # There's a complete date:
            dob_as_date = self.dob_as_date()
            try:
                today_in_birth_year = date(dob.year, until.month, until.day)
            except ValueError:
                # It must have been February 29th
                today_in_birth_year = date(dob.year, 3, 1)
            if today_in_birth_year > dob_as_date:
                min_age = max_age = until.year - dob.year
            else:
                min_age = max_age = (until.year - dob.year) - 1
        if min_age == max_age:
            # We know their exact age:
            return str(min_age)
        return "{min_age} or {max_age}".format(min_age=min_age, max_age=max_age)

    """
    Return the elected state for a person in an election.
    Takes the election object as an arg.
    Returns True if they were elected, False if not and None if
    the results have not been set.
    This assumes that someone can only be elected in a single
    post in any election.
    """

    def get_elected(self, election):
        return self.memberships.filter(
            ballot__election=election, elected=True
        ).exists()

    @property
    def version_diffs(self):
        versions = self.versions
        if not versions:
            versions = "[]"
        return get_version_diffs(json.loads(versions))

    def diff_for_version(self, version_id, inline_style=False):
        versions = self.versions or []
        all_version_diffs = get_version_diffs(json.loads(versions))
        right_version_diff = None
        for version_diff in all_version_diffs:
            if version_diff["version_id"] == version_id:
                right_version_diff = version_diff
                break
        if not right_version_diff:
            msg = "Couldn't find version {0} for person with ID {1}"
            raise VersionNotFound(msg.format(version_id, self.id))
        template = loader.get_template("candidates/_diffs_against_parents.html")
        rendered = template.render(
            {
                "diffs_against_all_parents": right_version_diff["diffs"],
                "inline_style": inline_style,
            }
        )
        from people.helpers import squash_whitespace

        return squash_whitespace("<dl>{}</dl>".format(rendered))

    def update_complex_field(self, location, new_value):
        existing_info_types = [location.info_type]
        if location.old_info_type:
            existing_info_types.append(location.old_info_type)
        related_manager = getattr(self, location.popolo_array)
        # Remove the old entries of that type:
        kwargs = {(location.info_type_key + "__in"): existing_info_types}
        related_manager.filter(**kwargs).delete()
        if new_value:
            kwargs = {
                location.info_type_key: location.info_type,
                location.info_value_key: new_value,
            }
            related_manager.create(**kwargs)

    def get_initial_form_data(self):
        initial_data = {}
        for field in settings.SIMPLE_POPOLO_FIELDS:
            initial_data[field.name] = getattr(self, field.name)
        initial_data["favourite_biscuit"] = self.favourite_biscuit

        not_standing_elections = list(self.not_standing.all())
        from elections.models import Election

        for election_data in (
            Election.objects.future()
            .filter(ballot__membership__person=self)
            .by_date()
        ):
            constituency_key = "constituency_" + election_data.slug
            standing_key = "standing_" + election_data.slug
            try:
                candidacy = Membership.objects.get(
                    ballot__election=election_data, person=self
                )
            except Membership.DoesNotExist:
                candidacy = None
            if election_data in not_standing_elections:
                initial_data[standing_key] = "not-standing"
            elif candidacy:
                initial_data[standing_key] = "standing"
                post_id = candidacy.ballot.post.slug
                initial_data[constituency_key] = post_id
                from candidates.models import PartySet

                party_set = PartySet.objects.get(post=candidacy.ballot.post)
                party = candidacy.party
                party_key = (
                    "party_" + party_set.slug.upper() + "_" + election_data.slug
                )
                initial_data[party_key] = party.ec_id
                position = candidacy.party_list_position
                position_key = (
                    "party_list_position_"
                    + party_set.slug.upper()
                    + "_"
                    + election_data.slug
                )
                if position:
                    initial_data[position_key] = position
            else:
                initial_data[standing_key] = "not-sure"
                initial_data[constituency_key] = ""
        return initial_data

    def update_from_form(self, form):
        from people.helpers import update_person_from_form

        update_person_from_form(self, form)

    @classmethod
    def create_from_form(cls, form):
        from people.helpers import update_person_from_form

        person = Person.objects.create(name=form.cleaned_data["name"])

        update_person_from_form(person, form)
        return person

    def dict_for_csv(self, base_url=None):
        elected_for_csv = ""
        image_copyright = ""
        image_uploading_user = ""
        image_uploading_user_notes = ""
        proxy_image_url_template = ""

        primary_image = None
        for image in self.images.all():
            if image.is_primary:
                primary_image = image
        primary_image_url = None
        if primary_image:
            primary_image_url = urljoin(base_url, primary_image.image.url)
            if settings.IMAGE_PROXY_URL and base_url:
                encoded_url = quote_plus(primary_image_url)
                proxy_image_url_template = (
                    settings.IMAGE_PROXY_URL
                    + encoded_url
                    + "/{height}/{width}.{extension}"
                )

            try:
                image_copyright = primary_image.copyright
                user = primary_image.uploading_user
                if user is not None:
                    image_uploading_user = primary_image.uploading_user.username
                image_uploading_user_notes = primary_image.user_notes
            except ObjectDoesNotExist:
                pass

        twitter_id = self.get_single_identifier_of_type("twitter_username")
        if twitter_id:
            twitter_user_id = twitter_id.internal_identifier
            twitter_user_name = twitter_id.value
        else:
            twitter_user_name = twitter_user_id = ""

        theyworkforyou_url = ""
        parlparse_id = ""
        twfy_id = self.get_single_identifier_of_type("theyworkforyou")
        if twfy_id:
            parlparse_id = twfy_id.internal_identifier
            theyworkforyou_url = twfy_id.value

        row = {
            "id": self.id,
            "name": self.name,
            "honorific_prefix": self.honorific_prefix,
            "honorific_suffix": self.honorific_suffix,
            "gender": self.gender,
            "birth_date": self.birth_date,
            "email": self.get_email,
            "twitter_username": twitter_user_name,
            "twitter_user_id": twitter_user_id,
            "facebook_page_url": self.get_single_identifier_value(
                "facebook_page_url"
            ),
            "favourite_biscuits": self.favourite_biscuit or "",
            "linkedin_url": self.get_single_identifier_value("linkedin_url"),
            "party_ppc_page_url": self.get_single_identifier_value(
                "party_ppc_page_url"
            ),
            "facebook_personal_url": self.get_single_identifier_value(
                "facebook_personal_url"
            ),
            "homepage_url": self.get_single_identifier_value("homepage_url"),
            "wikipedia_url": self.get_single_identifier_value("wikipedia_url"),
            "wikidata_id": self.get_single_identifier_value("wikidata_id"),
            "theyworkforyou_url": theyworkforyou_url,
            "parlparse_id": parlparse_id,
            "image_url": primary_image_url,
            "proxy_image_url_template": proxy_image_url_template,
            "image_copyright": image_copyright,
            "image_uploading_user": image_uploading_user,
            "image_uploading_user_notes": image_uploading_user_notes,
            "blog_url": self.get_single_identifier_value("blog_url"),
            "instagram_url": self.get_single_identifier_value("instagram_url"),
            "youtube_profile": self.get_single_identifier_value(
                "youtube_profile"
            ),
        }
        return row

    @property
    def primary_image_model(self):
        images = self.images.filter(is_primary=True)
        if images.exists():
            return images.first()

    @property
    def primary_image(self):
        image = self.primary_image_model
        if image:
            return image.image

    def get_display_image_url(self):
        """
        Return either the person's primary image or blank outline of a person
        """
        if self.primary_image:
            try:
                return get_thumbnail(self.primary_image.file, "x64").url
            except FileNotFoundError:
                pass

        return static("candidates/img/blank-person.png")

    def __str__(self):
        return self.name

    def user_can_edit(self, user):
        """
        User is ignored at the moment, but passed for future evaluation
        of edit permissions based on the user/group


        :type user: django.contrib.auth.models.User
        """
        return (
            self.edit_limitations != EditLimitationStatuses.EDITS_PREVENTED.name
        )

    @property
    def liable_to_vandalism(self):
        return self.edit_limitations == EditLimitationStatuses.NEEDS_REVIEW.name

    def current_elections_standing_down(self):
        """
        Returns a list of elections where:

        1. They were elected in the last ballot for this post
        2. They are marked as not_standing in the election for the next
           ballot for that post
        """
        standing_down_elections = []
        elected_memberships = self.memberships.filter(elected=True)
        for membership in elected_memberships:
            elected_ballot = membership.ballot
            next_ballot = Ballot.objects.filter(
                election__current=True
            ).get_next_ballot_for_post(elected_ballot)

            if next_ballot:
                if self.not_standing.filter(slug=next_ballot.election.slug):
                    standing_down_elections.append(next_ballot.election)
        return standing_down_elections


class GenderGuess(models.Model):
    """
    In many, many ways, this is a really bad idea.

    It's here because we often get asked about the gender of candidates as a
    whole at elections. The default in this project (and elsewhere, hopefully)
    is that we don't proscribe gender, or suggest that it's a binary choice.

    _However_, it is useful,sometimes, to ask for approximate balance of binary
    gender.

    This model should never be used to assert the gender of an individual,
    rather it should *only* be used in aggregate to infer rough balance,
    and even then reports and so on should be couched in language that
    explains this position.
    """

    gender = models.CharField(max_length=1)
    person = models.OneToOneField(
        on_delete=models.deletion.CASCADE,
        related_name="gender_guess",
        to="people.Person",
    )
