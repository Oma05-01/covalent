import json
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import ValidationError
from accounts.ai_contract import AIContractService
from django.contrib.auth import get_user_model
from accounts.models import Contract
from django.conf import settings
from rest_framework.test import APITestCase  # Changed to APITestCase
from rest_framework import status
from django.urls import reverse

User = get_user_model()

class AIContractServiceTests(APITestCase):  # Inherit from APITestCase

    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="pw")
        self.vendor = User.objects.create_user(email="vendor@instagram.com", password="pw")
        self.client.force_authenticate(user=self.buyer)
    
    @patch('accounts.ai_contract.genai.Client')
    def test_parse_contract_prompt_success(self, MockClient):
        """
        Unit Test: Prompt parsing & JSON validation.
        Proves the service correctly returns structured data when the LLM succeeds.
        """
        # 1. Setup the mock API response to simulate Gemini's output
        mock_client_instance = MockClient.return_value
        mock_response = MagicMock()
        
        # Simulating the exact schema structure you defined
        expected_json = {
            "item_title": "Used iPhone 13",
            "item_description": "Black, 128GB, no scratches. Includes charger.",
            "item_amount": 450000,
            "delivery_fee": 3000,
            "delivery_days": 1,
            "plain_language_summary": "- Buyer pays 450k for an iPhone 13.\n- Seller delivers within 1 day for 3k."
        }
        mock_response.text = json.dumps(expected_json)
        mock_client_instance.models.generate_content.return_value = mock_response

        # 2. Call your service
        service = AIContractService()
        result = service.parse_contract_prompt("I'm buying an iPhone 13 for 450k. Dispatch is 3k, need it tomorrow.")

        # 3. Assertions
        self.assertEqual(result["item_title"], "Used iPhone 13")
        self.assertEqual(result["item_amount"], 450000)
        self.assertEqual(result["delivery_fee"], 3000)
        
        # Ensure the prompt was passed to the LLM
        mock_client_instance.models.generate_content.assert_called_once()
        args, kwargs = mock_client_instance.models.generate_content.call_args
        self.assertIn("I'm buying an iPhone 13", kwargs['contents'])

    @patch('accounts.ai_contract.genai.Client')
    def test_parse_contract_prompt_api_failure(self, MockClient):
        """
        Unit Test: Exception handling.
        Proves the system safely catches API outages and raises a DRF ValidationError.
        """
        mock_client_instance = MockClient.return_value
        # Simulate a network timeout or API error
        mock_client_instance.models.generate_content.side_effect = Exception("Gemini API overloaded")

        service = AIContractService()
        
        # Verify it raises the ValidationError expected by Django Rest Framework
        with self.assertRaises(ValidationError) as context:
            service.parse_contract_prompt("Buy a car for 2 million")
            
        self.assertIn("AI contract generation failed", str(context.exception))

    @patch('accounts.ai_contract.AIContractService.parse_contract_prompt')
    def test_e2e_ai_draft_and_human_edit_flow(self, mock_parse):
        """
        Integration & E2E Test:
        Describes agreement -> AI drafts (saves to DB) -> Human edits via PATCH.
        """
        # 1. Mock the AI output
        mock_parse.return_value = {
            "item_title": "MacBook Pro M2",
            "item_description": "16GB RAM, 512GB SSD",
            "item_amount": 1200000,
            "delivery_fee": 10000,
            "delivery_days": 2,
            "plain_language_summary": "- Buyer pays 1.2M\n- Delivery in 2 days"
        }

        # STEP A: Describe Agreement -> AI Drafts (matches React handleGenerate)
        # Note: If your router uses a different basename, adjust 'contract-generate'
        generate_url = reverse('contract-generate') 
        gen_response = self.client.post(generate_url, {
            "prompt": "Buying a MacBook M2 from vendor@instagram.com for 1.2m",
            "vendor_email": "vendor@instagram.com"
        })
        
        self.assertEqual(gen_response.status_code, status.HTTP_201_CREATED)
        
        # Depending on your model's primary key (id vs contract_id), capture it:
        contract_pk = gen_response.data.get('contract_id') or gen_response.data.get('id')
        self.assertIsNotNone(contract_pk)

        # STEP B: Human Edit -> Correcting the AI's price (matches React handleSaveEdits)
        patch_url = reverse('contract-detail', args=[contract_pk])
        patch_response = self.client.patch(patch_url, {
            "item_amount": "1100000.00"  # Human haggled the price down 100k
        })

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # STEP C: Verify final database state
        contract = Contract.objects.get(pk=contract_pk)
        self.assertEqual(float(contract.item_amount), 1100000.00)  # Edit applied
        self.assertEqual(contract.status, "PROPOSED")              # Status is safe
        self.assertEqual(contract.vendor_email, "vendor@instagram.com")