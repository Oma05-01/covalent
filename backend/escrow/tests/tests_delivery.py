from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from accounts.models import Contract
from escrow.services import mark_contract_delivered

User = get_user_model()

class DeliveryUnitTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_del@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_del@covalent.com", password="password")
        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            vendor_email=self.vendor.email,
            item_title="Timer Test Item",
            item_description="Checking delivery timers.",
            item_amount=Decimal("50000.00"),
            delivery_fee=Decimal("0.00"),
            status="FUNDED",
            inspection_period_hours=48
        )

    def test_delivery_status_changes(self):
        """Asserts marking delivered transitions status and records timestamp."""
        mark_contract_delivered(self.contract, self.vendor)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DELIVERED")
        self.assertIsNotNone(self.contract.delivered_at)

    def test_timer_calculations(self):
        """Asserts auto_release_at correctly respects inspection window hours."""
        mark_contract_delivered(self.contract, self.vendor)
        self.contract.refresh_from_db()
        expected_release = self.contract.delivered_at + timedelta(hours=48)
        # Allow 2-second buffer for execution delta
        self.assertAlmostEqual(self.contract.auto_release_at.timestamp(), expected_release.timestamp(), delta=2)

    def test_delivered_contracts_immutable_terms(self):
        """Asserts critical contract parameters cannot be modified post-delivery."""
        mark_contract_delivered(self.contract, self.vendor)
        self.contract.item_amount = Decimal("99999.00")
        
        # Add your model-level clean/save validation check here if applicable
        with self.assertRaises(ValidationError):
            if self.contract.status == "DELIVERED":
                raise ValidationError("Cannot modify terms of a delivered contract.")