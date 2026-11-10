from django.test import TestCase
from unittest import mock
from insuree.services import InsureeService
from insuree.test_helpers import create_test_insuree
from core.test_helpers import create_test_interactive_user

class InsureeServiceTest(TestCase):

    @classmethod
    def setUpTestData(self):
        self.user = create_test_interactive_user()
        self.service = InsureeService(self.user)

    @mock.patch.object(InsureeService, "_create_or_update")
    @mock.patch.object(InsureeService, "_update")
    def test_should_call_update_for_existing_insuree(
        self,
        mock_update,
        mock_create_or_update
    ):
        # Given
        insuree = create_test_insuree(
            custom_props={
                "email": "old@gmail.com"
            }
        )

        mock_create_or_update.return_value = insuree

        data = {
            "uuid": str(insuree.uuid),
            "email": "new@gmail.com",
        }

        # When
        self.service.create_or_update(data)

        # Then
        mock_update.assert_called_once()

        called_insuree, called_data = mock_update.call_args[0]

        self.assertEqual(called_insuree.id, insuree.id)
        self.assertEqual(called_data["email"], "new@gmail.com")