try:
    from django.contrib.contenttypes.fields import GenericRelation
except ImportError:
    # This fallback import is the version that was deprecated in
    # Django 1.7 and is removed in 1.9:
    from django.contrib.contenttypes.generic import GenericRelation

try:
    # PassTrhroughManager was removed in django-model-utils 2.4
    # see issue #22 at https://github.com/openpolis/django-popolo/issues/22
    from model_utils.managers import PassThroughManager
except ImportError:
    pass

from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from model_utils import Choices
from slugify import slugify

from ynr_refactoring.settings import PersonIdentifierFields

from .behaviors.models import Dateframeable, GenericRelatable, Timestampable
from .querysets import (
    ContactDetailQuerySet,
    MembershipQuerySet,
    OrganizationQuerySet,
    OtherNameQuerySet,
    PostQuerySet,
)


class VersionNotFound(Exception):
    pass


class NotStandingValidationError(ValueError):
    pass


class Organization(Dateframeable, Timestampable, models.Model):
    """
    A group with a common purpose or reason for existence that goes beyond the
    set of people belonging to it see schema at
    http://popoloproject.com/schemas/organization.json#
    """

    name = models.CharField(
        "name",
        max_length=512,
        help_text="A primary name, e.g. a legally recognized name",
    )
    summary = models.CharField(
        "summary",
        max_length=1024,
        blank=True,
        help_text="A one-line description of an organization",
    )
    description = models.TextField(
        "biography",
        blank=True,
        help_text="An extended description of an organization",
    )

    # array of items referencing "http://popoloproject.com/schemas/other_name.json#"
    other_names = GenericRelation(
        "OtherName", help_text="Alternate or former names"
    )

    # array of items referencing "http://popoloproject.com/schemas/identifier.json#"
    identifiers = GenericRelation("Identifier", help_text="Issued identifiers")
    classification = models.CharField(
        "classification",
        max_length=512,
        blank=True,
        help_text="An organization category, e.g. committee",
    )

    # reference to "http://popoloproject.com/schemas/organization.json#"
    parent = models.ForeignKey(
        "Organization",
        blank=True,
        null=True,
        related_name="children",
        help_text="The organization that contains this organization",
        on_delete=models.CASCADE,
    )

    founding_date = models.CharField(
        "founding date",
        max_length=10,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex="^[0-9]{4}(-[0-9]{2}){0,2}$",
                message="founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$",
                code="invalid_founding_date",
            )
        ],
        help_text="A date of founding",
    )
    dissolution_date = models.CharField(
        "dissolution date",
        max_length=10,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex="^[0-9]{4}(-[0-9]{2}){0,2}$",
                message="dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$",
                code="invalid_dissolution_date",
            )
        ],
        help_text="A date of dissolution",
    )
    image = models.URLField(
        "image",
        blank=True,
        null=True,
        help_text="A URL of an image, to identify the organization visually",
    )

    # array of items referencing "http://popoloproject.com/schemas/contact_detail.json#"
    contact_details = GenericRelation(
        "ContactDetail", help_text="Means of contacting the organization"
    )

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation(
        "Source", help_text="URLs to source documents about the organization"
    )

    # Copied from OrganizationExtra
    slug = models.CharField(max_length=256, blank=True, unique=True)
    register = models.CharField(blank=True, max_length=512)

    def ec_id(self):
        if self.classification != "Party":
            raise ValueError("'{}' isn't a Party".format(str(self)))
        try:
            party_id = self.identifiers.filter(
                scheme="electoral-commission"
            ).first()
            return party_id.identifier
        except:
            return "ynmp-party:2"

    try:
        # PassTrhroughManager was removed in django-model-utils 2.4, see issue #22
        objects = PassThroughManager.for_queryset_class(OrganizationQuerySet)()
    except:
        objects = OrganizationQuerySet.as_manager()

    def add_member(self, person):
        m = Membership(organization=self, person=person)
        m.save()

    def add_members(self, persons):
        for p in persons:
            self.add_member(p)

    def add_post(self, **kwargs):
        kwargs["slug"] = slugify(kwargs["label"])
        p = Post(organization=self, **kwargs)
        p.save()

    def add_posts(self, posts):
        for p in posts:
            self.add_post(**p)

    def __str__(self):
        return self.name


