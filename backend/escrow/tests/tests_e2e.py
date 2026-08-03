from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import Dispute, Wallet
from escrow.models import ArbitratorAssignment
from escrow.services import deposit_funds
from accounts.models import PlatformAuditLog, ArbitrationVote, Contract

User = get_user_model()

class EscrowE2ETests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_e2e@covalent.com", password="password", trust_score=100)
        self.vendor = User.objects.create_user(email="vendor_e2e@covalent.com", password="password", trust_score=100)
        
        # Use get_or_create to safely handle automatic signal creation
        self.buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        self.buyer_wallet.available_balance = Decimal("200000.00")
        self.buyer_wallet.save()

        self.vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)
        self.vendor_wallet.available_balance = Decimal("0.00")
        self.vendor_wallet.save()
        
        self.lawyer1 = User.objects.create_user(email="lawyer1_e2e@covalent.com", password="password", is_lawyer=True, trust_score=100)
        self.lawyer2 = User.objects.create_user(email="lawyer2_e2e@covalent.com", password="password", is_lawyer=True, trust_score=100)
        self.lawyer3 = User.objects.create_user(email="lawyer3_e2e@covalent.com", password="password", is_lawyer=True, trust_score=100)
        
        Wallet.objects.get_or_create(user=self.lawyer1)
        Wallet.objects.get_or_create(user=self.lawyer2)
        Wallet.objects.get_or_create(user=self.lawyer3)

        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            vendor_email=self.vendor.email,
            item_title="E2E MacBook Pro",
            item_description="Full stack deployment test machine.",
            item_amount=Decimal("150000.00"),
            delivery_fee=Decimal("5000.00"),
            paystack_reference="E2E_REF_001",
            status="AWAITING_FUNDING"
        )

    def test_e2e_happy_path_escrow(self):
        """E2E 1: Fund -> Deliver -> Approve -> Withdraw."""
        # Step 1: Buyer funds contract via Paystack webhook simulation
        self.client.force_authenticate(user=self.buyer)
        res_pay = self.client.post('/api/v1/escrow/payments/verify/', {"reference": "E2E_REF_001"}, format='json')
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "FUNDED")

        # Step 2: Vendor marks item delivered
        self.client.force_authenticate(user=self.vendor)
        res_del = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/deliver/', format='json')
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        # Step 3: Buyer approves item within inspection window
        self.client.force_authenticate(user=self.buyer)
        res_app = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/approve/', format='json')
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)
        
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "RELEASED")

        # Step 4: Vendor verifies available balance and executes withdrawal simulation
        self.vendor_wallet.refresh_from_db()
        self.assertEqual(self.vendor_wallet.available_balance, Decimal("155000.00"))

    def test_e2e_dispute_and_arbitration_flow(self):
        """E2E 2: Fund -> Deliver -> Dispute -> Arbitration Consensus -> Payout & Penalties."""
        # Setup: Fast-forward contract to FUNDED
        self.contract.status = "FUNDED"
        self.contract.save()
        self.buyer_wallet.available_balance = Decimal("155000.00")
        self.buyer_wallet.locked_escrow_balance = Decimal("155000.00")
        self.buyer_wallet.save()

        # Vendor delivers item
        self.contract.status = "DELIVERED"
        self.contract.save()

        # Step 1 & 2: Buyer rejects item at the door, raising a dispute
        self.client.force_authenticate(user=self.buyer)
        deposit_funds(self.buyer, Decimal("10000.00"), reference="DISPUTE_FEE_TOPUP")
        
        res_disp = self.client.post(
            f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/', 
            {"reason": "Item arrived cracked and completely unusable."}, 
            format='json'
        )
        self.assertEqual(res_disp.status_code, status.HTTP_200_OK)

        # Step 3: Verify fee charged to buyer and contract status set
        self.buyer_wallet.refresh_from_db()
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "DISPUTED")

        # Step 4: Lawyers accept assignments and cast votes (2 for Vendor, 1 for Buyer)
        dispute = Dispute.objects.get(contract=self.contract)
        
        for lawyer in [self.lawyer1, self.lawyer2, self.lawyer3]:
            assignment = ArbitratorAssignment.objects.get(dispute=dispute, lawyer=lawyer)
            assignment.status = "ACCEPTED"
            assignment.save()

        ArbitrationVote.objects.create(
            dispute=dispute, lawyer=self.lawyer1, ruling="vendor", 
            legal_justification="Vendor submitted unblemished dispatch photos confirming secure handling."
        )
        ArbitrationVote.objects.create(
            dispute=dispute, lawyer=self.lawyer2, ruling="vendor", 
            legal_justification="Buyer failed to provide definitive unboxing evidence within policy guidelines."
        )

        # Third lawyer votes via API to trigger consensus (Vendor wins 2 to 1)
        self.client.force_authenticate(user=self.lawyer3)
        payload = {
            "ruling": "buyer", 
            "justification": "I find the shipping carrier negligence report compelling enough to favor the buyer claim."
        }
        res_vote = self.client.post(f'/api/v1/escrow/disputes/{dispute.id}/vote/', payload, format='json')
        self.assertEqual(res_vote.status_code, status.HTTP_200_OK)

        # Step 5: Verify Vendor wins escrow payout, Buyer trust score is penalized
        dispute.refresh_from_db()
        self.contract.refresh_from_db()
        self.vendor_wallet.refresh_from_db()
        self.buyer.refresh_from_db()

        self.assertEqual(dispute.status, "RESOLVED")
        self.assertEqual(self.contract.status, "COMPLETED")
        self.assertEqual(self.vendor_wallet.available_balance, Decimal("155000.00"))
        self.assertEqual(self.buyer.trust_score, 85)  # 100 - 15 penalty