from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Wallet, Contract

User = get_user_model()

class DeliveryE2ETests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_e2e_del@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_e2e_del@covalent.com", password="password")
        
        buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        buyer_wallet.available_balance = Decimal("100000.00")
        buyer_wallet.locked_escrow_balance = Decimal("60000.00")
        buyer_wallet.save()

        vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)
        vendor_wallet.available_balance = Decimal("0.00")
        vendor_wallet.save()

        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            vendor_email=self.vendor.email,
            item_title="E2E Delivery Pipeline",
            item_description="Complete lifecycle test.",
            item_amount=Decimal("60000.00"),
            delivery_fee=Decimal("0.00"),
            status="FUNDED"
        )

    def test_e2e_delivery_to_funds_release(self):
        """E2E: Deliver work -> Inspection period -> Client approves -> Funds released."""
        # 1. Vendor delivers work
        self.client.force_authenticate(user=self.vendor)
        res_del = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/deliver/', format='json')
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        # 2. Verify inspection period countdown is active
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DELIVERED")
        self.assertIsNotNone(self.contract.auto_release_at)

        # 3. Client approves within inspection window
        self.client.force_authenticate(user=self.buyer)
        res_app = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/approve/', format='json')
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)

        # 4. Verify funds released to vendor wallet and contract closed
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "RELEASED")
        
        vendor_wallet = self.vendor.wallet
        vendor_wallet.refresh_from_db()
        self.assertEqual(vendor_wallet.available_balance, Decimal("60000.00"))