class Post(Dateframeable, Timestampable, models.Model):
    """
    A position that exists independent of the person holding it
    see schema at http://popoloproject.com/schemas/json#
    """

    label = models.CharField(
        "label",
        max_length=512,
        blank=True,
        help_text="A label describing the post",
    )
    other_label = models.CharField(
        "other label",
        max_length=512,
        blank=True,
        null=True,
        help_text="An alternate label, such as an abbreviation",
    )

    role = models.CharField(
        "role",
        max_length=512,
        blank=True,
        help_text="The function that the holder of the post fulfills",
    )

    # reference to "http://popoloproject.com/schemas/organization.json#"
    organization = models.ForeignKey(
        "Organization",
        related_name="posts",
        help_text="The organization in which the post is held",
        on_delete=models.CASCADE,
    )

    # array of items referencing "http://popoloproject.com/schemas/contact_detail.json#"
    contact_details = GenericRelation(
        "ContactDetail", help_text="Means of contacting the holder of the post"
    )

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation(
        "Source", help_text="URLs to source documents about the post"
    )

    # PostExtra fields
    slug = models.CharField(max_length=256, blank=True)

    elections = models.ManyToManyField(
        "elections.Election", related_name="posts", through="candidates.Ballot"
    )
    group = models.CharField(max_length=1024, blank=True)
    party_set = models.ForeignKey(
        "candidates.PartySet", blank=True, null=True, on_delete=models.CASCADE
    )

    @property
    def short_label(self):
        from candidates.election_specific import shorten_post_label

        return shorten_post_label(self.label)

    try:
        # PassTrhroughManager was removed in django-model-utils 2.4, see issue #22
        objects = PassThroughManager.for_queryset_class(PostQuerySet)()
    except:
        objects = PostQuerySet.as_manager()

    def __str__(self):
        return self.label

    class Meta:
        unique_together = ("slug", "organization")


