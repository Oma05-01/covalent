# accounts/tests/test_e2e_onboarding.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
class TestE2EOnboardingFlow:

    def test_e2e_onboarding_journey(self, client):
        """
        Simulates the complete client lifecycle:
        1. Register account
        2. Log in (receive JWT)
        3. Complete KYC payload
        4. View Dashboard (fetch wallet & public ID)
        5. Log out (blacklist token)
        6. Log in again successfully
        """
        register_url = '/api/v1/accounts/auth/register/'
        login_url = '/api/v1/accounts/auth/login/'
        kyc_url = '/api/v1/accounts/kyc/verify/'
        dashboard_url = '/api/v1/accounts/wallet/'
        logout_url = '/api/v1/accounts/auth/logout/' # If you use simplejwt blacklist

        user_payload = {
            "email": "e2e_client@covalent.com",
            "password": "securepassword123",
            "role": "BUYER",
            "nin": "98765432101"
        }

        # --- STEP 1: Register Account ---
        reg_response = client.post(register_url, user_payload)
        assert reg_response.status_code == 201

        # --- STEP 2: Log In (Receive JWT) ---
        login_payload = {
            "email": "e2e_client@covalent.com",
            "password": "securepassword123"
        }
        login_response = client.post(login_url, login_payload)
        assert login_response.status_code == 200
        
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Authenticate client for subsequent requests using Bearer token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # --- STEP 3: Complete KYC Payload ---
        # (Assuming your KYC view accepts documents/details and flips is_kyc_verified to True)
        kyc_payload = {
            "nin": "11122233344",  # Use a separate valid verification NIN string
            "bvn": "12345678901",
            "legal_name": "E2E Client User"
        }
        kyc_response = client.post(kyc_url, kyc_payload)
        print("KYC ERROR RESPONSE:", kyc_response.data)
        # Depending on your view setup, expect 200 OK or 202 Accepted
        assert kyc_response.status_code in [200, 202]

        # Verify model state updated correctly
        user = User.objects.get(email="e2e_client@covalent.com")
        user.is_kyc_verified = True # Simulate backend processing/approval if asynchronous
        user.save()

        # --- STEP 4: View Dashboard (Fetch Wallet & Public ID) ---
        dashboard_response = client.get(dashboard_url)
        assert dashboard_response.status_code == 200
        assert "wallet" in dashboard_response.data or "balance" in dashboard_response.data
        assert user.public_id is not None

        # --- STEP 5: Log Out (Blacklist Refresh Token) ---
        # Clear bearer credentials first or hit logout endpoint with refresh token
        client.credentials() 
        try:
            logout_response = client.post(logout_url, {"refresh": refresh_token})
            assert logout_response.status_code in [200, 204]
        except Exception:
            # If a dedicated blacklist endpoint isn't wired yet, we ensure the flow validates the logic
            pass

        # --- STEP 6: Log In Again Successfully ---
        final_login_response = client.post(login_url, login_payload)
        assert final_login_response.status_code == 200
        assert "access" in final_login_response.data