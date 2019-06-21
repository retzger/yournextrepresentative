from django.db import models
from django.db import transaction, connection
from django.contrib.postgres.fields import JSONField

from people.models import PersonIdentifier


class MaterializedModelMixin:
    @classmethod
    @transaction.atomic
    def refresh_view(cls):
        with connection.cursor() as cursor:
            cursor.execute(
                "REFRESH MATERIALIZED VIEW {}".format(cls._meta.db_table)
            )

    @classmethod
    @transaction.atomic
    def recreate_view(cls):
        with connection.cursor() as cursor:
            cursor.execute
            cursor.execute(
                "DROP MATERIALIZED VIEW IF EXISTS {}".format(cls._meta.db_table)
            )
            print(cls.get_view_sql())
            cursor.execute(cls.get_view_sql())


class MaterializedMemberships(MaterializedModelMixin, models.Model):
    class Meta:
        db_table = "materialized_memberships"
        managed = False

    @classmethod
    def get_view_sql(cls):
        """
        The SQL to create a materialized view containing a row per membership
        (candidacy)

        Use crosstab to create a column for each PersonIdentifier value type.

        The values types need to be created dynamically as postgres offers
        no way to use populate the columns from the value types itself.

        :return:
        """

        sql_str = """
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
                person_ids.json_data as identifiers
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
                
                SELECT p.id as person_id, json_ids as json_data 
				FROM people_person p
				JOIN (
					SELECT person_id, json_object_agg(
					src.value_type, src.value
				)::jsonb AS json_ids
				FROM (
	  				SELECT person_id, value_type, value
    				FROM people_personidentifier
					GROUP BY person_id, value_type, value
				) src
	
			   GROUP BY person_id
			   ) src_json
			   ON p.id = src_json.person_id
                
                
                
            )
            AS person_ids
            ON person_ids.person_id=person.id
            ORDER BY mem.person_id
        """

        return sql_str.format(view_name=cls._meta.db_table)

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

    identifiers = JSONField()