class Membership(Dateframeable, Timestampable, models.Model):
    """
    A relationship between a person and an organization
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(
        "label",
        max_length=512,
        blank=True,
        help_text="A label describing the membership",
    )
    role = models.CharField(
        "role",
        max_length=512,
        blank=True,
        help_text="The role that the person fulfills in the organization",
    )

    # reference to "http://popoloproject.com/schemas/person.json#"
    person = models.ForeignKey(
        "people.Person",
        to_field="id",
        related_name="memberships",
        help_text="The person who is a party to the relationship",
        on_delete=models.CASCADE,
    )

    party = models.ForeignKey(
        "parties.Party",
        null=True,
        help_text="The political party for this membership",
        on_delete=models.PROTECT,
    )

    # reference to "http://popoloproject.com/schemas/post.json#"
    post = models.ForeignKey(
        "Post",
        blank=True,
        null=True,
        related_name="memberships",
        help_text="The post held by the person in the organization through this membership",
        on_delete=models.CASCADE,
    )

    # array of items referencing "http://popoloproject.com/schemas/contact_detail.json#"
    contact_details = GenericRelation(
        "ContactDetail",
        help_text="Means of contacting the member of the organization",
    )

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation(
        "Source", help_text="URLs to source documents about the membership"
    )

    # Moved from MembeshipExtra
    elected = models.NullBooleanField()
    party_list_position = models.PositiveSmallIntegerField(null=True)
    ballot = models.ForeignKey("candidates.Ballot", on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.ballot and getattr(self, "check_for_broken", True):
            if self.ballot.election in self.person.not_standing.all():
                msg = (
                    "Trying to add a Membership with an election "
                    '"{election}", but that\'s in {person} '
                    "({person_id})'s not_standing list."
                )
                raise NotStandingValidationError(
                    msg.format(
                        election=self.ballot.election,
                        person=self.person.name,
                        person_id=self.person.id,
                    )
                )
        super().save(*args, **kwargs)

    try:
        # PassTrhroughManager was removed in django-model-utils 2.4, see issue #22
        objects = PassThroughManager.for_queryset_class(MembershipQuerySet)()
    except:
        objects = MembershipQuerySet.as_manager()

    def __str__(self):
        return self.label

    class Meta:
        unique_together = ("person", "ballot")
        ordering = ("party__name", "party_list_position", "person__name")

    def dict_for_csv(self, redirects=None):
        identifier_dict = {}
        id_values = [f.value for f in PersonIdentifierFields]
        for identifier in self.person.tmp_person_identifiers.all():
            if identifier not in id_values:
                continue
            identifier_dict[identifier.value_type] = identifier.value

        membership_dict = {
            "election": self.ballot.election.slug,
            "election_date": self.ballot.election.election_date,
            "election_current": self.ballot.election.current,
            "party_name": self.party.name,
            "party_id": self.party.legacy_slug,
            "party_ec_id": self.party.ec_id,
            "party_list_position": self.party_list_position,
            "party_lists_in_use": self.ballot.election.party_lists_in_use,
            "mapit_url": "",
            "gss_code": "",
            "post_id": self.ballot.post.slug,
            "post_label": self.ballot.post.short_label,
            "cancelled_poll": self.ballot.cancelled,
        }

        if redirects and redirects.get(self.person_id):
            membership_dict["old_person_ids"] = ";".join(
                [str(i) for i in redirects.get(self.person_id)]
            )
        else:
            membership_dict["old_person_ids"] = ""

        if self.elected:
            membership_dict["elected"] = self.elected
        else:
            membership_dict["elected"] = ""

        membership_dict.update(identifier_dict)
        membership_dict.update(self.person.dict_for_csv())
        return membership_dict


class ContactDetail(
    Timestampable, Dateframeable, GenericRelatable, models.Model
):
    """
    A means of contacting an entity
    see schema at http://popoloproject.com/schemas/contact-detail.json#
    """

    CONTACT_TYPES = Choices(
        ("ADDRESS", "address", "Address"),
        ("EMAIL", "email", "Email"),
        ("URL", "url", "Url"),
        ("MAIL", "mail", "Snail mail"),
        ("TWITTER", "twitter", "Twitter"),
        ("FACEBOOK", "facebook", "Facebook"),
        ("PHONE", "phone", "Telephone"),
        ("MOBILE", "mobile", "Mobile"),
        ("TEXT", "text", "Text"),
        ("VOICE", "voice", "Voice"),
        ("FAX", "fax", "Fax"),
        ("CELL", "cell", "Cell"),
        ("VIDEO", "video", "Video"),
        ("PAGER", "pager", "Pager"),
        ("TEXTPHONE", "textphone", "Textphone"),
    )

    label = models.CharField(
        "label",
        max_length=512,
        blank=True,
        help_text="A human-readable label for the contact detail",
    )
    contact_type = models.CharField(
        "type",
        max_length=12,
        choices=CONTACT_TYPES,
        help_text="A type of medium, e.g. 'fax' or 'email'",
    )
    value = models.CharField(
        "value",
        max_length=512,
        help_text="A value, e.g. a phone number or email address",
    )
    note = models.CharField(
        "note",
        max_length=512,
        blank=True,
        help_text="A note, e.g. for grouping contact details by physical location",
    )

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    sources = GenericRelation(
        "Source", help_text="URLs to source documents about the contact detail"
    )

    try:
        # PassTrhroughManager was removed in django-model-utils 2.4, see issue #22
        objects = PassThroughManager.for_queryset_class(ContactDetailQuerySet)()
    except:
        objects = ContactDetailQuerySet.as_manager()

    def __str__(self):
        return u"{} - {}".format(self.value, self.contact_type)


class OtherName(Dateframeable, GenericRelatable, models.Model):
    """
    An alternate or former name
    see schema at http://popoloproject.com/schemas/name-component.json#
    """

    name = models.CharField(
        "name", max_length=512, help_text="An alternate or former name"
    )
    note = models.CharField(
        "note",
        max_length=1024,
        blank=True,
        help_text="A note, e.g. 'Birth name'",
    )

    try:
        # PassTrhroughManager was removed in django-model-utils 2.4, see issue #22
        objects = PassThroughManager.for_queryset_class(OtherNameQuerySet)()
    except:
        objects = OtherNameQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "object_id", "content_type")


class Identifier(GenericRelatable, models.Model):
    """
    An issued identifier
    see schema at http://popoloproject.com/schemas/identifier.json#
    """

    identifier = models.CharField(
        "identifier",
        max_length=512,
        help_text="An issued identifier, e.g. a DUNS number",
    )
    scheme = models.CharField(
        "scheme",
        max_length=128,
        blank=True,
        help_text="An identifier scheme, e.g. DUNS",
    )

    def __str__(self):
        return "{}: {}".format(self.scheme, self.identifier)


class Source(GenericRelatable, models.Model):
    """
    A URL for referring to sources of information
    see schema at http://popoloproject.com/schemas/link.json#
    """

    url = models.URLField("url", help_text="A URL")
    note = models.CharField(
        "note",
        max_length=512,
        blank=True,
        help_text="A note, e.g. 'Parliament website'",
    )

    def __str__(self):
        return self.url


class Language(models.Model):
    """
    Maps languages, with names and 2-char iso 639-1 codes.
    Taken from http://dbpedia.org, using a sparql query
    """

    dbpedia_resource = models.CharField(
        max_length=255, help_text="DbPedia URI of the resource", unique=True
    )
    iso639_1_code = models.CharField(max_length=2)
    name = models.CharField(
        max_length=128, help_text="English name of the language"
    )

    def __str__(self):
        return u"{} ({})".format(self.name, self.iso639_1_code)


##
## signals
##

## copy founding and dissolution dates into start and end dates,
## so that Organization can extend the abstract Dateframeable behavior
## (it's way easier than dynamic field names)
@receiver(pre_save, sender=Organization)
def copy_organization_date_fields(sender, **kwargs):
    obj = kwargs["instance"]

    if obj.founding_date:
        obj.start_date = obj.founding_date
    if obj.dissolution_date:
        obj.end_date = obj.dissolution_date


## all instances are validated before being saved
# @receiver(pre_save, sender=Person)
@receiver(pre_save, sender=Organization)
@receiver(pre_save, sender=Post)
def validate_date_fields(sender, **kwargs):
    obj = kwargs["instance"]
    obj.full_clean()
