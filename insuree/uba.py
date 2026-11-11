"""
The ENROLMENT credential on the insuree module: an enrolment officer holds it on the
villages they work in, and the rights of their role's UBA bag are granted there only.

Two questions, kept apart as in `core/docs/uba.md`:

- *may the user open a query at all ?* `can_query`: the right held globally, or held in
  the UBA bag together with an ENROLMENT link - the rows are then narrowed to the linked
  villages by the model `get_queryset`;
- *may the user write on that family / insuree ?* `check_enrolment_perms`: the right
  held globally, or held in the UBA bag with an ENROLMENT link on the village the row
  sits in. A write touching two villages (a family moved, an insuree changing family)
  needs the credential on both.
"""
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from core.uba_filters import has_perms_somewhere
from core.apps import ENROLMENT_UBA_LINK_TYPE, VILLAGE_MODEL


def can_query(user, perms):
    return has_perms_somewhere(user, perms, ENROLMENT_UBA_LINK_TYPE)


def has_enrolment_perms_somewhere(user, perms):
    """
    The gate of a batch write, before its rows are looked at: the rights held globally
    or in the UBA bag with an ENROLMENT link. Each row is then checked on its village.
    """
    return can_query(user, perms)


def village_access_requirements(village):
    """The business map demanding the ENROLMENT credential on `village`."""
    return [VILLAGE_MODEL, village.uuid, ENROLMENT_UBA_LINK_TYPE]


def village_in_scope(user, village):
    """
    Is `village` inside the districts `user` is assigned to ? The same rule as the read
    side (`Family.get_queryset`): a right, global or UBA, never reaches a row outside the
    user's districts. An unknown village (None) is not located, so not refused here.
    """
    if village is None:
        return True
    from django.conf import settings
    from location.apps import LocationConfig
    from location.models import Location
    if not settings.ROW_SECURITY or LocationConfig.no_location_check:
        return True
    user = Location.scoping_user(user)
    if user is None or getattr(user, "is_anonymous", True):
        return False
    from location.models import is_location_unscoped
    if is_location_unscoped(user):
        return True
    village_id = getattr(village, "id", village)
    return Location.objects.filter(id=village_id).filter(
        *Location.filter_location(user, paths=("parent__parent",), loc_types=['D'])
    ).exists()


def has_enrolment_perms(user, perms, villages):
    """
    Are `perms` granted on every village of `villages` ? Every known village must first
    sit inside the user's districts (row security, whatever bag the right comes from).
    Then the global bag answers alone; otherwise each village needs the rights in the
    UBA bag and an ENROLMENT link on it. A write whose village is unknown (None) can
    only be granted by the global bag.
    """
    villages = list(villages)
    if not all(village_in_scope(user, village) for village in villages):
        return False
    if user.has_perms(perms):
        return True
    if not villages or any(village is None for village in villages):
        return False
    return all(
        user.has_perms(perms, access_requirements=village_access_requirements(village))
        for village in {village.id: village for village in villages}.values()
    )


def check_enrolment_perms(user, perms, *villages):
    if not has_enrolment_perms(user, perms, villages):
        raise PermissionDenied(_("unauthorized"))


def family_village(family):
    return family.location if family is not None else None


def insuree_village(insuree):
    """Where an insuree is enrolled: their family's village, their own when they have none."""
    if insuree is None:
        return None
    if insuree.family_id:
        return insuree.family.location
    return insuree.current_village
