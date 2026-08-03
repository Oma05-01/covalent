from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from decimal import Decimal
from accounts.models import Dispute
from accounts.models import Contract, Wallet
from escrow.models import LedgerTransaction
from escrow.models import ArbitratorAssignment
from django.urls import reverse
from django.utils import timezone
from accounts.models import ArbitrationVote
from escrow.services import deposit_funds

User = get_user_model()

class EscrowAPITests(APITestCase):
    def setUp(self):
        """Provision the marketplace actors and a pending contract."""
        self.buyer = User.objects.create_user(
            email="api_buyer@covalent.com", password="password123"
        )
        self.vendor = User.objects.create_user(
            email="api_vendor@covalent.com", password="password123"
        )

        self.lawyer1 = User.objects.create_user(email="lawyer1@covalent.com", password="password", is_lawyer=True, trust_score=100)
        self.lawyer2 = User.objects.create_user(email="lawyer2@covalent.com", password="password", is_lawyer=True, trust_score=100)
        self.lawyer3 = User.objects.create_user(email="lawyer3@covalent.com", password="password", is_lawyer=True, trust_score=100)
        
        Wallet.objects.get_or_create(user=self.lawyer1)
        Wallet.objects.get_or_create(user=self.lawyer2)
        Wallet.objects.get_or_create(user=self.lawyer3)
        
        # Ensure wallets exist (if your signal doesn't auto-create them in testing)
        self.buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        self.vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)

        # Create a contract waiting for payment
        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            vendor_email=self.vendor.email,
            item_title="Integration Test Job",
            item_description="Testing escrow endpoints.",
            item_amount=Decimal("100000.00"),
            delivery_fee=Decimal("0.00"),
            paystack_reference="REF_TEST_123",
            status="AWAITING_FUNDING"
        )

    def test_paystack_webhook_funds_and_locks_escrow(self):
        """Asserts the payment callback deposits and locks money in the buyer's wallet."""
        self.client.force_authenticate(user=self.buyer)
        
        payload = {"reference": "REF_TEST_123"}
        
        # Simulate Paystack hitting our verify endpoint
        response = self.client.post('/api/v1/escrow/payments/verify/', payload, format='json')
        
        # 1. API Response Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. Contract State Check
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "FUNDED")
        
        # 3. Financial Ledger Check
        self.buyer_wallet.refresh_from_db()
        self.assertEqual(self.buyer_wallet.locked_escrow_balance, Decimal("100000.00"))
        
        # 4. Transaction Integrity Check
        # There should be 2 ledger entries: The external deposit, and the escrow lock
        transactions = LedgerTransaction.objects.filter(wallet=self.buyer_wallet)
        self.assertEqual(transactions.count(), 2)
        self.assertTrue(transactions.filter(transaction_type="DEPOSIT").exists())
        self.assertTrue(transactions.filter(transaction_type="ESCROW_LOCK").exists())

    def test_buyer_approval_releases_escrow_to_vendor(self):
        """Asserts a buyer approving a delivery moves money to the vendor."""
        # 1. Setup: Fast-forward the contract to DELIVERED and manually lock funds
        self.contract.status = "DELIVERED"
        self.contract.save()
        
        self.buyer_wallet.locked_escrow_balance = Decimal("100000.00")
        self.buyer_wallet.save()

        # 2. Action: Buyer approves the deal
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/approve/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Verify Contract State
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "RELEASED")
        
        # 4. Verify the Money Moved!
        self.buyer_wallet.refresh_from_db()
        self.vendor_wallet.refresh_from_db()
        
        self.assertEqual(self.buyer_wallet.locked_escrow_balance, Decimal("0.00"))
        self.assertEqual(self.vendor_wallet.available_balance, Decimal("100000.00"))


    def test_vendor_delivery_starts_timer(self):
        """Asserts vendor marking item as 'deliver' sets delivered_at and auto_release_at deadline."""
        self.contract.status = "FUNDED"
        self.contract.save()
        
        self.client.force_authenticate(user=self.vendor)
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/deliver/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DELIVERED")
        self.assertIsNotNone(self.contract.delivered_at)
        self.assertIsNotNone(self.contract.auto_release_at)

    def test_raise_dispute_deducts_fee_and_drafts_lawyers(self):
        """Asserts raising a dispute debits 5000 NGN and creates 3 assignments."""
        # 1. Fast forward contract to DELIVERED and give buyer enough money for the fee
        self.contract.status = "DELIVERED"
        self.contract.save()
        deposit_funds(self.buyer, Decimal("10000.00"), reference="BUYER_FUNDING")
        
        # 2. Buyer raises dispute
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/', {"reason": "Item was broken"}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Assert Fee was deducted via Ledger
        self.buyer_wallet.refresh_from_db()
        self.assertEqual(self.buyer_wallet.available_balance, Decimal("5000.00"))  # 10k - 5k fee
        
        # 4. Assert Dispute and Lawyers drafted
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DISPUTED")
        
        dispute = Dispute.objects.get(contract=self.contract)
        assignments = ArbitratorAssignment.objects.filter(dispute=dispute)
        self.assertEqual(assignments.count(), 3)

    def test_lawyer_vote_triggers_consensus(self):
        """Asserts casting the 3rd valid verdict executes payout."""
        # 1. Setup a dispute and assignments manually
        self.contract.status = "DISPUTED"
        self.contract.save()
        
        # Lock escrow so payout has funds to move
        self.buyer_wallet.locked_escrow_balance = Decimal("100000.00")
        self.buyer_wallet.save()
        
        dispute = Dispute.objects.create(contract=self.contract, initiator=self.buyer, reason="Fake item")
        ArbitratorAssignment.objects.create(dispute=dispute, lawyer=self.lawyer1, status="ACCEPTED")
        ArbitratorAssignment.objects.create(dispute=dispute, lawyer=self.lawyer2, status="ACCEPTED")
        ArbitratorAssignment.objects.create(dispute=dispute, lawyer=self.lawyer3, status="ACCEPTED")
        
        # 2. Two lawyers vote for the Vendor
        ArbitrationVote.objects.create(dispute=dispute, lawyer=self.lawyer1, ruling="vendor", legal_justification="Evidence clears vendor.")
        ArbitrationVote.objects.create(dispute=dispute, lawyer=self.lawyer2, ruling="vendor", legal_justification="Buyer claim unfounded.")
        
        # 3. Third lawyer votes via API
        self.client.force_authenticate(user=self.lawyer3)
        payload = {"ruling": "buyer", 
                    "justification": "I strongly disagree with my colleagues. The buyer provided a complete, unedited unboxing video that clearly shows the defect."}
        
        response = self.client.post(f'/api/v1/escrow/disputes/{dispute.id}/vote/', payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Verify Consensus Executed (Vendor wins 2 to 1)
        dispute.refresh_from_db()
        self.contract.refresh_from_db()
        self.vendor_wallet.refresh_from_db()
        
        self.assertEqual(dispute.status, "RESOLVED")
        self.assertEqual(self.contract.status, "COMPLETED")
        self.assertEqual(self.vendor_wallet.available_balance, Decimal("100000.00"))


    def test_raise_dispute_deducts_fee(self):
        """Asserts initiating a dispute debits the arbitration fee using the ledger service."""
        self.contract.status = "DELIVERED"
        self.contract.save()
        deposit_funds(self.buyer, Decimal("10000.00"), reference="FEE_FUNDING")
        
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/', {"reason": "Defective item fee test"}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.buyer_wallet.refresh_from_db()
        self.assertEqual(self.buyer_wallet.available_balance, Decimal("5000.00"))

    def test_raise_dispute_drafts_lawyers(self):
        """Asserts dispute creation successfully drafts 3 eligible, non-involved lawyers."""
        self.contract.status = "DELIVERED"
        self.contract.save()
        deposit_funds(self.buyer, Decimal("10000.00"), reference="DRAFT_FUNDING")
        
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/', {"reason": "Draft check"}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        
        dispute = Dispute.objects.get(contract=self.contract)
        assignments = ArbitratorAssignment.objects.filter(dispute=dispute)
        self.assertEqual(assignments.count(), 3)
        
        # Ensure neither buyer nor vendor were accidentally drafted
        drafted_lawyer_ids = assignments.values_list('lawyer_id', flat=True)
        self.assertNotIn(self.buyer.id, drafted_lawyer_ids)
        self.assertNotIn(self.vendor.id, drafted_lawyer_ids)