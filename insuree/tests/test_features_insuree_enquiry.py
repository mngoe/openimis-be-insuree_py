"""
Tests for backend/features/insuree-enquiry.feature, insuree module part.
"""
import unittest
import datetime
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.test_helpers import create_test_interactive_user
from insuree.models import Insuree
from insuree.services import InsureeService, validate_insuree_number
from insuree.test_helpers import create_test_insuree

HIV_MARKER_EMAIL = "newhivuser_XM7dw70J0M3N@gmail.com"
GAP = "CHFID normalisation (#38348, insuree PR 152) is not in this checkout: it is on origin/test-csu"


@mock.patch("insuree.services.InsureeConfig.is_insuree_photo_required", False)
class ChfidNormalisationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_test_interactive_user(username="featinschf")
        cls.service = InsureeService(cls.user)

    def _saved_chf_id(self, raw, **extra):
        with mock.patch.object(InsureeService, "_create_or_update", side_effect=lambda ins, photo: ins) as m:
            self.service.create_or_update({
                "chf_id": raw, "last_name": "TEST", "other_names": "TEST",
                "gender_id": "M", "dob": "1990-01-01", **extra,
            }, create_family=False)
        return m.call_args[0][0].chf_id

    # Scenario: Insuree create and update trim the CHFID (@redmine-38348)
    def test_chfid_trimmed(self):
        cases = [
            ("120902348063480 ", "120902348063480"),
            (" 120902348063480 ", "120902348063480"),
            (" ​120902348063480​", "120902348063480"),
            ("CE/38/01/23/001 AKO/ELI ", "CE/38/01/23/001 AKO/ELI"),
        ]
        for raw, stored in cases:
            with self.subTest(raw=repr(raw)):
                self.assertEqual(self._saved_chf_id(raw), stored, GAP)

    # Scenario: An invisible character inside the CHFID is refused (@redmine-38348)
    def test_inner_invisible_character_refused(self):
        with self.assertRaisesRegex(ValidationError, "invisible characters", msg=GAP):
            self._saved_chf_id("1209​02348063480")

    # Scenario: The insuree number validation uses the normalised number (@redmine-38348)
    @mock.patch("insuree.services.InsureeConfig.get_insuree_number_modulo_root", return_value=None)
    @mock.patch("insuree.services.InsureeConfig.get_insuree_number_length", return_value=None)
    @mock.patch("insuree.services.InsureeConfig.get_insuree_number_validator", return_value=None)
    def test_validate_insuree_number_normalises(self, *_):
        self.assertEqual(validate_insuree_number(" 120902348063480 "), [])
        self.assertEqual(len(validate_insuree_number("1209\t02348063480")), 1, GAP)

    # Scenario: An all-numeric MPI is still refused for an HIV patient (@redmine-38348)
    def test_all_numeric_mpi_refused_for_hiv(self):
        with self.assertRaisesRegex(ValidationError, "mutation.insuree.mpi_entirely_numeric_error"):
            self._saved_chf_id("120902348063480", email=HIV_MARKER_EMAIL)


@mock.patch("insuree.services.InsureeConfig.is_insuree_photo_required", False)
class HivPatientUpdateTest(TestCase):
    # Scenario: Changes to an HIV patient are saved (@redmine-38086)
    def test_hiv_patient_changes_saved(self):
        user = create_test_interactive_user(username="featinshiv")
        insuree = create_test_insuree(custom_props={
            "chf_id": "TARVFEAT01", "email": HIV_MARKER_EMAIL, "dob": datetime.date(1980, 1, 1)})
        InsureeService(user).create_or_update({
            "uuid": str(insuree.uuid),
            "chf_id": "TARVFEAT01",
            "last_name": insuree.last_name,
            "other_names": insuree.other_names,
            "email": HIV_MARKER_EMAIL,
            "dob": datetime.date(1981, 2, 3),
            "gender_id": "F",
            "head": insuree.head,
            "family_id": insuree.family_id,
        })
        current = Insuree.objects.get(chf_id="TARVFEAT01", validity_to__isnull=True)
        self.assertEqual(current.dob, datetime.date(1981, 2, 3),
                         "update of an existing insuree drops the new values (fix #38082/#38086 on origin/dev-csu)")
        self.assertEqual(current.gender_id, "F")


class TemporaryMpiTest(TestCase):
    # Scenario: A temporary MPI number is linked to the final MPI number (@redmine-28689)
    @unittest.skip("postponed: #28689")
    def test_temporary_mpi_linked_to_final(self):
        pass
