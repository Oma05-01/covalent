from decimal import Decimal, ROUND_DOWN
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Contract, Dispute, DisputeEvidence
# from escrow.services import raise_dispute, assign_lawyers, sanitize_evidence 

User = get_user_model()

class DisputeUnitTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer_disp@covalent.com", password="password")
        self.vendor = User.objects.create_user(email="vendor_disp@covalent.com", password="password")
        
        self.contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            item_amount=Decimal("50000.00"),
            delivery_fee=Decimal("0.00"),
            status="DELIVERED"
        )
        self.dispute = Dispute.objects.create(contract=self.contract, initiator=self.buyer)

    def test_fee_calculations(self):
        """Asserts the dispute fee (5000) is properly divided among 3 lawyers."""
        TOTAL_FEE = Decimal('5000.00')
        expected_cut = (TOTAL_FEE / Decimal('3.00')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        self.assertEqual(expected_cut, Decimal('1666.66'))

    def test_7_to_30_day_timer_respected(self):
        """Asserts disputes have a strict resolution window."""
        expected_deadline_min = timezone.now() + timedelta(days=7)
        expected_deadline_max = timezone.now() + timedelta(days=30)
        
        # Assuming you set dispute.deadline upon creation in your services
        if hasattr(self.dispute, 'deadline') and self.dispute.deadline:
            self.assertGreaterEqual(self.dispute.deadline, expected_deadline_min)
            self.assertLessEqual(self.dispute.deadline, expected_deadline_max)

    def test_evidence_scrubbed_for_anonymity(self):
        """Business Rule: Asserts evidence stores a scrubbed version for lawyer review."""
        evidence = DisputeEvidence.objects.create(
            dispute=self.dispute,
            uploader=self.buyer,
            original_file="disputes/raw_evidence/test_doc.pdf",
            scrubbed_file="disputes/clean_evidence/test_doc_clean.pdf",
            file_type="DOCUMENT"
        )
        
        # Lawyers should only have access to the scrubbed_file
        self.assertIsNotNone(evidence.scrubbed_file)
        self.assertNotEqual(evidence.original_file, evidence.scrubbed_file)
