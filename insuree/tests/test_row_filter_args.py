import json
from dataclasses import dataclass

from graphql_jwt.shortcuts import get_token

from core.models import User
from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase
from core.test_helpers import create_test_interactive_user
from insuree.models import Family, Insuree
from insuree.test_helpers import create_test_insuree
from location.test_helpers import create_test_village


@dataclass
class DummyContext:
    user: User


class InsureeRowFilterArgsTest(openIMISGraphQLTestCase):
    """insurees / families: the legacy arguments keep their meaning, isDeleted is new.

    Validity is applied by the models (OP-2029), not by the resolvers: the
    resolvers only state what their legacy arguments mean.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        village = create_test_village({"name": "RowArgs"})
        cls.live = create_test_insuree(
            with_family=True, is_head=True,
            custom_props={"chf_id": "RFA000001", "current_village": village},
            family_custom_props={"location": village})
        cls.deleted = create_test_insuree(
            with_family=True, is_head=True,
            custom_props={"chf_id": "RFA000002", "current_village": village},
            family_custom_props={"location": village})
        Insuree.objects.filter(id=cls.deleted.id).update(validity_to="2020-01-01")
        Family.objects.filter(id=cls.deleted.family_id).update(validity_to="2020-01-01")
        cls.admin = create_test_interactive_user(username="rowArgsAdmin")
        cls.token = get_token(cls.admin, DummyContext(user=cls.admin))

    def _chf_ids(self, args):
        response = self.query(
            '{ insurees(chfId_Istartswith: "RFA"%s) { edges { node { chfId } } } }' % args,
            headers={"HTTP_AUTHORIZATION": f"Bearer {self.token}"})
        self.assertResponseNoErrors(response)
        edges = json.loads(response.content)["data"]["insurees"]["edges"]
        return sorted(e["node"]["chfId"] for e in edges)

    def _family_found(self, family, args=""):
        response = self.query(
            '{ families(uuid: "%s"%s) { totalCount } }' % (family.uuid, args),
            headers={"HTTP_AUTHORIZATION": f"Bearer {self.token}"})
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]["families"]["totalCount"] == 1

    def test_default_hides_deleted_insurees(self):
        self.assertEqual(["RFA000001"], self._chf_ids(""))

    def test_show_history_keeps_its_legacy_meaning(self):
        self.assertEqual(["RFA000001", "RFA000002"], self._chf_ids(", showHistory: true"))

    def test_uuid_lookup_finds_a_deleted_insuree(self):
        self.assertEqual(["RFA000002"], self._chf_ids(', uuid: "%s"' % self.deleted.uuid))

    def test_is_deleted(self):
        self.assertEqual(["RFA000002"], self._chf_ids(", isDeleted: true"))
        self.assertEqual(["RFA000001"], self._chf_ids(", isDeleted: false"))

    def test_is_deleted_overrides_show_history(self):
        self.assertEqual(["RFA000001"], self._chf_ids(", showHistory: true, isDeleted: false"))

    def test_families(self):
        deleted_family = Family.objects.get(id=self.deleted.family_id)
        self.assertTrue(self._family_found(self.live.family))
        self.assertFalse(self._family_found(deleted_family))
        self.assertTrue(self._family_found(deleted_family, ", showHistory: true"))
        self.assertTrue(self._family_found(deleted_family, ", isDeleted: true"))
