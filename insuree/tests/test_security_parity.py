"""
Security parity tests for insuree (row scope + API rights) against the openimis-dev-tools
reference (release/26.10). Each test asserts the REFERENCE behaviour: a failure is a gap
in the Cameroon code.

Tags: [REF <reference file>::<test>] ported, [NEW] no reference equivalent.

Fixture: two disjoint branches R1>D1>W1>V1 / R2>D2>W2>V2 (core.test_helpers.create_security_tree).
`user_a` holds the insuree rights in the GLOBAL bag (no UBA) and is assigned district D1 only.
"""
import json

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.test import TestCase, override_settings

from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase
from core.test_helpers import create_security_tree, create_right_only_user, get_test_token, perm_ids
from insuree.apps import InsureeConfig
from insuree.models import Family, Insuree, InsureePolicy
from insuree.test_helpers import create_test_insuree

def _u(*lists):
    """de-duplicated right ids (a role cannot hold the same right twice)"""
    return list(dict.fromkeys(r for lst in lists for r in lst))


def _product(code):
    """product.test_helpers imports program.test_helpers, absent on Cameroon's program dev-csu."""
    from program.models import Program
    from product.models import Product
    program = Program.objects.create(code=code[:10], nameProgram=f"Program {code}")
    return Product.objects.create(
        code=code, name=f"Test product {code}", lump_sum=123.45, max_members=5,
        grace_period_enrolment=1, insurance_period=12, date_from="2019-01-01", date_to="2049-01-01",
        validity_from="2019-01-01", audit_user_id=-1, program=program)


READ_RIGHTS = _u(perm_ids(InsureeConfig.gql_query_insurees_perms), perm_ids(InsureeConfig.gql_query_families_perms))
WRITE_RIGHTS = _u(
    perm_ids(InsureeConfig.gql_mutation_create_insurees_perms),
    perm_ids(InsureeConfig.gql_mutation_update_insurees_perms),
    perm_ids(InsureeConfig.gql_mutation_delete_insurees_perms),
    perm_ids(InsureeConfig.gql_mutation_create_families_perms),
    perm_ids(InsureeConfig.gql_mutation_update_families_perms),
    perm_ids(InsureeConfig.gql_mutation_delete_families_perms),
)


def _build_family(village, chf_head, chf_member):
    head = create_test_insuree(
        with_family=True, is_head=True,
        custom_props={"chf_id": chf_head, "current_village": village},
        family_custom_props={"location": village})
    member = create_test_insuree(
        with_family=False,
        custom_props={"chf_id": chf_member, "family": head.family, "current_village": village})
    return head, member


def _refused(call):
    """A write is refused when it raises PermissionDenied / DoesNotExist or returns errors."""
    try:
        result = call()
    except (PermissionDenied, ObjectDoesNotExist):
        return True
    return bool(result)


def _unauthorized(call):
    """Refused *because of rights* (not a later functional error)."""
    try:
        result = call()
    except PermissionDenied:
        return True
    from django.utils.translation import gettext as _
    text = json.dumps(result or [], default=str).lower()
    return "unauthorized" in text or _("unauthorized").lower() in text


