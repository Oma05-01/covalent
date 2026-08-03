from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from decimal import Decimal
from accounts.models import Contract, ContractApplication

User = get_user_model()

class ContractAPITests(APITestCase):
    def setUp(self):
        """Provision users and force authentication for API tests."""
        self.buyer = User.objects.create_user(
            email="api_buyer@covalent.com",
            password="securepassword123",
            first_name="API",
            last_name="Buyer",
            role="BUYER"
        )
        self.vendor = User.objects.create_user(
            email="api_vendor@covalent.com",
            password="securepassword123",
            first_name="API",
            last_name="Vendor",
            role="VENDOR"
        )

    def test_direct_proposal_flow(self):
        """Asserts a buyer can create a direct contract via the API."""
        self.client.force_authenticate(user=self.buyer)
        
        payload = {
            "item_title": "API Backend Build",
            "item_description": "Build DRF endpoints.",
            "item_amount": "400000.00",
            "delivery_fee": "0.00",
            "vendor_email": self.vendor.email, # Direct targeting
            "is_public": False
        }
        
        # We expect a POST request to the contract creation endpoint
        response = self.client.post('/api/v1/accounts/contracts/', payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PROPOSED')
        self.assertEqual(response.data['total_escrow'], '400000.00')
        
        # Verify it saved in the DB correctly
        contract = Contract.objects.get(contract_id=response.data['contract_id'])
        self.assertEqual(contract.vendor, self.vendor)

    def test_open_market_bidding_flow(self):
        """Asserts a vendor can apply to an open market contract."""
        # 1. Buyer creates an open contract
        open_contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Public Django Job",
            item_description="Need a Django dev.",
            item_amount=Decimal("150000.00"),
            delivery_fee=Decimal("5000.00"),
            is_public=True,
            status="OPEN"
        )
        
        # 2. Vendor authenticates and applies
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "cover_message": "I have 5 years of Django experience.",
            "proposed_amount": "150000.00"
        }
        
        # POST to the application endpoint
        response = self.client.post(f'/api/v1/accounts/contracts/{open_contract.contract_id}/apply/', payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContractApplication.objects.count(), 1)
        self.assertEqual(ContractApplication.objects.first().applicant, self.vendor)

    def test_contract_acceptance_binds_vendor(self):
        """Asserts a buyer can accept an application, locking the contract."""
        open_contract = Contract.objects.create(
            creator=self.buyer,
            item_title="Public Django Job",
            item_description="Need a Django dev.",
            item_amount=Decimal("150000.00"),
            delivery_fee=Decimal("5000.00"),
            is_public=True,
            status="OPEN"
        )
        application = ContractApplication.objects.create(
            contract=open_contract,
            applicant=self.vendor,
            cover_message="Let's do this."
        )
        
        # Buyer authenticates and accepts the specific application
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.post(f'/api/v1/accounts/contracts/{open_contract.contract_id}/accept_application/', {
            "application_id": application.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from DB
        open_contract.refresh_from_db()
        self.assertEqual(open_contract.status, "AWAITING_FUNDING")
        self.assertEqual(open_contract.vendor, self.vendor)
        self.assertFalse(open_contract.is_public)

    def test_contract_rejection_flow(self):
        """Asserts a vendor can reject a proposed contract, tombstoning it."""
        proposed_contract = Contract.objects.create(
            creator=self.buyer,
            vendor=self.vendor,
            item_title="Bad Deal",
            item_description="Terrible terms.",
            item_amount=Decimal("10.00"),
            delivery_fee=Decimal("0.00"),
            is_public=False,
            status="PROPOSED"
        )
        
        # Vendor authenticates and rejects
        self.client.force_authenticate(user=self.vendor)
        response = self.client.post(f'/api/v1/accounts/contracts/{proposed_contract.contract_id}/reject/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        proposed_contract.refresh_from_db()
        self.assertEqual(proposed_contract.status, "REJECTED")