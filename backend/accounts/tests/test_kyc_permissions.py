# accounts/tests/test_kyc_permissions.py
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestUserTransactionEligibility:
    
    def test_unverified_user_cannot_transact(self):
        """Users without completed KYC should be blocked from escrow actions."""
        user = User.objects.create_user(
            email="newbie@covalent.com",
            password="password",
            is_kyc_verified=False,
            fraud_risk_level="LOW",
            trust_score=70
        )
        assert user.is_eligible_for_escrow() is False

    def test_high_fraud_risk_user_blocked(self):
        """Even with KYC, a high fraud risk flag must block transactions."""
        user = User.objects.create_user(
            email="risky@covalent.com",
            password="password",
            is_kyc_verified=True,
            fraud_risk_level="HIGH",
            trust_score=70
        )
        assert user.is_eligible_for_escrow() is False

    def test_low_trust_score_user_blocked(self):
        """Users whose trust score drops below 50 cannot create new contracts."""
        user = User.objects.create_user(
            email="untrusted@covalent.com",
            password="password",
            is_kyc_verified=True,
            fraud_risk_level="LOW",
            trust_score=45
        )
        assert user.is_eligible_for_escrow() is False

    def test_fully_verified_clean_user_can_transact(self):
        """A verified, low-risk user with a good trust score is eligible."""
        user = User.objects.create_user(
            email="solid@covalent.com",
            password="password",
            is_kyc_verified=True,
            fraud_risk_level="LOW",
            trust_score=75
        )
        assert user.is_eligible_for_escrow() is True