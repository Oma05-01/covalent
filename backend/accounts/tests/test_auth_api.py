# accounts/tests/test_auth_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
class TestAuthAPI:
    
    def test_login_flow_success(self, client):
        """Asserts login returns a valid JWT access and refresh token."""
        # 1. Create a user with a known password
        user = User.objects.create_user(
            email="loginuser@covalent.com",
            password="mypassword123"
        )
        
        url = '/api/v1/accounts/auth/login/'
        payload = {
            "email": "loginuser@covalent.com",
            "password": "mypassword123"
        }
        
        response = client.post(url, payload)
        
        # 2. Assert success and token payload structure
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_refresh_success(self, client):
        """Asserts the refresh token correctly issues a new access token."""
        user = User.objects.create_user(
            email="refreshuser@covalent.com",
            password="mypassword123"
        )
        
        # Get initial tokens via login
        login_url = '/api/v1/accounts/auth/login/'
        login_response = client.post(login_url, {
            "email": "refreshuser@covalent.com",
            "password": "mypassword123"
        })
        
        refresh_token = login_response.data["refresh"]
        
        # Request a new access token using the refresh token
        refresh_url = '/api/v1/accounts/auth/refresh/'
        refresh_response = client.post(refresh_url, {
            "refresh": refresh_token
        })
        
        assert refresh_response.status_code == 200
        assert "access" in refresh_response.data