import uuid  # <-- ADD THIS IMPORT
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.cache import cache
from django.contrib.auth import get_user_model
from governance.models import GovernanceProfile
from accounts.models import Contract

User = get_user_model()

class InitializeEscrowSecurityTests(APITestCase):
    def setUp(self):
        self.attacker = User.objects.create_user(email="attacker@example.com", password="pw")
        self.vendor = User.objects.create_user(
            email="vendor@example.com", 
            password="pw", 
            paystack_subaccount_code="ACCT_mock_123"
        )
        
        # Create a valid UUID for the test
        self.test_uuid = uuid.uuid4()
        
        # Create the dummy contract using the valid UUID
        self.contract = Contract.objects.create(
            contract_id=self.test_uuid,  # <-- FIX: Using a real UUID
            creator=self.attacker,
            vendor_email=self.vendor.email,
            item_amount="450.00",
            delivery_fee="50.00"
        )
        
        cache.clear()

    def test_velocity_spike_triggers_immediate_suspension(self):
        self.client.force_authenticate(user=self.attacker)
        
        profile = self.attacker.governance_profile
        profile.fraud_risk_score = 90
        profile.save()
        
        cache_key = f"velocity_{self.attacker.id}_initialize_escrow"
        cache.set(cache_key, 5, timeout=60)
        
        url = f"/api/v1/escrow/contracts/{self.contract.contract_id}/pay/"
        
        response = self.client.post(url, {
            "contract_id": str(self.contract.contract_id) 
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['detail'], 
            "Action blocked: Account suspended due to critical security risk."
        )
        
        profile.refresh_from_db()
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.SUSPENDED)
        self.assertEqual(profile.fraud_risk_score, 105)