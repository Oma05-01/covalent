from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Wallet, Contract, Dispute, DisputeEvidence
import io
from PIL import Image
from escrow.models import ArbitratorAssignment

User = get_user_model()

class DisputeE2ETests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_e2e2@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_e2e2@covalent.com", password="password")
        
        buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        buyer_wallet.available_balance = Decimal("10000.00")
        buyer_wallet.locked_escrow_balance = Decimal("60000.00")
        buyer_wallet.save()

        vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)
        vendor_wallet.available_balance = Decimal("0.00")
        vendor_wallet.save()

        # Create 3 lawyers for consensus
        self.lawyers = []
        for i in range(3):
            lawyer = User.objects.create_user(email=f"lawyer_e2e_{i}@covalent.com", password="password", is_lawyer=True)
            w, _ = Wallet.objects.get_or_create(user=lawyer)
            w.available_balance = Decimal("0.00")
            w.save()
            self.lawyers.append(lawyer)

        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            item_amount=Decimal("60000.00"),
            delivery_fee=Decimal("0.00"),
            status="DELIVERED"
        )

    def test_e2e_full_dispute_lifecycle(self):
        """E2E: Raise -> Evidence -> Review -> Decision -> Distribution"""
        # 1. Buyer raises dispute
        self.client.force_authenticate(user=self.buyer)
        res_disp = self.client.post(f'/api/v1/escrow/contracts/{self.contract.contract_id}/dispute/')
        self.assertEqual(res_disp.status_code, status.HTTP_200_OK)
        dispute_id = res_disp.data['dispute_id']

        # 2. Upload DisputeEvidence (using multipart/form-data)
        image_buffer = io.BytesIO()
        image = Image.new('RGB', (1, 1), color='white')
        image.save(image_buffer, format='JPEG')
        image_buffer.seek(0)
        
        # 👇 Use the valid image buffer bytes instead of b"file_content"
        mock_file = SimpleUploadedFile("evidence.jpg", image_buffer.read(), content_type="image/jpeg")
        
        res_ev = self.client.post(
            f'/api/v1/escrow/disputes/{dispute_id}/evidence/',
            data={'file': mock_file, 'file_type': 'IMAGE'},
            format='multipart'
        )
        self.assertEqual(res_ev.status_code, status.HTTP_201_CREATED)

        # 3. Lawyers Review & Vote
        legal_justification = "Based on the provided evidence and the smart contract terms, this is a formal legal justification for the ruling that exceeds the eighty character minimum requirement."

        # 3. Lawyers Review & Vote
        dispute = Dispute.objects.get(id=dispute_id)

        assignments = ArbitratorAssignment.objects.filter(dispute=dispute)
        for assignment in assignments:
            assignment.status = 'ACCEPTED'
            assignment.save()

        # 2 lawyers vote for the buyer
        for lawyer in self.lawyers[:2]:
            self.client.force_authenticate(user=lawyer)
            res = self.client.post(f'/api/v1/escrow/disputes/{dispute_id}/vote/', data={
                'ruling': 'buyer', 
                'justification': legal_justification
            })
            
            if res.status_code == 400:
                print("\nDRF ERROR 1:", res.data)

        # 4. Final Vote Triggers Consensus (Votes for Vendor / Party B)
        self.client.force_authenticate(user=self.lawyers[2])
        res2 = self.client.post(f'/api/v1/escrow/disputes/{dispute_id}/vote/', data={
            'ruling': 'vendor', 
            'justification': legal_justification
        })
        
        if res2.status_code == 400:
            print("\nDRF ERROR 2:", res2.data)

        # 5. Verify Payout and Penalties
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "REFUNDED") # Buyer won
        
        self.buyer.governance_profile.refresh_from_db()
        self.vendor.governance_profile.refresh_from_db()
        
        # Buyer started at 50, gets +2 for winning
        self.assertEqual(self.buyer.governance_profile.trust_score, 52)
        # Vendor started at 50, gets -15 for losing
        self.assertEqual(self.vendor.governance_profile.trust_score, 35)
        # Vendor drops below 50, status should now be WARNING
        self.assertEqual(self.vendor.governance_profile.status, 'WARNING')

        self.buyer.wallet.refresh_from_db()
        # Initial 10k - 5k fee + 60k refund = 65000
        self.assertEqual(self.buyer.wallet.available_balance, Decimal("65000.00"))
        
        self.vendor.refresh_from_db()