@override_settings(ROW_SECURITY=True)
class InsureeReadScopeTest(TestCase):
    """Model-level row scope (Family/Insuree/InsureePolicy.get_queryset)."""

    @classmethod
    def setUpTestData(cls):
        cls.t = create_security_tree("SPI")
        cls.head_a, cls.member_a = _build_family(cls.t.v1, "SPI00001", "SPI00002")
        cls.head_b, cls.member_b = _build_family(cls.t.v2, "SPI00003", "SPI00004")
        # insuree with NO current village, member of a family located in district 2
        cls.nullv_b = create_test_insuree(
            with_family=False,
            custom_props={"chf_id": "SPI00005", "family": cls.head_b.family, "current_village": cls.t.v2})
        Insuree.objects.filter(id=cls.nullv_b.id).update(current_village=None)
        cls.user_a = create_right_only_user("spiread", READ_RIGHTS, [cls.t.d1.id])

    def setUp(self):
        cache.clear()

    def _chfids(self, model_qs):
        return set(model_qs.values_list("chf_id", flat=True))

    def test_insurees_exclude_other_district(self):
        """[REF insuree/tests/test_officer_row_security.py] insurees of district 2 are invisible."""
        visible = self._chfids(Insuree.get_queryset(Insuree.objects.filter(chf_id__startswith="SPI"), self.user_a))
        self.assertIn("SPI00001", visible)
        self.assertNotIn("SPI00003", visible)
        self.assertNotIn("SPI00004", visible)

    def test_families_exclude_other_district(self):
        """[REF insuree/tests/test_officer_row_security.py] families of district 2 are invisible."""
        ids = set(Family.get_queryset(
            Family.objects.filter(id__in=[self.head_a.family_id, self.head_b.family_id]), self.user_a
        ).values_list("id", flat=True))
        self.assertEqual({self.head_a.family_id}, ids)

    def test_insuree_without_village_in_foreign_family_is_hidden(self):
        """[NEW] an insuree with current_village NULL whose family sits in district 2 must
        stay hidden (Cameroon: `OR current_village__parent__parent IS NULL` leaks it)."""
        visible = self._chfids(Insuree.get_queryset(Insuree.objects.filter(chf_id="SPI00005"), self.user_a))
        self.assertNotIn("SPI00005", visible)

    def test_insuree_policies_exclude_other_district(self):
        """[REF insuree/models.py InsureePolicy.get_queryset] insuree policies follow the insuree scope
        (an insuree with NULL village in district 2 included)."""
        from policy.test_helpers import create_test_policy
        product = _product("SPIPR1")
        create_test_policy(product, self.head_b)
        create_test_policy(product, self.nullv_b)
        visible = set(InsureePolicy.get_queryset(
            InsureePolicy.objects.filter(insuree__chf_id__in=["SPI00003", "SPI00005"]), self.user_a
        ).values_list("insuree__chf_id", flat=True))
        self.assertEqual(set(), visible)


