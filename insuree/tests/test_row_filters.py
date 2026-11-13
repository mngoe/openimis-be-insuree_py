"""get_queryset honours the OP-2029 validity contract (epic OP-3317, phase 1).

Explicit validity values return the expected rows; a caller asking for
nothing gets what it got before the contract existed.
"""

from django.test import TestCase

from core.models.row_filters import Audits, Validity
from core.test_helpers import assert_row_filters, create_test_interactive_user, mark_deleted
from insuree.models import Family, Insuree
from insuree.test_helpers import create_test_insuree


class InsureeRowFiltersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_test_interactive_user(username="insureerowfilters")

    def test_insuree(self):
        live = create_test_insuree()
        deleted = mark_deleted(create_test_insuree())
        assert_row_filters(
            self, Insuree, Insuree.objects.filter(id__in=[live.id, deleted.id]), self.user,
            live.id, deleted.id, default_hides_deleted=False,
        )

    def test_family(self):
        live = create_test_insuree().family
        deleted = mark_deleted(create_test_insuree().family)
        assert_row_filters(
            self, Family, Family.objects.filter(id__in=[live.id, deleted.id]), self.user,
            live.id, deleted.id, default_hides_deleted=False,
        )

    def test_audits_all_returns_the_history(self):
        insuree = create_test_insuree()
        copy_id = insuree.save_history()
        rows = Insuree.objects.filter(chf_id=insuree.chf_id)
        self.assertEqual(
            {insuree.id, copy_id},
            set(Insuree.get_queryset(rows, self.user, validity=Validity.NOW, audits=Audits.ALL)
                .values_list("id", flat=True)),
        )
        self.assertEqual(
            {insuree.id},
            set(Insuree.get_queryset(rows, self.user, validity=Validity.NOW).values_list("id", flat=True)),
        )


class InsureeNullVillageScopeTest(TestCase):
    """Cameroon: an insuree without current village is located by its family
    (ordered fallback), so it no longer leaks to every district."""

    @classmethod
    def setUpTestData(cls):
        from core.test_helpers import create_right_only_user, create_security_tree
        from insuree.apps import InsureeConfig
        cls.tree = create_security_tree("SPIF")
        cls.user = create_right_only_user(
            "spifuser", [int(p) for p in InsureeConfig.gql_query_insurees_perms], [cls.tree.d1.id])
        cls.home = create_test_insuree(
            custom_props={"chf_id": "SPIF0001", "current_village": cls.tree.v1},
            family_custom_props={"location": cls.tree.v1})
        cls.orphan = create_test_insuree(
            custom_props={"chf_id": "SPIF0002", "current_village": cls.tree.v2},
            family_custom_props={"location": cls.tree.v2})
        Insuree.objects.filter(pk=cls.orphan.pk).update(current_village=None)
        cls.homeless_here = create_test_insuree(
            custom_props={"chf_id": "SPIF0003", "current_village": cls.tree.v1},
            family_custom_props={"location": cls.tree.v1})
        Insuree.objects.filter(pk=cls.homeless_here.pk).update(current_village=None)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_family_location_answers_when_the_village_is_null(self):
        visible = set(Insuree.get_queryset(
            Insuree.objects.filter(chf_id__startswith="SPIF"), self.user
        ).values_list("chf_id", flat=True))
        self.assertEqual({"SPIF0001", "SPIF0003"}, visible)

    def test_insuree_policies_follow_the_same_rule(self):
        from insuree.models import InsureePolicy
        sql = str(InsureePolicy.get_queryset(InsureePolicy.objects.all(), self.user).query)
        self.assertIn("IS NULL", sql)
