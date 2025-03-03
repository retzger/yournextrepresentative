from django.conf import settings

from auth_helpers.views import user_in_group

TRUSTED_TO_MERGE_GROUP_NAME = "Trusted To Merge"
TRUSTED_TO_LOCK_GROUP_NAME = "Trusted To Lock"
TRUSTED_TO_RENAME_GROUP_NAME = "Trusted To Rename"
RESULT_RECORDERS_GROUP_NAME = "Result Recorders"


class NameChangeDisallowedException(Exception):
    pass


class ChangeToLockedConstituencyDisallowedException(Exception):
    pass


def is_post_locked(post, election):
    return post.ballot_set.filter(
        election=election, candidates_locked=True
    ).exists()


def get_constituency_lock_from_person_data(
    user, api, election, person_popit_data
):
    """Return whether the constituency is locked and whether this user can edit"""

    standing_in = person_popit_data.get("standing_in", {}) or {}
    standing_in_election = standing_in.get(election, {}) or {}
    return get_constituency_lock(user, api, standing_in_election.get("post_id"))


def get_constituency_lock(user, post, election):
    """
    Return whether the constituency is locked and whether this user can edit

    You should make sure that 'extra' is populated on the post that's
    passed in to avoid an extra query.

    """

    if post is None:
        return False, True
    ballot = election.ballot_set.get(post=post)
    # Use the cached version because it'll be faster than going to
    # PopIt, even if it brings in embeds that we don't need:
    edits_allowed = ballot.user_can_edit_membership(user)
    return ballot.candidates_locked, edits_allowed


def check_creation_allowed(user, new_candidacies):
    for candidacy in new_candidacies:
        post = candidacy.ballot.post
        election = candidacy.ballot.election
        dummy, edits_allowed = get_constituency_lock(user, post, election)
        if not edits_allowed:
            raise ChangeToLockedConstituencyDisallowedException(
                "The candidates for this ballot are locked now"
            )


def check_update_allowed(
    user, old_name, old_candidacies, new_name, new_candidacies
):
    # Check whether an unauthorized user has tried to rename someone
    # while RESTRICT_RENAMES is set:
    if settings.RESTRICT_RENAMES:
        allowed_by_group = user_in_group(user, TRUSTED_TO_RENAME_GROUP_NAME)
        name_the_same = old_name == new_name
        if not (allowed_by_group or name_the_same):
            message = "Name change from '{0}' to '{1}' by user {2} disallowed"
            raise NameChangeDisallowedException(
                message.format(old_name, new_name, user.username)
            )
    # Check that none of the posts that the person's leaving or
    # joining were locked:
    old_posts = {(c.post, c.ballot.election) for c in old_candidacies}
    new_posts = {(c.post, c.ballot.election) for c in new_candidacies}
    for post, election in old_posts ^ new_posts:
        dummy, edits_allowed = get_constituency_lock(user, post, election)
        if not edits_allowed:
            raise ChangeToLockedConstituencyDisallowedException(
                (
                    "That update isn't allowed because candidates for a locked "
                    "post ({post_label}) would be changed"
                ).format(post_label=post.label)
            )
    # Now check that they're not changing party in a locked
    # constituency:
    for post, election in old_posts & new_posts:
        old_party = next(c.party for c in old_candidacies if c.post == post)
        new_party = next(c.party for c in new_candidacies if c.post == post)
        dummy, edits_allowed = get_constituency_lock(user, post, election)
        if not edits_allowed and (old_party != new_party):
            raise ChangeToLockedConstituencyDisallowedException(
                (
                    "That update isn't allowed because you can't change the party "
                    "(in this case from {old_party} to {new_party}) for a candidate "
                    "in a locked post ({post_label})"
                ).format(
                    old_party=old_party.name,
                    new_party=new_party.name,
                    post_label=post.label,
                )
            )
