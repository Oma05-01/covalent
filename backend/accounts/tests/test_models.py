import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
# Assuming Wallet is in the same app. Adjust import if needed.
from accounts.models import Wallet 

User = get_user_model()

@pytest.mark.django_db
class TestCovalentUserModel:
    
    def test_user_creation_and_defaults(self):
        """Validates standard user creation and default values."""
        user = User.objects.create_user(
            email="test@covalent.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.email == "test@covalent.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_lawyer is False
        assert user.is_kyc_verified is False
        
    def test_password_hashing(self):
        """Ensures raw passwords are not stored in the DB."""
        user = User.objects.create_user(
            email="hash@covalent.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe"
        )
        assert user.password != "securepassword123"
        assert user.check_password("securepassword123") is True

    def test_public_id_generation(self):
        """Confirms CVL-XXXXX format and auto-generation on save."""
        user = User.objects.create_user(
            email="id@covalent.com",
            password="password",
            first_name="ID",
            last_name="Test"
        )
        assert user.public_id is not None
        assert user.public_id.startswith("CVL-")
        assert len(user.public_id) == 10 # CVL- + 6 characters

    def test_trust_score_and_fraud_initialization(self):
        """Checks that the Trust Engine defaults are correctly applied."""
        user = User.objects.create_user(
            email="risk@covalent.com",
            password="password",
            first_name="Risk",
            last_name="Test"
        )
        assert user.trust_score == 70
        assert user.fraud_risk_level == "LOW"
        assert user.get_trust_tier_display() == "🟡 Good"

    def test_unique_email_enforcement(self):
        """Asserts same email cannot register twice."""
        User.objects.create_user(email="unique@covalent.com", password="pwd", first_name="A", last_name="B")
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="unique@covalent.com", password="pwd", first_name="C", last_name="D")

    def test_wallet_creation_signal(self):
        """
        Asserts a Wallet is automatically created when a User is created.
        Requires a post_save signal in your accounts/signals.py
        """
        user = User.objects.create_user(
            email="wallet@covalent.com",
            password="password",
            first_name="Wallet",
            last_name="Owner"
        )
        
        wallet = Wallet.objects.get(user=user)
        assert wallet is not None
        assert wallet.available_balance == 0.00
        assert wallet.locked_escrow_balance == 0.00