from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Wallet, Contract

User = get_user_model()

class DeliveryIntegrationTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_di@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_di@covalent.com", password="password")
        
        buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        buyer_wallet.available_balance = Decimal("100000.00")
        buyer_wallet.locked_escrow_balance = Decimal("50000.00")
        buyer_wallet.save()

        vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)
        vendor_wallet.available_balance = Decimal("0.00")
        vendor_wallet.save()

        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            vendor_email=self.vendor.email,
            item_title="Integration Item",
            item_description="Testing delivery integration flows.",
            item_amount=Decimal("50000.00"),
            delivery_fee=Decimal("0.00"),
            status="FUNDED"
        )

    def test_vendor_marks_delivered_and_countdown_starts(self):
        """Asserts vendor delivery endpoint initiates countdown timer successfully."""
        self.client.force_authenticate(user=self.vendor)
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/deliver/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DELIVERED")
        self.assertIsNotNone(self.contract.auto_release_at)

    def test_auto_release_only_after_timer(self):
        """Business Rule: Auto-release background check ignores contracts within the review window."""
        self.contract.status = "DELIVERED"
        self.contract.delivered_at = timezone.now()
        self.contract.auto_release_at = timezone.now() + timedelta(hours=24) # Future
        self.contract.save()

        # Simulate scheduler check
        expired_contracts = Contract.objects.filter(status="DELIVERED", auto_release_at__lte=timezone.now())
        self.assertNotIn(self.contract, expired_contracts)