@override_settings(ROW_SECURITY=True)
class InsureeGraphQLScopeTest(openIMISGraphQLTestCase):
    """Resolvers over HTTP with a Bearer token."""

    @classmethod
    def setUpTestData(cls):
        cls.t = create_security_tree("SPJ")
        cls.head_a, cls.member_a = _build_family(cls.t.v1, "SPJ00001", "SPJ00002")
        cls.head_b, cls.member_b = _build_family(cls.t.v2, "SPJ00003", "SPJ00004")
        cls.nullv_b = create_test_insuree(
            with_family=False,
            custom_props={"chf_id": "SPJ00005", "family": cls.head_b.family, "current_village": cls.t.v2})
        Insuree.objects.filter(id=cls.nullv_b.id).update(current_village=None)
        cls.user_a = create_right_only_user(
            "spjread", _u(READ_RIGHTS, perm_ids(InsureeConfig.gql_query_insuree_family_members)), [cls.t.d1.id])
        cls.token = get_test_token(cls.user_a)
        cls.no_right_user = create_right_only_user("spjnoright", [], [cls.t.d1.id])
        cls.no_right_token = get_test_token(cls.no_right_user)

    def setUp(self):
        cache.clear()

    def _q(self, query, token):
        resp = self.query(query, headers={"HTTP_AUTHORIZATION": f"Bearer {token}"})
        return json.loads(resp.content)

    def _insuree_chfids(self, extra=""):
        content = self._q(f'{{ insurees(chfId_Istartswith: "SPJ"{extra}) {{ edges {{ node {{ chfId family {{ uuid }} }} }} }} }}', self.token)
        self.assertNotIn("errors", content, content.get("errors"))
        return {e["node"]["chfId"] for e in content["data"]["insurees"]["edges"]}

    def test_gql_insurees_scoped(self):
        """[REF insuree/tests/test_enquiry_right.py] `insurees` keeps district 2 out."""
        visible = self._insuree_chfids()
        self.assertIn("SPJ00001", visible)
        self.assertFalse({"SPJ00003", "SPJ00004", "SPJ00005"} & visible, visible)

    def test_gql_insurees_ignore_location_stays_scoped(self):
        """[REF insuree/tests/test_enquiry_right.py::ignoreLocation without enquiry right stays scoped]"""
        visible = self._insuree_chfids(", ignoreLocation: true")
        self.assertFalse({"SPJ00003", "SPJ00004", "SPJ00005"} & visible, visible)

    def test_gql_families_scoped(self):
        """[REF insuree/tests/test_officer_row_security.py] `families` keeps district 2 out."""
        content = self._q('{ families { edges { node { uuid headInsuree { chfId } } } } }', self.token)
        self.assertNotIn("errors", content, content.get("errors"))
        uuids = {e["node"]["uuid"] for e in content["data"]["families"]["edges"]}
        self.assertNotIn(str(self.head_b.family.uuid), uuids)

    def test_gql_family_members_of_foreign_family_hidden(self):
        """[REF insuree resolvers go through Family.get_queryset] `familyMembers` of a
        district-2 family returns nothing (or an error), never its members."""
        content = self._q(
            f'{{ familyMembers(familyUuid: "{self.head_b.family.uuid}") {{ edges {{ node {{ chfId }} }} }} }}',
            self.token)
        edges = ((content.get("data") or {}).get("familyMembers") or {}).get("edges") or []
        self.assertEqual([], [e["node"]["chfId"] for e in edges])

    def test_gql_insurees_without_right_denied(self):
        """[REF insuree/tests/test_rights_insuree.py] no right -> error, no data."""
        content = self._q('{ insurees { edges { node { chfId } } } }', self.no_right_token)
        self.assertIn("errors", content)

    def test_gql_insurees_anonymous_denied(self):
        """[REF core/tests/test_mutation_authentication.py] anonymous -> error, no data."""
        resp = self.query('{ insurees { edges { node { chfId } } } }')
        content = json.loads(resp.content)
        self.assertTrue("errors" in content or resp.status_code in (401, 403))

    def test_gql_insuree_officers_refuses_anonymous(self):
        """[DECISION 2026-11-10] no dedicated officers right (covered by UBA / location
        scope), but anonymous callers are refused."""
        resp = self.query('{ insureeOfficers { edges { node { code } } } }')
        content = json.loads(resp.content)
        edges = ((content.get("data") or {}).get("insureeOfficers") or {}).get("edges") or []
        self.assertTrue("errors" in content or resp.status_code in (401, 403) or not edges, content)


