from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.models import Contract, ContractApplication

User = get_user_model()

class ContractE2ETests(APITestCase):
    def setUp(self):
        """Provision our actors."""
        self.buyer = User.objects.create_user(
            email="e2e_buyer@covalent.com", password="password123", role="BUYER"
        )
        self.vendor = User.objects.create_user(
            email="e2e_vendor@covalent.com", password="password123", role="VENDOR"
        )

    def test_e2e_marketplace_lifecycle(self):
        """
        Simulates the full Open Market flow:
        1. Buyer creates public job.
        2. Vendor browses and applies.
        3. Buyer reviews applications and accepts one.
        4. Contract locks and awaits funding.
        """
        
        # ---------------------------------------------------------
        # STEP 1: Buyer creates a public contract
        # ---------------------------------------------------------
        self.client.force_authenticate(user=self.buyer)
        create_payload = {
            "item_title": "Fullstack React App",
            "item_description": "Need a marketplace built.",
            "item_amount": "500000.00",
            "delivery_fee": "10000.00",
            "is_public": True
        }
        response = self.client.post('/api/v1/accounts/contracts/', create_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contract_id = response.data['contract_id']
        
        # ---------------------------------------------------------
        # STEP 2: Vendor browses and applies
        # ---------------------------------------------------------
        self.client.force_authenticate(user=self.vendor)
        
        # Vendor checks the public board
        list_response = self.client.get('/api/v1/accounts/contracts/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        # Ensure the contract is in the public list
        self.assertTrue(any(c['contract_id'] == contract_id for c in list_response.data))
        
        # Vendor submits an application
        apply_payload = {
            "cover_message": "I built something exactly like this last year.",
            "proposed_amount": "500000.00"
        }
        apply_response = self.client.post(f'/api/v1/accounts/contracts/{contract_id}/apply/', apply_payload)
        self.assertEqual(apply_response.status_code, status.HTTP_201_CREATED)
        application_id = apply_response.data['id']

        # ---------------------------------------------------------
        # STEP 3: Buyer reviews and accepts the bid
        # ---------------------------------------------------------
        self.client.force_authenticate(user=self.buyer)
        
        accept_payload = {"application_id": application_id}
        accept_response = self.client.post(f'/api/v1/accounts/contracts/{contract_id}/accept_application/', accept_payload)
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

        # ---------------------------------------------------------
        # STEP 4: System Verification
        # ---------------------------------------------------------
        # Fetch the final contract state from the database
        final_contract = Contract.objects.get(contract_id=contract_id)
        
        self.assertEqual(final_contract.status, "AWAITING_FUNDING")
        self.assertEqual(final_contract.vendor, self.vendor)
        self.assertFalse(final_contract.is_public)  # It is now locked and private
        
        # Verify the application was marked as accepted
        accepted_app = ContractApplication.objects.get(id=application_id)
        self.assertEqual(accepted_app.status, "ACCEPTED")

    def test_e2e_direct_contract_rejection(self):
        """
        Simulates a Direct Flow rejection:
        1. Buyer targets a specific vendor.
        2. Vendor reviews and rejects the terms.
        """
        # Buyer proposes contract
        self.client.force_authenticate(user=self.buyer)
        create_payload = {
            "item_title": "Quick Bug Fix",
            "item_description": "Fix the navbar.",
            "item_amount": "20000.00",
            "delivery_fee": "0.00",
            "vendor_email": self.vendor.email,
            "is_public": False
        }
        response = self.client.post('/api/v1/accounts/contracts/', create_payload)
        contract_id = response.data['contract_id']

        # Vendor rejects it
        self.client.force_authenticate(user=self.vendor)
        reject_response = self.client.post(f'/api/v1/accounts/contracts/{contract_id}/reject/')
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)

        # Verify state
        final_contract = Contract.objects.get(contract_id=contract_id)
        self.assertEqual(final_contract.status, "REJECTED")