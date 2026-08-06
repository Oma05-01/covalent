from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Contract

User = get_user_model()

class AIContractIntegrationTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="pw")
        self.vendor = User.objects.create_user(email="vendor@example.com", password="pw")
        self.client.force_authenticate(user=self.buyer)

    @patch('accounts.ai_contract.AIContractService.parse_contract_prompt')
    def test_ai_draft_human_edit_and_contract_creation(self, mock_parse):
        """
        Integration Test:
        AI generates draft -> Human edits terms -> Contract is created successfully.
        """
        # 1. Mock the AI parsing output
        mock_parse.return_value = {
            "item_title": "MacBook Pro M2",
            "item_description": "16GB RAM, 512GB SSD, Space Gray",
            "item_amount": 1200000,
            "delivery_fee": 10000,
            "delivery_days": 2,
            "plain_language_summary": "- Buyer pays 1.2M for MacBook Pro M2.\n- Delivery in 2 days."
        }

        # Step A: Request AI generation
        generate_url = reverse('contract-generate-ai-draft')
        gen_response = self.client.post(generate_url, {"prompt": "I'm buying a MacBook M2 from vendor@example.com for 1.2m"})
        
        self.assertEqual(gen_response.status_code, status.HTTP_200_OK)
        draft_data = gen_response.data

        # Step B: Human Edits - Buyer negotiates lower price (1.1M) before saving
        contract_payload = {
            **draft_data,
            "item_amount": "1100000.00",  # Human override
            "vendor_email": self.vendor.email,
            "is_public": False
        }

        # Step C: Save final edited contract to DB
        create_url = reverse('contract-list')
        create_response = self.client.post(create_url, contract_payload)

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Verify Human Edit persisted in Database
        contract = Contract.objects.get(contract_id=create_response.data['contract_id'])
        self.assertEqual(float(contract.item_amount), 1100000.00)
        self.assertEqual(contract.status, "PROPOSED")
        self.assertEqual(contract.creator, self.buyer)
        self.assertEqual(contract.vendor, self.vendor)