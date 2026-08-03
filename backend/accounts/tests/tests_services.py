from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from accounts.models import Contract, ContractVersion
# We will create this file next!
from accounts.services import update_contract_terms, accept_contract, generate_contract_summary

User = get_user_model()

class ContractServiceTests(TestCase):
    def setUp(self):
        """Provision the test actors."""
        self.buyer = User.objects.create_user(
            email="buyer2@covalent.com",
            password="securepassword123",
            first_name="Client",
            last_name="Two"
        )
        self.vendor = User.objects.create_user(
            email="vendor2@covalent.com",
            password="securepassword123",
            first_name="Freelancer",
            last_name="Two"
        )
        
        # A standard draft contract
        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,  # 🆕 Added the vendor so validation passes!
            item_title="Initial Title",
            item_description="Initial Description",
            item_amount=Decimal("100000.00"),
            delivery_fee=Decimal("0.00"),
            status="DRAFT"
        )

    def test_contract_version_snapshot_created(self):
        """Asserts modifying a contract logs a new ContractVersion."""
        
        # Action: Update the contract via our service
        updated_contract = update_contract_terms(
            contract=self.contract,
            user=self.buyer,
            item_amount=Decimal("120000.00"),
            item_title="Updated Title"
        )
        
        # Assertions
        self.assertEqual(updated_contract.item_amount, Decimal("120000.00"))
        
        # Verify the snapshot was created
        self.assertEqual(self.contract.versions.count(), 1)
        latest_version = self.contract.versions.first()
        self.assertEqual(latest_version.version_number, 1)
        self.assertEqual(latest_version.item_amount, Decimal("120000.00"))
        self.assertEqual(latest_version.created_by, self.buyer)

    def test_cannot_edit_accepted_contract(self):
        """Asserts editing core terms after acceptance raises an error."""
        # Manually push it to accepted state
        self.contract.status = "AWAITING_FUNDING"
        self.contract.save()
        
        # Action & Assertion
        with self.assertRaisesMessage(ValidationError, "Cannot edit an accepted or active contract."):
            update_contract_terms(
                contract=self.contract,
                user=self.buyer,
                item_amount=Decimal("150000.00")
            )

    def test_acceptance_timestamp_recorded(self):
        """Asserts accepting a contract binds the vendor and logs the exact time."""
        
        # Action: Accept the contract via our service
        accepted_contract = accept_contract(contract=self.contract, vendor=self.vendor)
        
        # Assertions
        self.assertEqual(accepted_contract.status, "AWAITING_FUNDING")
        self.assertEqual(accepted_contract.vendor, self.vendor)
        self.assertFalse(accepted_contract.is_public)
        self.assertIsNotNone(accepted_contract.accepted_at)
        
        # Ensure the timestamp is recent (within the last minute)
        time_difference = timezone.now() - accepted_contract.accepted_at
        self.assertLess(time_difference, timedelta(minutes=1))

    def test_plain_language_summary_generation(self):
        """Asserts the plain-language summary is successfully generated and saved."""
        
        self.assertIsNone(self.contract.plain_language_summary)
        
        # Action
        contract_with_summary = generate_contract_summary(self.contract)
        
        # Assertions
        self.assertIsNotNone(contract_with_summary.plain_language_summary)
        self.assertIn("Initial Title", contract_with_summary.plain_language_summary)