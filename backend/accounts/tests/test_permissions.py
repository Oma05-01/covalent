# accounts/tests/test_permissions.py
import pytest
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from accounts.permissions import IsLawyer, IsVendor, IsBuyer, IsKycVerifiedAndSafe

User = get_user_model()

@pytest.fixture
def factory():
    """Provides a DRF request factory for testing permissions."""
    return APIRequestFactory()

@pytest.mark.django_db
class TestRolePermissions:
    
    def test_is_lawyer_permission(self, factory):
        """Asserts IsLawyer only allows users with the LAWYER role."""
        request = factory.get('/')
        lawyer_user = User.objects.create_user(email="lawyer@covalent.com", password="pwd", role="LAWYER")
        buyer_user = User.objects.create_user(email="buyer@covalent.com", password="pwd", role="BUYER")
        
        permission = IsLawyer()
        
        request.user = lawyer_user
        assert permission.has_permission(request, None) is True
        
        request.user = buyer_user
        assert permission.has_permission(request, None) is False

    def test_lawyer_role_isolation_on_vendor_endpoint(self, factory):
        """Asserts Lawyer role is isolated and receives 403 on Vendor endpoints."""
        request = factory.get('/')
        lawyer_user = User.objects.create_user(email="sneaky_lawyer@covalent.com", password="pwd", role="LAWYER")
        
        # Simulate a view that requires IsVendor
        permission = IsVendor()
        request.user = lawyer_user
        
        # The lawyer should be denied access to the vendor permission
        assert permission.has_permission(request, None) is False

    def test_is_buyer_permission(self, factory):
        """Asserts IsBuyer only allows users with the BUYER role."""
        request = factory.get('/')
        buyer_user = User.objects.create_user(email="buyer2@covalent.com", password="pwd", role="BUYER")
        
        permission = IsBuyer()
        request.user = buyer_user
        assert permission.has_permission(request, None) is True

@pytest.mark.django_db
class TestEscrowEligibilityPermission:

    def test_kyc_and_safe_permission_allows_valid_user(self, factory):
        """Asserts IsKycVerifiedAndSafe relies on the model's is_eligible_for_escrow method."""
        request = factory.get('/')
        good_user = User.objects.create_user(
            email="good@covalent.com", 
            password="pwd", 
            is_kyc_verified=True, 
            fraud_risk_level="LOW", 
            trust_score=75
        )
        
        permission = IsKycVerifiedAndSafe()
        request.user = good_user
        assert permission.has_permission(request, None) is True

    def test_kyc_and_safe_permission_denies_risky_user(self, factory):
        request = factory.get('/')
        risky_user = User.objects.create_user(
            email="bad@covalent.com", 
            password="pwd", 
            is_kyc_verified=False, # Fails KYC
            fraud_risk_level="LOW", 
            trust_score=75
        )
        
        permission = IsKycVerifiedAndSafe()
        request.user = risky_user
        assert permission.has_permission(request, None) is False