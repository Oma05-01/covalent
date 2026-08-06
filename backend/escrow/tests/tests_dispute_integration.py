from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Wallet, Contract, Dispute, DisputeEvidence


User = get_user_model()

class DisputeIntegrationTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_di2@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_di2@covalent.com", password="password")
        
        buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        buyer_wallet.available_balance = Decimal("10000.00")
        buyer_wallet.locked_escrow_balance = Decimal("50000.00")
        buyer_wallet.save()

        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            item_amount=Decimal("50000.00"),
            delivery_fee=Decimal("0.00"),
            status="DELIVERED"
        )

        # 👇 ADD THESE LAWYERS so the view doesn't 503
        for i in range(3):
            lawyer = User.objects.create_user(email=f"lawyer_di2_{i}@covalent.com", password="password", is_lawyer=True)
            w, _ = Wallet.objects.get_or_create(user=lawyer)

    def test_raise_dispute_deducts_support_fee_and_locks_state(self):
        self.client.force_authenticate(user=self.buyer)
        res = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/', data={'reason': 'Defective work'})
        
        # 👇 Change to 200_OK
        self.assertEqual(res.status_code, status.HTTP_200_OK) 
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DISPUTED")
        
        self.buyer.wallet.refresh_from_db()
        self.assertEqual(self.buyer.wallet.available_balance, Decimal("5000.00"))

    def test_lawyers_and_parties_are_anonymous(self):
        # 👇 Change raised_by to initiator
        dispute = Dispute.objects.create(contract=self.contract, initiator=self.buyer)
        
        self.client.force_authenticate(user=self.buyer)
        res = self.client.get(f'/api/v1/escrow/disputes/{dispute.id}/')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.vendor.email, str(res.data))