@override_settings(ROW_SECURITY=True)
class InsureeWriteScopeTest(TestCase):
    """[REF insuree/tests/test_insuree_write_row_security.py] writes stay in the user's
    districts for a user holding the rights in the GLOBAL bag."""

    @classmethod
    def setUpTestData(cls):
        cls.t = create_security_tree("SPK")
        cls.head_a, cls.member_a = _build_family(cls.t.v1, "SPK00001", "SPK00002")
        cls.head_b, cls.member_b = _build_family(cls.t.v2, "SPK00003", "SPK00004")
        cls.user_a = create_right_only_user("spkwrite", _u(READ_RIGHTS, WRITE_RIGHTS), [cls.t.d1.id])

    def setUp(self):
        cache.clear()

    def _family_valid(self, family_id):
        return Family.objects.filter(id=family_id, validity_to__isnull=True).exists()

    def test_delete_family_refuses_foreign_family(self):
        """[REF test_insuree_write_row_security.py::test_delete_family_refuses_foreign_family]"""
        from insuree.gql_mutations import DeleteFamiliesMutation
        fid = self.head_b.family_id
        refused = _refused(lambda: DeleteFamiliesMutation.async_mutate(
            self.user_a, uuids=[self.head_b.family.uuid], delete_members=False))
        self.assertTrue(refused and self._family_valid(fid), "family of district 2 deleted")

    def test_delete_insuree_refuses_foreign_insuree(self):
        """[REF test_insuree_write_row_security.py::test_delete_insuree_refuses_foreign_insuree]"""
        from insuree.gql_mutations import DeleteInsureesMutation
        _refused(lambda: DeleteInsureesMutation.async_mutate(self.user_a, uuids=[self.member_b.uuid]))
        self.assertIsNone(Insuree.objects.get(id=self.member_b.id).validity_to,
                          "insuree of district 2 deleted")

    def test_delete_own_insuree_allowed(self):
        """[REF test_insuree_write_row_security.py::test_delete_own_insuree] (control)"""
        from insuree.gql_mutations import DeleteInsureesMutation
        errors = DeleteInsureesMutation.async_mutate(self.user_a, uuids=[self.member_a.uuid])
        self.assertFalse(errors)
        self.assertIsNotNone(Insuree.objects.get(id=self.member_a.id).validity_to)

    def test_set_head_refuses_foreign_family(self):
        """[REF test_insuree_write_row_security.py::test_set_head_refuses_foreign_family]"""
        from insuree.gql_mutations import SetFamilyHeadMutation
        _refused(lambda: SetFamilyHeadMutation.async_mutate(
            self.user_a, uuid=self.head_b.family.uuid, insuree_uuid=self.member_b.uuid))
        self.assertEqual(self.head_b.id, Family.objects.get(id=self.head_b.family_id).head_insuree_id,
                         "head of a district-2 family changed")

    def test_change_family_refuses_foreign_family(self):
        """[REF test_insuree_write_row_security.py::test_change_family_refuses_foreign_family]"""
        from insuree.gql_mutations import ChangeInsureeFamilyMutation
        _refused(lambda: ChangeInsureeFamilyMutation.async_mutate(
            self.user_a, family_uuid=self.head_b.family.uuid,
            insuree_uuid=self.member_a.uuid, cancel_policies=False))
        self.assertEqual(self.head_a.family_id, Insuree.objects.get(id=self.member_a.id).family_id,
                         "insuree moved into a district-2 family")

    def test_update_refuses_foreign_insuree(self):
        """[REF test_insuree_write_row_security.py::test_update_refuses_foreign_insuree]"""
        from insuree.gql_mutations import UpdateInsureeMutation
        # NB Cameroon's InsureeService.create_or_update re-saves the stored row without
        # applying the payload (services.py ~400), so the field cannot be the witness:
        # the refusal must come from the rights check.
        refused = _unauthorized(lambda: UpdateInsureeMutation.async_mutate(
            self.user_a, uuid=str(self.member_b.uuid), chf_id=self.member_b.chf_id,
            last_name="SPKHACK", other_names="X", gender_id="M", dob="1980-01-01", head=False, card_issued=False,
            family_id=self.head_b.family_id))
        self.assertTrue(refused, "UpdateInsuree on a district-2 insuree not refused")

    def test_update_own_insuree_allowed(self):
        """[control] the update payload used above is functionally valid: same call on
        an insuree of district 1 succeeds (so a refusal above is a rights refusal)."""
        from insuree.gql_mutations import UpdateInsureeMutation
        errors = UpdateInsureeMutation.async_mutate(
            self.user_a, uuid=str(self.member_a.uuid), chf_id=self.member_a.chf_id,
            last_name="SPKOWN", other_names="X", gender_id="M", dob="1980-01-01", head=False,
            card_issued=False, family_id=self.head_a.family_id)
        self.assertFalse(errors, errors)

    def test_create_own_insuree_allowed(self):
        """[control] creating an insuree in a district-1 village works with this payload."""
        from insuree.gql_mutations import CreateInsureeMutation
        errors = CreateInsureeMutation.async_mutate(
            self.user_a, chf_id="SPK00098", last_name="SPK", other_names="Own",
            gender_id="M", dob="1980-01-01", head=False, card_issued=False,
            current_village_id=self.t.v1.id)
        self.assertFalse(errors, errors)

    def test_update_family_refuses_foreign_family(self):
        """[NEW] UpdateFamily on a district-2 family is refused."""
        from insuree.gql_mutations import UpdateFamilyMutation
        refused = _unauthorized(lambda: UpdateFamilyMutation.async_mutate(
            self.user_a, uuid=str(self.head_b.family.uuid), location_id=self.t.v2.id,
            head_insuree_id=self.head_b.id, address="SPKHACK"))
        self.assertTrue(refused, "UpdateFamily on district 2 not refused for rights")

    def test_create_family_refuses_foreign_village(self):
        """[REF test_insuree_write_row_security.py::test_create_refuses_foreign_village]"""
        from insuree.gql_mutations import CreateFamilyMutation
        refused = _unauthorized(lambda: CreateFamilyMutation.async_mutate(
            self.user_a, location_id=self.t.v2.id, head_insuree={}))
        self.assertTrue(refused, "family creation in a district-2 village not refused")

    def test_create_insuree_refuses_foreign_village(self):
        """[REF test_insuree_write_row_security.py::test_create_refuses_foreign_village]"""
        from insuree.gql_mutations import CreateInsureeMutation
        _refused(lambda: CreateInsureeMutation.async_mutate(
            self.user_a, chf_id="SPK00099", last_name="SPK", other_names="New",
            gender_id="M", dob="1980-01-01", head=False, card_issued=False, current_village_id=self.t.v2.id))
        self.assertFalse(Insuree.objects.filter(chf_id="SPK00099").exists(),
                         "insuree created in a district-2 village")


