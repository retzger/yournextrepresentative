from django.db import models
from django.db import transaction, connection

from people.models import PersonIdentifier


class PersonIdentifierField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 800
        super().__init__(*args, **kwargs)


class MaterializedModelMixin:
    @transaction.atomic
    def refresh_view(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "REFRESH MATERIALIZED VIEW CONCURRENTLY {}".format(
                    self._meta.db_table
                )
            )

    @transaction.atomic
    def recreate_view(self):
        with connection.cursor() as cursor:
            cursor.execute
            cursor.execute(
                "DROP MATERIALIZED VIEW IF EXISTS {}".format(
                    self._meta.db_table
                )
            )
            print(self.get_view_sql())
            cursor.execute(self.get_view_sql())


class MaterializedMemberships(MaterializedModelMixin, models.Model):
    class Meta:
        db_table = "materialized_memberships"
        managed = False

    def get_view_sql(self):
        """
        The SQL to create a materialized view containing a row per membership
        (candidacy)

        Use crosstab to create a column for each PersonIdentifier value type.

        The values types need to be created dynamically as postgres offers
        no way to use populate the columns from the value types itself.

        :return:
        """

        sql_str = """
            CREATE EXTENSION IF NOT EXISTS tablefunc;
            CREATE MATERIALIZED VIEW {view_name} AS
            SELECT 
                mem.id as id,
                ballots.ballot_paper_id,
                Cast(position('.by.' in ballot_paper_id) as BOOLEAN) as is_by_election,
                ballots.election_name,
                ballots.election_date,
                ballots.post_label as division_name,
                mem.person_id,
                mem.party_list_position,
                person.name,
                parties.ec_id as party_id,
                parties.name as party_name,
                mem.elected,
                {person_identifier_selects}
            FROM popolo_membership as mem
            JOIN people_person person on mem.person_id = person.id
            JOIN (
                SELECT 
                    pee.id as pee,
                    elections.name as election_name,
                    elections.election_date as election_date,
                    posts.label as post_label,
                    pee.*
                FROM candidates_postextraelection as pee
                JOIN elections_election as elections
                ON elections.id = pee.election_id
                JOIN popolo_post posts
                ON pee.post_id = posts.id
            ) as ballots
            ON mem.post_election_id = ballots.pee
            JOIN parties_party as parties
            ON mem.party_id = parties.id
            
            LEFT JOIN (
                SELECT * from crosstab(
                    $$SELECT
                        person_id,
                        value_type::text,
                        value::text 
                        FROM people_personidentifier
                        ORDER BY 1,2$$,
                    $$VALUES 
                        {person_identifier_values}
                    $$
                ) as ids (
                    person_id int,
                    {person_identifier_as_casts}
                )
            )
            AS person_ids
            ON person_ids.person_id=person.id
            ORDER BY mem.person_id
        """

        # Populate the person identifier columns
        # These are declared as fields on the model class using the
        # PersonIdentifierField class
        person_identifier_fields = [
            f.name
            for f in self._meta.fields
            if isinstance(f, PersonIdentifierField)
        ]

        person_identifier_values = ",\n".join(
            ["('{}'::text)".format(pi) for pi in person_identifier_fields]
        )
        person_identifier_as_casts = ",\n".join(
            ["{} text".format(pi) for pi in person_identifier_fields]
        )
        person_identifier_selects = ",\n".join(
            ["person_ids.{}".format(pi) for pi in person_identifier_fields]
        )

        return sql_str.format(
            view_name=self._meta.db_table,
            person_identifier_values=person_identifier_values,
            person_identifier_as_casts=person_identifier_as_casts,
            person_identifier_selects=person_identifier_selects,
        )

    membership = models.OneToOneField(
        "popolo.Membership", db_column="id", primary_key=True
    )
    ballot_paper = models.ForeignKey(
        "candidates.PostExtraElection", to_field="ballot_paper_id"
    )
    is_by_election = models.BooleanField()
    party = models.ForeignKey("parties.Party", to_field="ec_id")
    party_name = models.CharField(max_length=800)
    party_list_position = models.PositiveIntegerField()
    person = models.ForeignKey("people.Person")
    person_name = models.CharField(max_length=800, db_column="name")

    election_name = models.CharField(max_length=800)
    election_date = models.DateField()
    division_name = models.CharField(max_length=800)

    # Define the person identifier fields we want in the view.
    # There is no validation here,so `foo_bar = PersonIdentifierField()` will
    # create a column, and that column will always be blank unless
    # a value_type of `foo_bar` actually exists in the person identifier table
    email = PersonIdentifierField()
    facebook_page_url = PersonIdentifierField()
    facebook_personal_url = PersonIdentifierField()
    homepage_url = PersonIdentifierField()
    linkedin_url = PersonIdentifierField()
    party_ppc_page_url = PersonIdentifierField()
    theyworkforyou = PersonIdentifierField()
    twitter_username = PersonIdentifierField()
    wikidata_id = PersonIdentifierField()
    wikipedia_url = PersonIdentifierField()
    ynmep_id = PersonIdentifierField()
