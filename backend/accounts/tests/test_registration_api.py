# accounts/tests/test_registration_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
class TestRegistrationAPI:
    
    def test_registration_pipeline_success(self, client):
        """Asserts User creation, Wallet creation, and Notification Preferences."""
        url = '/api/v1/accounts/auth/register/'
        payload = {
            "email": "client@covalent.com",
            "password": "securepassword123",
            "role": "BUYER",
            "nin": "12345678902" 
        }
        
        response = client.post(url, payload)
        
        # 1. Asserts User creation and correct response
        assert response.status_code == 201
        assert "tokens" in response.data  # Good practice: log them in immediately
        assert User.objects.count() == 1
        
        user = User.objects.get(email="client@covalent.com")
        
        # 2. Asserts Wallet creation with 0.00 balances
        assert hasattr(user, 'wallet')
        assert float(user.wallet.available_balance) == 0.00
        
        # 3. Asserts Notification Preferences creation
        assert hasattr(user, 'notification_preferences')

    def test_duplicate_email_registration(self, client):
        """Asserts same email cannot register twice (returns 400)."""
        User.objects.create_user(email="taken@covalent.com", password="password123")
        
        url = '/api/v1/accounts/auth/register/'
        payload = {
            "email": "taken@covalent.com",
            "password": "newpassword123",
            "nin": "09876543210"
        }
        response = client.post(url, payload)
        
        assert response.status_code == 400
        assert "email" in response.data
        
    def test_duplicate_nin_registration(self, client):
        """Asserts same NIN cannot be reused across accounts."""
        User.objects.create_user(
            email="first@covalent.com", 
            password="pwd", 
            nin="12345678901"
        )
        
        url = '/api/v1/accounts/auth/register/'
        payload = {
            "email": "second@covalent.com",
            "password": "pwd",
            "nin": "12345678901" # Duplicate NIN
        }
        response = client.post(url, payload)
        
        assert response.status_code == 400
        assert "nin" in response.data