@override_settings(ROW_SECURITY=True)
class InsureeRightNamesTest(TestCase):
    """[REF insuree/tests/test_mutation_right_names.py] each mutation checks its own right."""

    @classmethod
    def setUpTestData(cls):
        cls.t = create_security_tree("SPL")
        cls.head_a, cls.member_a = _build_family(cls.t.v1, "SPL00001", "SPL00002")
        cls.update_only = create_right_only_user(
            "splupd", _u(READ_RIGHTS, perm_ids(InsureeConfig.gql_mutation_update_insurees_perms)), [cls.t.d1.id])
        cls.create_only = create_right_only_user(
            "splcre", _u(READ_RIGHTS, perm_ids(InsureeConfig.gql_mutation_create_insurees_perms)), [cls.t.d1.id])

    def setUp(self):
        cache.clear()

    def _update(self, user):
        from insuree.gql_mutations import UpdateInsureeMutation
        return lambda: UpdateInsureeMutation.async_mutate(
            user, uuid=str(self.member_a.uuid), chf_id=self.member_a.chf_id, last_name="SPLUPD",
            other_names="X", gender_id="M", dob="1980-01-01", head=False, card_issued=False, family_id=self.head_a.family_id)

    def test_update_insuree_granted_by_update_right(self):
        """[REF test_mutation_right_names.py] the update right alone allows UpdateInsuree
        (Cameroon checks gql_mutation_create_insurees_perms, gql_mutations.py:319)."""
        self.assertFalse(_unauthorized(self._update(self.update_only)),
                         "UpdateInsuree refused to a holder of the update right")

    def test_update_insuree_not_granted_by_create_right(self):
        """[REF test_mutation_right_names.py] the create right alone does NOT allow UpdateInsuree."""
        self.assertTrue(_unauthorized(self._update(self.create_only)),
                        "UpdateInsuree allowed with the create right only")
