from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db import IntegrityError
# Adjust this import based on where your Contract model actually lives
from accounts.models import Contract, ContractApplication

User = get_user_model()

class ContractModelTests(TestCase):
    def setUp(self):
        """Provision the test actors."""
        self.buyer = User.objects.create_user(
            email="buyer@covalent.com",
            password="securepassword123",
            first_name="Client",
            last_name="One"
        )
        self.vendor = User.objects.create_user(
            email="vendor@covalent.com",
            password="securepassword123",
            first_name="Freelancer",
            last_name="One"
        )

    def test_contract_auto_calculates_escrow(self):
        """Asserts that total_escrow is dynamically calculated on save."""
        contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Backend API Development",
            item_description="Build a REST API.",
            item_amount=Decimal("500000.00"),
            delivery_fee=Decimal("15000.00"),
            is_public=True
        )
        
        # 500,000 + 15,000 = 515,000
        self.assertEqual(contract.total_escrow, Decimal("515000.00"))

    def test_direct_contract_overrides_public_flag(self):
        """
        Asserts that if a contract is bound to a specific vendor, 
        it cannot accidentally be pushed to the public marketplace.
        """
        contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor, # Explicitly assigning a vendor
            item_title="Private Code Audit",
            item_description="Audit my smart contracts.",
            item_amount=Decimal("200000.00"),
            delivery_fee=Decimal("0.00"),
            is_public=True, # Attempting to make it public anyway
            status="PROPOSED" # Moving past DRAFT
        )
        
        # The save() method should have intercepted and forced this to False
        self.assertFalse(contract.is_public)

    def test_open_market_contract_creation(self):
        """Asserts the open market configuration saves correctly without a vendor."""
        contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Looking for Frontend Dev",
            item_description="Need a React expert.",
            item_amount=Decimal("150000.00"),
            delivery_fee=Decimal("5000.00"),
            is_public=True,
            status="OPEN"
        )
        
        self.assertTrue(contract.is_public)
        self.assertIsNone(contract.vendor)
        self.assertEqual(contract.status, "OPEN")

    def test_contract_application_creation(self):
        """Asserts a vendor can successfully apply to an OPEN contract."""
        contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Looking for Backend Dev",
            item_description="Need a FastAPI expert.",
            item_amount=Decimal("150000.00"),
            delivery_fee=Decimal("5000.00"),
            is_public=True,
            status="OPEN"
        )
        
        application = ContractApplication.objects.create(
            contract=contract,
            applicant=self.vendor,
            cover_message="I built a TRACE Ingestion API with FastAPI recently.",
            proposed_amount=Decimal("150000.00")
        )
        
        self.assertEqual(application.status, "PENDING")
        self.assertEqual(contract.applications.count(), 1)
        self.assertEqual(contract.applications.first().applicant, self.vendor)

    def test_duplicate_application_blocked(self):
        """Asserts a vendor cannot apply to the same contract twice (unique_together)."""
        contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Database Seeding Script",
            item_description="Need an SQLAlchemy script.",
            item_amount=Decimal("100000.00"),
            delivery_fee=Decimal("0.00"),
            is_public=True,
            status="OPEN"
        )
        
        # First application succeeds
        ContractApplication.objects.create(
            contract=contract,
            applicant=self.vendor,
            cover_message="I can do this."
        )
        
        # Second application should raise an IntegrityError
        with self.assertRaises(IntegrityError):
            ContractApplication.objects.create(
                contract=contract,
                applicant=self.vendor,
                cover_message="Wait, I want to change my price!"
            )

    def test_cannot_create_direct_without_counterparty(self):
        """Asserts validation fails if is_public=False but no vendor is specified."""
        contract = Contract(
            creator=self.buyer,
            item_title="Private SwapGuard Integration",
            item_description="Integration details.",
            item_amount=Decimal("250000.00"),
            delivery_fee=Decimal("0.00"),
            is_public=False,  # Not public!
            status="PROPOSED"
            # Missing vendor and vendor_email intentionally!
        )
        
        with self.assertRaises(ValidationError):
            contract.clean() # This triggers model-level validation